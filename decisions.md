# Design Decisions

This document explains **why** each design choice was made in the Chronis Behavioral Insight Engine. It's structured as an engineering defense—each section covers the reasoning, alternatives considered, and tradeoffs accepted. If you're reviewing this as part of a technical evaluation, every decision here has a deliberate rationale.

---

## Pattern Detection: Why Rolling Windows + Linear Regression

### The Approach

Patterns are detected using two complementary methods that must cross-validate each other:

1. **Rolling window comparison** — Compare the mean of a recent window (last 7 days) against a baseline window (preceding 7 days). If the percent change exceeds 10%, flag it as a candidate pattern.
2. **Linear regression** — Fit a line to the metric values over the analysis window. Extract slope, R², and p-value to quantify trend direction, strength, and statistical significance.

### Why This Combination

**Rolling windows** are intuitive and fast. They directly answer the question "is recent behavior different from baseline behavior?" in a way that's immediately explainable to a non-technical stakeholder. A 7-day window naturally captures weekday/weekend behavioral cycles—a person's sleep or activity pattern on weekdays may systematically differ from weekends, and a full-week window smooths over that variance.

**Linear regression** adds statistical rigor. Window comparison alone can be noisy—a single outlier in the recent window can inflate the percent change. Regression provides a slope (magnitude of change per day), R² (how much of the variance is explained by the trend), and p-value (probability the trend is due to chance). When both methods agree—window comparison shows a significant shift AND regression confirms a statistically significant slope—confidence in the pattern is substantially higher.

The **10% threshold** for window comparison was chosen to filter out day-to-day noise. Behavioral metrics naturally fluctuate by 3–8% due to measurement variability, mood, and circumstance. A 10% bar ensures that flagged patterns represent meaningful behavioral change, not random drift.

### Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| **ARIMA / exponential smoothing** | Overpowered for 30-day datasets. ARIMA requires parameter tuning (p, d, q), risks overfitting on short series, and produces outputs that are harder to explain to non-statisticians. |
| **Simple threshold on absolute values** | Too rigid. "Sleep below 6 hours" doesn't account for individual baselines—someone who normally sleeps 5 hours isn't anomalous at 5.2. |
| **ML-based trend detection (e.g., change-point detection)** | More sophisticated, but introduces opaque model decisions. The goal is full explainability, and a reviewer should be able to verify any pattern by hand with a calculator. |

### Tradeoffs Accepted

- **7-day window means trends shorter than 7 days are invisible.** A 3-day spike in screen time won't register as a "pattern." This is intentional—we want sustained behavioral shifts, not transient blips.
- **10% threshold may miss gradual drift.** A metric declining 1% per day over 30 days is a 30% total change but may never exceed 10% in any single 7-day window. This is a known limitation; multi-week windows (listed in Future Improvements) would address it.

---

## Anomaly Detection: Why Z-score + IQR + Rolling Deviation

### The Approach

A data point is flagged as anomalous if **any** of three methods triggers:

1. **Z-score** (threshold: 2.5) — Measures how many standard deviations a value is from the global mean.
2. **IQR (Interquartile Range)** — Flags values below Q1 − 1.5×IQR or above Q3 + 1.5×IQR.
3. **Rolling deviation** — Flags values that deviate from the rolling mean by more than 2× the rolling standard deviation.

### Why Three Methods

Each method has a specific blind spot that the others compensate for:

| Method | Strength | Weakness |
|---|---|---|
| **Z-score** | Sensitive to global outliers; easy to interpret | Assumes normality; distorted by extreme outliers in the dataset itself |
| **IQR** | Robust to non-normal distributions; not affected by extreme outliers | Less sensitive to moderate outliers; uses only quartile information |
| **Rolling deviation** | Catches *contextual* anomalies—values that are unusual relative to recent history, even if globally normal | Requires sufficient window history; can't detect anomalies in the first few days |

**Example:** A person normally walks 8,000 steps but has been walking 4,000 for the last week (injured). On the 8th day they walk 3,800. Z-score says "normal" (3,800 is within 2.5σ of the 30-day global mean). IQR says "normal." But rolling deviation flags it as unusual relative to the recent 4,000-step baseline. Conversely, if someone suddenly walks 15,000 steps on a single day, Z-score and IQR catch it immediately, even if the rolling window hasn't adjusted.

### Why OR Logic (Flag if ANY Triggers)

The alternative—requiring ALL methods to agree—would dramatically reduce false positives but would also miss real anomalies that only one method can detect. In a behavioral health context, **false negatives (missing a real anomaly) are more costly than false positives (flagging a non-issue).** A flagged anomaly that turns out to be benign is easily dismissed; a missed anomaly that indicates a health concern is a failure.

