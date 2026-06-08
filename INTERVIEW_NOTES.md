# Interview Notes: Chronis Behavioral Insight Engine

This document serves as a study guide for the technical interview. It synthesizes the architecture, rationales, and potential Q&A based on the design decisions of the Behavioral Insight Engine.

## 1. Architecture Explanation
**Pipeline Flow:**
1. **`data_loader`**: Reads CSV, dynamically infers schema (identifying date vs. numeric metric columns), and cleans data (dropping all-NaN columns).
2. **`pattern_detector`**: Scans numeric series for sustained trends using rolling windows and linear regression.
3. **`anomaly_detector`**: Scans for point-in-time outliers using Z-score, IQR, and rolling deviation.
4. **`confidence_engine` & `evidence_validator`**: Evaluates findings. Filters out noise and abstains if evidence is insufficient.
5. **`insight_generator`**: Converts high-confidence statistical findings into safe, factual, natural-language insights (strictly enforcing the `FORBIDDEN_TERMS` policy).
6. **`report_builder` & `main`**: Orchestrates the modules and outputs to JSON and Markdown.

**Design Philosophy:**
- **Modular & Typed:** Built with standard Python `@dataclass` structures for type safety and separation of concerns.
- **Explainable Analytics:** Uses transparent statistical methods rather than black-box ML models, ensuring every output can be mathematically verified.
- **Dynamic Schema:** Hardcoding column names is avoided so the system can seamlessly process new metrics without code changes.

---

## 2. Statistical Choices & Rationale

### Why Regression + Rolling Windows?
- **Rolling Windows (7-day vs baseline):** Captures intuitive weekly behavioral shifts, smoothing over day-of-week variance (e.g., weekend vs. weekday).
- **Linear Regression:** Provides rigorous quantification of the trend (magnitude/slope, R², p-value).
- **Together:** They cross-validate. If regression says there's a trend but rolling windows don't see a significant relative shift, it might be statistical noise. When both agree, confidence is high.

### Why Z-score + IQR + Rolling Deviation?
No single anomaly detection method is perfect. The engine uses an **OR-logic** ensemble:
- **Z-score:** Good for global outliers but assumes normal distribution.
- **IQR:** Robust to extreme outliers and non-normal distributions, compensating for Z-score's weakness.
- **Rolling Deviation:** Catches *contextual* anomalies (e.g., walking 4,000 steps is normally fine, but highly anomalous if the user averaged 10,000 steps over the last 5 days).

### Confidence Scoring Rationale
Instead of binary pass/fail, confidence is a continuous weighted score (0.0 to 1.0):
- **Trend Strength (0.35):** Highest weight; magnitude of behavioral change is the most important signal.
- **Sample Size (0.25):** Ensures there is enough data to make a reliable claim.
- **Consistency (0.25):** Ensures the trend spans across multiple days.
- **Variance Stability (0.15):** Ensures the trend isn't just noise.
A threshold of **0.60** is required to promote a finding to an "insight", balancing sensitivity and specificity.

### Abstention Rationale
In health and behavioral analytics, **a wrong insight is worse than no insight.**
- The engine actively abstains (outputting structural reasons) when:
  - Sample size is too small (< 7 days).
  - The coefficient of variation is negligible (< 0.01).
  - Confidence fails to meet the 0.60 threshold.
- **Analogy:** Like a medical lab test returning "Inconclusive" instead of guessing.

---

## 3. Key Tradeoffs & Known Limitations

**Tradeoffs:**
- **Explainable Stats vs. Advanced ML:** Opted against ARIMA or change-point ML models to ensure 100% explainability.
- **OR-logic in Anomalies:** May increase false positives (as any method can trigger it), but in behavioral health, false negatives are far more dangerous.
- **Factual Language vs. Engaging Copy:** Output is intentionally clinical and factual to guarantee psychological and medical safety, prioritizing responsibility over "engaging" product copy.

**Known Limitations:**
- **No Cross-Metric Inference:** Currently processes metrics in isolation. It cannot declare "Sleep decreases *when* Screen Time increases" (correlation between variables).
- **Short-Term Trends:** A 7-day rolling window will miss transient 2-day spikes.
- **Dataset Size:** 30 days is relatively small; confidence and statistical significance are inherently limited by sample size.

---

## 4. Likely Interviewer Questions & Answers

**Q1: Why didn't you use an ML library like scikit-learn or a time-series model like Prophet?**
*A:* "The prompt explicitly stated 'The goal is NOT to maximize ML sophistication' but rather 'Explainability' and 'Evidence-backed reasoning'. A complex ML model would introduce opacity. By using SciPy's linear regression and basic rolling statistics, I can trace exactly why every insight was generated, providing the explainability required in a behavioral health context."

**Q2: What happens if I upload a CSV with completely different columns, like `calories_burned` and `water_intake`?**
*A:* "The engine will process it perfectly without any code changes. The `data_loader` dynamically inspects data types and column names, separating date features from continuous numeric features. As long as it's numerical time-series data, the engine adapts automatically."

**Q3: How do you prevent the system from diagnosing a user with depression or anxiety?**
*A:* "This is solved structurally. First, the `insight_generator` uses a strict fact-based template system. It describes the data ('Mood decreased by 15%'), not the person. Second, as a fallback, I implemented a `FORBIDDEN_TERMS` list in the configuration that actively scans and prevents diagnostic, medical, or judgmental language from ever reaching the output."

**Q4: Your system missed a major anomaly on day 3. Why?**
*A:* "The rolling deviation method requires a minimum window to establish a baseline. An anomaly on day 3 might trigger the Z-score or IQR if it's a global outlier, but if it's merely a contextual outlier, it will be missed because 3 days isn't enough to build a reliable local baseline. This is a deliberate tradeoff to avoid false positives on initialization."

**Q5: Why did you build an abstention engine? Why not just output the closest guess?**
*A:* "In behavioral data, guessing is dangerous. If there's insufficient evidence (e.g., flatline data, less than a week of observations), providing an insight creates false signals. By outputting an explicit 'Abstention' with a reason code, the system communicates the limits of the data, which is critical for reliability and trust."