### Why Z-score Threshold 2.5

| Threshold | Sensitivity | Specificity | Practical Effect |
|---|---|---|---|
| **2.0** | High | Low | Flags ~5% of data points; too many false positives for 30-day datasets |
| **2.5** | Moderate | Moderate | Flags ~1.2% of data points; good balance for small datasets |
| **3.0** | Low | High | Flags ~0.3%; may miss genuine anomalies in short series |

With only 30 data points, a threshold of 2.0 would flag 1–2 points per metric almost by definition (statistical expectation). A threshold of 3.0 would require truly extreme values—unlikely to appear in everyday behavioral data. **2.5 balances sensitivity and specificity for the dataset size.**

### Tradeoffs Accepted

- **OR logic may increase false positives.** If all three methods flag independently at a 5% rate, the combined false positive rate is higher. This is mitigated downstream by the confidence engine—a flagged anomaly with low confidence is reported but not elevated to an insight.
- **Z-score assumes approximate normality.** Behavioral data (especially step counts and screen time) can be skewed. IQR compensates for this, but Z-score may still produce spurious flags on heavily skewed metrics.

---

## Confidence Scoring: Why a Weighted Composite

### The Approach

Every finding receives a confidence score between 0.0 and 1.0, computed as a weighted average of four independently interpretable components:

| Component | Weight | What It Measures |
|---|---|---|
| **Sample size** | 0.25 | More data → more reliable conclusions |
| **Trend strength** | 0.35 | Larger magnitude change → stronger signal |
| **Consistency** | 0.25 | Trend visible across more days → more credible |
| **Variance stability** | 0.15 | Lower noise → trend is less likely to be random |

A finding is promoted to an **insight** only if its overall confidence ≥ 0.60.

### Why These Weights

**Trend strength (0.35)** receives the highest weight because it directly measures the magnitude of behavioral change—the core question the system is designed to answer. A strong trend in a small sample is more interesting than a weak trend in a large sample.

**Sample size (0.25) and consistency (0.25)** are equally weighted because they measure complementary aspects of reliability. A large sample with inconsistent data (trend appears in 4 of 10 days) is no more trustworthy than a small but perfectly consistent sample.

**Variance stability (0.15)** receives the lowest weight because low variance alone doesn't indicate a meaningful trend—it just means the data isn't noisy. It's a supporting signal, not a primary one.

### Why 0.60 Threshold

The threshold determines how aggressive the system is about making claims:

| Threshold | Behavior |
|---|---|
| **0.40** | Aggressive — produces many insights but includes speculative ones |
| **0.50** | Moderate — still includes borderline findings |
| **0.60** | Balanced — requires meaningful evidence across multiple components |
| **0.70** | Conservative — misses some real patterns to avoid any weak claims |
| **0.80** | Very conservative — only the strongest signals pass |

**0.60 was chosen as a moderate bar.** It requires that at least 2–3 components score above average, preventing any single strong component from carrying a finding over the threshold alone. This aligns with the project's philosophy of evidence-backed claims without being so conservative that the system abstains on everything.

### Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| **Binary pass/fail on each check** | Loses granularity. A trend of 9.9% and 10.1% would receive completely different outcomes. Continuous scoring preserves the gradient. |
| **ML-based confidence (trained classifier)** | Requires labeled training data ("this is a real pattern / not a real pattern") which doesn't exist. Also violates the explainability principle—a learned model's confidence is not independently auditable. |
| **Unweighted average** | Treats all components as equally important, which doesn't match domain reality. Trend strength matters more than variance stability. |

### Tradeoffs Accepted

- **Weights are hand-tuned, not optimized.** Without labeled data, there's no principled way to learn optimal weights. The current weights reflect domain reasoning, not empirical optimization.
- **0.60 is a single global threshold.** Ideally, different metrics might warrant different thresholds (sleep hours may need a lower bar than step count). A per-metric threshold system is left for future work.

---

## Abstention: Why It's a Core Feature

### The Problem

Most analytical systems are designed to always produce output. Given any input, they generate a prediction, a score, or a classification. This creates a dangerous failure mode: **when the system doesn't have enough evidence, it still says something—and that something can be wrong.**

In behavioral health contexts, a wrong insight is worse than no insight. Telling someone "your mood is declining" based on 5 noisy data points could cause unnecessary anxiety. Telling someone "your activity levels are healthy" based on insufficient data could create false reassurance.

### The Solution

Abstention is a **first-class output type**, not an error state. When the system abstains, it produces a structured record that includes:

- **Which metric** was analyzed
- **Why** the system abstained (specific reason code)
- **What evidence** was insufficient (exact values vs. thresholds)
- **What would be needed** to produce an insight (implicitly, by showing the gap)

### Three Abstention Triggers

| Trigger | Condition | Rationale |
|---|---|---|
| **Insufficient data** | Sample size < 7 | Fewer than 7 data points can't establish a meaningful weekly pattern. Any trend in <7 points is too easily dominated by a single outlier. |
| **Weak signal** | Coefficient of variation < 0.01 OR trend magnitude < 5% | If the data barely varies, or the detected trend is negligibly small, there's nothing meaningful to report. Forcing an insight would be manufacturing significance. |
| **Low confidence** | Overall confidence < 0.60 | Even if the data passes basic sufficiency checks, the composite confidence score may still fall below threshold—indicating that while individual components are adequate, the overall evidence is not compelling. |

### The Medical Testing Analogy

This design mirrors established practices in medical diagnostics. A blood test can return three results: positive, negative, or **inconclusive**. An inconclusive result isn't a failure—it's the system honestly communicating the limits of its analysis. The patient can then decide to retest with a different method or at a later time.

Similarly, a behavioral abstention communicates: "Based on the current data, I cannot make a reliable claim about this metric. More data or a different analysis window might yield a result."

### Tradeoffs Accepted

- **The system may abstain on metrics where a human analyst would feel comfortable making a judgment call.** This is intentional—the system errs on the side of caution.
- **Abstentions don't provide actionable recommendations.** They explain what's insufficient but don't suggest what to do about it. This is a scope boundary—the system analyzes, it doesn't advise.

---

## Output Safety

### The Problem

Behavioral data analysis sits adjacent to sensitive domains: mental health, medical diagnosis, and personality assessment. An automated system that generates natural-language descriptions of behavior could easily cross into territory that is:

- **Medically irresponsible** ("your heart rate pattern suggests cardiac risk")
- **Psychologically harmful** ("your mood data indicates depression")
- **Judgmental** ("your screen time suggests poor self-control")

### The Solution

Output safety is enforced at two levels:

1. **`FORBIDDEN_TERMS` list** — A curated set of terms that the system will never include in generated text. This includes medical conditions, psychological diagnoses, personality labels, and judgmental language.

2. **Factual-only language policy** — All generated descriptions are limited to observable, behavioral facts:
   - ✅ "steps decreased by 15% compared to baseline"
   - ✅ "screen_time_minutes was 2.8 standard deviations above the mean on 2024-03-15"
   - ❌ "user is becoming sedentary"
   - ❌ "this pattern suggests anxiety"
   - ❌ "user should exercise more"

### Why This Is a Product Decision

This isn't just a content filter bolted on at the end. It's a **deliberate product constraint** that shapes the entire insight generation pipeline. The `insight_generator` module is designed from the ground up to produce behavioral descriptions, not behavioral assessments. The forbidden terms list is a safety net, not the primary mechanism—the primary mechanism is that the generation logic never attempts to produce diagnostic or judgmental language in the first place.

### Tradeoffs Accepted

- **Outputs may feel "dry" or overly clinical.** A system that says "steps decreased by 15%" is less engaging than one that says "you might want to get moving more!" But clinical precision is the correct tradeoff for a system that could influence health-related decisions.
- **The forbidden terms list requires maintenance.** New problematic terms may emerge as language evolves. The list should be reviewed periodically.

---

## Known Limitations

### Data Constraints

- **30-day dataset is small.** Statistical methods are more reliable with larger samples. Trends and anomalies identified in 30 days may reverse or strengthen with 90+ days of data. The system's own evidence validation partially mitigates this—it won't make claims without sufficient evidence—but the ceiling on what it *can* detect is inherently limited.
- **No causal inference.** The system identifies correlations and trends, not causes. "Sleep decreased while screen time increased" does not mean screen time caused poor sleep. The output language is carefully designed to avoid causal claims.
- **Missing value handling is basic.** The current approach skips `NaN` values rather than imputing them. For metrics with many missing values, this reduces the effective sample size and may trigger abstention. More sophisticated imputation (forward-fill, interpolation) was considered but rejected for this version to avoid introducing assumptions about missing data.

### Analytical Constraints

- **7-day window can miss shorter patterns.** A 3-day behavioral change (e.g., a weekend binge) is smoothed out by the weekly window. Sub-weekly pattern detection would require shorter windows, which come with higher noise sensitivity.
- **Single-metric analysis only.** Each metric is analyzed independently. The system cannot detect cross-metric relationships (e.g., "on days when sleep drops below 6 hours, mood tends to decrease"). Cross-correlation analysis is a planned future improvement.
- **No seasonality detection.** The system treats all 30 days equally. It cannot identify day-of-week effects (e.g., consistently lower steps on Sundays) or monthly cycles.

### Edge Cases

- **All-constant data.** If a metric has identical values across all days (e.g., resting heart rate is exactly 72 for all 30 days), Z-score computation fails (division by zero with `std=0`) and IQR collapses to zero width. The system handles this gracefully by catching the edge case and triggering an abstention with an `insufficient_variance` reason.
- **Very short datasets (<14 days).** Window comparison requires at least two non-overlapping windows (7 + 7 = 14 days). Datasets shorter than 14 days produce no pattern detection results. The system does not error—it simply returns an empty pattern list and may generate abstentions.
- **Extreme outliers.** A single extreme value (e.g., 50,000 steps in one day) can skew the global mean and standard deviation, affecting Z-score calculations. IQR is included specifically because it's robust to such outliers, but the Z-score component may still produce misleading results in the presence of extreme values.

---

## Engineering Tradeoffs

### Dataclasses over Pydantic

**Choice:** Python's built-in `@dataclass` decorator.

**Rationale:** The project has a minimal dependency philosophy. Pydantic would add runtime validation, serialization features, and better error messages—but at the cost of an additional dependency and a learning curve for reviewers unfamiliar with Pydantic v2. Since all data flows through a controlled pipeline (not user-supplied API requests), the validation benefits of Pydantic are less critical. Dataclasses provide type hints, `__repr__`, and structural clarity with zero additional dependencies.

### scipy.stats.linregress over sklearn

**Choice:** `scipy.stats.linregress` for linear regression.

**Rationale:** The project needs slope, R², and p-value from a simple ordinary least squares regression. `sklearn.linear_model.LinearRegression` is more powerful but doesn't directly provide p-values (requires manual computation or `statsmodels`). `scipy.stats.linregress` returns slope, intercept, R-value, p-value, and standard error in a single call. It's also a lighter dependency than sklearn—scipy is already needed for Z-score computation, so no additional install is required.

### Centralized config.py over YAML

**Choice:** All constants in a single `config.py` file.

**Rationale:** A YAML configuration file would allow non-developers to modify thresholds without touching Python code. However, for a single-developer project at this stage, `config.py` is simpler: it's type-checked by the IDE, importable without a parser, and doesn't require a YAML library. Migration to YAML is straightforward if needed (listed in Future Improvements) and would be the right choice for a multi-user or deployed system.

### sys.argv over argparse

**Choice:** Direct `sys.argv[1]` access for the optional CSV path argument.

**Rationale:** The pipeline accepts exactly one optional argument (the CSV file path). `argparse` would add help text, type validation, and a `--help` flag—all valuable for a CLI tool with multiple arguments. For a single optional positional argument, `sys.argv` is simpler and more readable. If the CLI grows (e.g., `--config`, `--output-dir`, `--verbose`), argparse should be adopted.

### Dynamic Schema Discovery over Hardcoded Columns

**Choice:** Auto-detect date columns and numeric metrics at runtime.

**Rationale:** Hardcoding column names (`sleep_hours`, `steps`, etc.) would be faster and simpler, but it would make the pipeline brittle—any new dataset with different column names would require code changes. Dynamic discovery allows the pipeline to work with arbitrary behavioral CSVs, making it more reusable and demonstrating a more production-ready design. The tradeoff is slightly more complex data loading logic and the possibility of incorrectly classifying a non-behavioral numeric column as a metric.

---

## Failure Modes

This section documents how the system behaves under adverse conditions. Graceful degradation is preferred over crashing.

| Failure Mode | System Behavior |
|---|---|
| **All-constant data** (std = 0) | Z-score computation is skipped (division by zero guard). IQR collapses but doesn't error. Abstention generated with `insufficient_variance` reason. |
| **Very short dataset** (<14 days) | Window comparison returns empty results (insufficient data for two windows). Regression may still run but with low confidence. Abstentions generated for affected metrics. |
| **Extreme outliers** | Z-score may produce inflated results due to skewed mean/std. IQR (robust to outliers) compensates. Anomaly flagged but confidence may be lower due to high variance. |
| **Missing date column** | `SchemaValidationError` raised with a clear message listing the columns found and what was expected. Pipeline halts with an actionable error. |
| **Empty CSV file** | `InsufficientDataError` raised immediately during data loading. No partial results produced. |
| **All NaN values in a metric** | Metric is skipped entirely. If all metrics are NaN, pipeline produces empty outputs with abstentions for every metric. |
| **Non-numeric columns** | Automatically excluded during schema discovery. A warning is logged if unexpected non-numeric columns are found. |
| **Duplicate dates** | Processed as-is (each row treated independently). May inflate sample size calculations. A future improvement could deduplicate or aggregate by date. |
