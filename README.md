<div align="center">

# 🧠 Chronis Behavioral Insight Engine

**An explainable, evidence-backed behavioral analytics pipeline that knows when to speak — and when to stay silent.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-56%20passed-28A745?style=flat-square&logo=pytest&logoColor=white)](#-testing)
[![Coverage](https://img.shields.io/badge/coverage-89%25-28A745?style=flat-square)](#-testing)
[![Dataset](https://img.shields.io/badge/dataset-official%20Chronis-blue?style=flat-square)](#-assessment-results)

---

*Submission for the **Chronis AI/ML Internship Assessment** — Task A*

[Features](#-features) · [Architecture](#-architecture) · [Quick Start](#-quick-start) · [Methodology](#-methodology) · [Results](#-assessment-results) · [Decisions](decisions.md)

</div>

---

## 📋 Overview

This system analyzes daily behavioral time-series data and produces **six distinct analytical outputs**:

| Output | Purpose |
|--------|---------|
| **Pattern Discovery** | Identifies sustained behavioral trends using dual-method cross-validation |
| **Anomaly Detection** | Flags statistically unusual data points using an ensemble of three methods |
| **Confidence Scoring** | Assigns transparent, weighted confidence scores to every finding |
| **Evidence Validation** | Enforces minimum evidence thresholds before any claim is made |
| **Insight Generation** | Produces safe, factual, human-readable narratives for high-confidence findings |
| **Explicit Abstention** | Openly refuses to generate insights when evidence is insufficient |

The pipeline automatically handles **multi-user datasets** — it detects grouping columns (e.g. `user_id`), runs the full analysis per user, and tags all outputs with the originating user.

> **Explainability** — every insight traces back to a specific method, threshold, and data window.
> **Evidence sufficiency** — claims are only made when statistical evidence meets rigorous thresholds.
> **Explicit abstention** — the system says *"I don't know"* rather than fabricating weak conclusions.

The result is a **deterministic, reproducible** analysis pipeline that a human can audit end-to-end.

---

## ✅ Features

| Category | Feature | Details |
|----------|---------|---------|
| **Data Handling** | Dynamic Schema Detection | Auto-discovers date, numeric, and grouping columns — no hardcoded metric names |
| | Multi-User Support | Detects `user_id` columns and runs per-user analysis automatically |
| **Pattern Analysis** | Rolling-Window Trend Analysis | 7-day recent vs. baseline window comparison with configurable thresholds |
| | Linear Regression Trend Detection | Slope, R², p-value quantification via `scipy.stats.linregress` |
| **Anomaly Detection** | Z-score Detection | Flags global outliers beyond 2.5 standard deviations |
| | IQR Detection | Distribution-robust outlier detection using interquartile range |
| | Rolling Deviation Detection | Catches *contextual* anomalies relative to recent local history |
| **Scoring** | Confidence Scoring Engine | 4-component weighted composite score (0.0–1.0) for every finding |
| | Evidence Sufficiency Validation | Triple-gate: sample size ≥ 7, CV > 0.01, trend magnitude ≥ 5% |
| **Output** | Safe Insight Generation | Factual-only language; `FORBIDDEN_TERMS` filter blocks diagnostic claims |
| | Abstention Framework | First-class output type with structured reason codes |
| **Quality** | Comprehensive Testing | 56 tests, 89% statement coverage across all modules |

---

## 🏗 Architecture

```
                          CSV Dataset
                              │
                              ▼
                    ┌───────────────────┐
                    │    Data Loader    │  Schema discovery, validation,
                    │                   │  date parsing, group detection
                    └────────┬──────────┘
                             │
                    ┌────────┴──────────┐
                    │  Per-User Loop    │  (if user_id detected)
                    │  or Single Pass   │
                    └────────┬──────────┘
                             │
                             ▼
                    ┌───────────────────┐
                    │    Feature        │  Rolling means, rolling std,
                    │    Engineering    │  baseline computation
                    └────────┬──────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
    ┌───────────────────┐     ┌───────────────────┐
    │  Pattern Detector │     │ Anomaly Detector  │
    │                   │     │                   │
    │  Window Comparison│     │  Z-score          │
    │  + Regression     │     │  + IQR            │
    │                   │     │  + Rolling Dev.   │
    └────────┬──────────┘     └────────┬──────────┘
             │                         │
             └────────────┬────────────┘
                          │
                          ▼
                ┌───────────────────┐
                │    Evidence       │  Sample size, variance,
                │    Validator      │  signal strength checks
                └────────┬──────────┘
                         │
                         ▼
                ┌───────────────────┐
                │   Confidence      │  Weighted composite:
                │   Engine          │  sample + trend + consistency
                └────────┬──────────┘       + variance
                         │
                         ▼
                ┌───────────────────┐
                │   Insight         │  confidence ≥ 0.60 → Insight
                │   Generator       │  confidence < 0.60 → Abstention
                └────────┬──────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
     ┌─────────────┐      ┌──────────────┐
     │  Insights   │      │ Abstentions  │
     └──────┬──────┘      └──────┬───────┘
            │                    │
            └────────┬───────────┘
                     │
                     ▼
            ┌───────────────────┐
            │  Report Builder   │  Markdown report
            └────────┬──────────┘  + JSON outputs
                     │
                     ▼
                 outputs/
```

### Module Reference

| Module | Responsibility |
|--------|---------------|
| `data_loader.py` | CSV loading with automatic schema discovery — detects date columns, grouping columns (e.g. `user_id`), and numeric metrics |
| `feature_engineering.py` | Computes rolling statistics (mean, std) over configurable windows to establish behavioral baselines |
| `pattern_detector.py` | Dual-method trend detection: rolling window comparison + linear regression for slope, R², and significance |
| `anomaly_detector.py` | Three-method anomaly ensemble: Z-score, IQR, and rolling deviation with OR-logic |
| `evidence_validator.py` | Triple-gate sufficiency checks: minimum sample size (≥ 7), meaningful variance (CV > 0.01), minimum trend magnitude (≥ 5%) |
| `confidence_engine.py` | Transparent weighted confidence score from four components: sample size, trend strength, consistency, variance stability |
| `insight_generator.py` | Generates evidence-backed narratives for findings passing all gates (confidence ≥ 0.60); issues explicit abstentions otherwise |
| `report_builder.py` | Assembles a professional Markdown report with methodology notes, insight details, anomaly tables, and abstention disclosures |
| `main.py` | Orchestrates the full pipeline with multi-user support: load → detect groups → per-user analysis → aggregate → report |
| `models.py` | All data structures as Python `@dataclass` types: `Pattern`, `Anomaly`, `Insight`, `Abstention`, `ConfidenceScore` |
| `config.py` | Centralized, auditable constants — window sizes, thresholds, weights, forbidden terms, output paths |
| `exceptions.py` | Custom exception hierarchy: `SchemaValidationError`, `InsufficientDataError` for precise error reporting |

---

## 📁 Project Structure

```
chronis-behavioral-insight-engine/
│
├── src/                              # Core pipeline source code
│   ├── __init__.py
│   ├── models.py                     # Dataclass definitions for all types
│   ├── config.py                     # Centralized tunable constants
│   ├── exceptions.py                 # Custom exception classes
│   ├── data_loader.py                # CSV loading + schema + group discovery
│   ├── feature_engineering.py        # Rolling statistics computation
│   ├── pattern_detector.py           # Window comparison + regression
│   ├── anomaly_detector.py           # Z-score + IQR + rolling deviation
│   ├── evidence_validator.py         # Sufficiency gate checks
│   ├── confidence_engine.py          # Weighted confidence scoring
│   ├── insight_generator.py          # Insight + abstention generation
│   ├── report_builder.py             # Markdown report assembly
│   └── main.py                       # Pipeline orchestrator (entry point)
│
├── tests/                            # Comprehensive test suite
│   ├── conftest.py                   # Shared fixtures and test data
│   ├── test_patterns.py              # Pattern detection tests
│   ├── test_anomalies.py             # Anomaly detection tests
│   ├── test_confidence.py            # Confidence scoring tests
│   ├── test_abstention.py            # Abstention logic tests
│   ├── test_data_loader.py           # Data loading + feature engineering
│   └── test_main.py                  # End-to-end integration tests
│
├── data/
│   └── behavioral_data.csv           # Official Chronis assessment dataset
│
├── outputs/                          # Generated analysis results
│   ├── patterns.json
│   ├── anomalies.json
│   ├── insights.json
│   ├── abstentions.json
│   └── report.md
│
├── README.md                         # This file
├── decisions.md                      # Engineering decision rationale
├── DATASET_ANALYSIS.md               # Dataset schema and statistics
├── TASK_A_REQUIREMENT_MATRIX.md      # Assessment compliance matrix
├── INTERVIEW_NOTES.md                # Technical interview preparation
├── DELTA_REPORT.md                   # Before/after comparison report
├── requirements.txt                  # Python dependencies
└── .gitignore
```

| Document | Purpose |
|----------|---------|
| `decisions.md` | In-depth engineering defense of every design choice |
| `DATASET_ANALYSIS.md` | Complete schema, summary statistics, and per-user analysis of the official dataset |
| `TASK_A_REQUIREMENT_MATRIX.md` | Line-by-line compliance mapping of every Task A requirement |
| `INTERVIEW_NOTES.md` | Architecture walkthrough, statistical rationale, and likely Q&A |
| `DELTA_REPORT.md` | Comparison of results before and after switching to the official dataset |

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/SamarthKapdi/chronis-behavioral-insight-engine.git
cd chronis-behavioral-insight-engine
pip install -r requirements.txt
```

### Run the Pipeline

```bash
# Analyze the official Chronis dataset
python src/main.py

# Or analyze your own CSV
python src/main.py path/to/your_data.csv
```

### Run Tests

```bash
python -m pytest --cov=src -v
```

> **Note:** The pipeline auto-discovers the CSV schema at runtime. It handles single-user and multi-user datasets automatically — if a `user_id` column is detected, analysis runs per-user.

---

## 🔬 Methodology

### Pattern Discovery

Trends are detected using **two complementary methods** that must cross-validate each other:

**1. Rolling Window Comparison**
Compares the mean of the most recent 7 days against the preceding 7 days. If the percent change exceeds ±10%, the trend is flagged as increasing or decreasing.

```
Percent Change = (recent_mean - baseline_mean) / baseline_mean × 100
```

**2. Linear Regression Analysis**
Fits an OLS regression line across the full analysis window using `scipy.stats.linregress`. Extracts:
- **Slope** — magnitude of daily change
- **R²** — proportion of variance explained by the trend
- **p-value** — statistical significance (threshold: p < 0.05)

**Cross-Validation:** When both methods agree — the window comparison shows a significant shift AND regression confirms a statistically significant slope — confidence in the pattern is substantially higher.

---

### Anomaly Detection

A data point is flagged as anomalous if **any** of three independent methods triggers:

| Method | How It Works | Strength |
|--------|-------------|----------|
| **Z-score** (threshold: 2.5σ) | Measures standard deviations from the global mean | Sensitive to global outliers |
| **IQR** (1.5× multiplier) | Flags values outside Q1 − 1.5×IQR to Q3 + 1.5×IQR | Robust to non-normal distributions |
| **Rolling Deviation** (2.0σ window) | Flags values deviating from the 7-day rolling mean by > 2× rolling std | Catches *contextual* anomalies |

**Why OR-logic?** Each method has a specific blind spot. In behavioral health contexts, **false negatives are more costly than false positives**.

---

### Confidence Scoring

Every finding receives a continuous confidence score (0.0–1.0) computed as a **weighted average**:

```
confidence = (0.25 × sample_score)
           + (0.35 × trend_score)
           + (0.25 × consistency_score)
           + (0.15 × variance_score)
```

| Component | Weight | What It Measures |
|-----------|--------|------------------|
| `sample_score` | **0.25** | More data → more reliable. Saturates at n=30 |
| `trend_score` | **0.35** | Larger magnitude change → stronger signal |
| `consistency_score` | **0.25** | Trend visible across more days → more credible |
| `variance_score` | **0.15** | Lower noise → trend less likely to be random |

A finding is promoted to an **Insight** only if confidence **≥ 0.60**.

---

### Abstention Logic

> *"Abstention is a feature, not a failure."*

| Trigger | Condition | Rationale |
|---------|-----------|-----------|
| **Insufficient Data** | Sample size < 7 | Fewer than 7 points can't establish a weekly pattern |
| **Weak Signal** | CV < 0.01 or trend < 5% | If data barely varies, there's nothing meaningful to report |
| **Low Confidence** | Composite score < 0.60 | Evidence exists but is not compelling enough |

---

## 📊 Example Outputs

All examples below are **real outputs** generated from the official Chronis assessment dataset.

### Insight (from `insights.json`)

```json
{
  "insight": "[U4] Average daily deep work hours decreased by 55.6% over the last 7 days (from 4.3 to 1.9).",
  "metric": "deep_work_hours",
  "confidence": 0.860,
  "confidence_components": {
    "sample_score": 1.0,
    "trend_score": 1.0,
    "consistency_score": 0.667,
    "variance_score": 0.619,
    "final_confidence": 0.860
  },
  "evidence": "Recent 7-day average: 1.9, Previous 7-day average: 4.3",
  "reasoning": "[U4] Consistent decreasing trend observed. Linear regression slope: -0.0647/day (R²=0.122, p=0.0581). 4 of last 7 days showed day-over-day decreasing."
}
```

### Anomaly (from `anomalies.json`)

```json
{
  "date": "2026-01-10",
  "metric": "steps",
  "observed_value": 4362.0,
  "expected_value": 8492.67,
  "deviation": -1.80,
  "methods_triggered": ["rolling_deviation"],
  "explanation": "[U2] steps unusually low: observed 4362 vs expected range 3901-13085 (1.8 standard deviations below mean)"
}
```

### Abstention (from `abstentions.json`)

```json
{
  "metric": "screen_time_hours",
  "status": "ABSTAIN",
  "reason": "[U1] Evidence insufficient: Trend magnitude too small: 3.4% below 5.0% minimum",
  "evidence_result": {
    "metric": "screen_time_hours",
    "is_sufficient": false,
    "sample_size": 30,
    "has_sufficient_variance": true,
    "has_sufficient_signal": false,
    "reasons": ["Trend magnitude too small: 3.4% below 5.0% minimum"]
  }
}
```

---

## 🧪 Testing

```bash
python -m pytest --cov=src -v
```

```
56 passed in 4.33s
```

### Test Suite

| Test Module | Tests | Coverage Focus |
|-------------|-------|----------------|
| `test_abstention.py` | 8 | Abstention triggers, reason codes, insight generation, output safety, report structure |
| `test_anomalies.py` | 8 | Known anomaly detection, normal data baseline, metadata validation, edge cases |
| `test_confidence.py` | 15 | Component scoring, weight validation, threshold behavior, evidence sufficiency |
| `test_data_loader.py` | 10 | Schema discovery, date heuristics, rolling stats, missing values, edge cases |
| `test_main.py` | 7 | Pipeline orchestration, path resolution, JSON serialization, E2E integration |
| `test_patterns.py` | 8 | Trend direction, regression statistics, insufficient data, multi-metric detection |

### Coverage Report

| Module | Stmts | Miss | Cover |
|--------|-------|------|-------|
| `__init__.py` | 0 | 0 | **100%** |
| `anomaly_detector.py` | 124 | 16 | **87%** |
| `confidence_engine.py` | 42 | 1 | **98%** |
| `config.py` | 40 | 0 | **100%** |
| `data_loader.py` | 95 | 18 | **81%** |
| `evidence_validator.py` | 41 | 1 | **98%** |
| `exceptions.py` | 4 | 0 | **100%** |
| `feature_engineering.py` | 44 | 2 | **95%** |
| `insight_generator.py` | 66 | 9 | **86%** |
| `main.py` | 108 | 33 | **69%** |
| `models.py` | 76 | 0 | **100%** |
| `pattern_detector.py` | 74 | 9 | **88%** |
| `report_builder.py` | 78 | 0 | **100%** |
| **TOTAL** | **792** | **89** | **89%** |

---

## 🎯 Design Decisions

Full rationale is documented in [`decisions.md`](decisions.md). Key choices:

| Decision | Rationale |
|----------|-----------|
| **Rolling windows + regression** over ARIMA | ARIMA is overpowered for 30-day datasets and produces opaque outputs. Rolling windows are intuitive; regression adds statistical rigor. |
| **Three anomaly methods** over one | Each method has a blind spot. The ensemble compensates. |
| **Weighted composite confidence** over binary pass/fail | Continuous scoring preserves granularity. |
| **Explicit abstention** as first-class output | In behavioral health, a wrong insight is worse than no insight. |
| **No deep learning, no LLM APIs** | The goal is explainability, not sophistication. Zero randomness, fully deterministic. |
| **Dynamic schema + group detection** | Makes the pipeline portable to any behavioral CSV. Automatically handles single-user and multi-user datasets. |

---

## ⚠️ Limitations

| Limitation | Impact |
|------------|--------|
| **Single-metric analysis** | Each metric is analyzed independently per user. No cross-metric correlation. |
| **No causal inference** | Correlations and trends are reported, never causes. |
| **No cross-user comparison** | Each user is analyzed in isolation. The system doesn't compare User A vs. User B. |
| **No forecasting** | The system describes what happened, not what will happen next. |
| **7-day window floor** | Behavioral changes shorter than 7 days are smoothed out. |
| **No seasonality detection** | Day-of-week effects are not modeled. |

---

## 🔮 Future Improvements

- **Cross-metric correlation analysis** — Detect relationships between metrics using Pearson/Spearman correlation with lag analysis
- **Cross-user comparison** — Compare behavioral profiles across users to identify population-level trends
- **Multivariate behavioral modeling** — Jointly analyze metrics to surface compound patterns
- **Seasonality detection** — Identify day-of-week and cyclical effects
- **Adaptive thresholds** — Per-metric thresholds that adjust based on individual baseline variability
- **Online / incremental learning** — Support appending new rows and re-analyzing only the delta
- **Behavioral clustering** — Group similar days or time periods by behavioral profile
- **Interactive visualization** — Generate HTML dashboards with trend lines, anomaly markers, and confidence breakdowns

---

## 📈 Assessment Results

Pipeline execution on the **official Chronis assessment dataset** (`Chronis_TaskA_Synthetic_Behavioral_Data_v2-2.csv`):

| Metric | Value |
|--------|-------|
| **Dataset** | 150 rows, 5 users (U1–U5), 30 days each |
| **Metrics Analyzed** | `steps`, `sleep_hours`, `screen_time_hours`, `deep_work_hours`, `exercise_minutes` |
| **Patterns Detected** | 25 (5 per user) |
| **Anomalies Detected** | 3 |
| **Insights Generated** | 7 |
| **Abstentions Issued** | 18 |
| **Tests Passed** | 56 / 56 |
| **Statement Coverage** | 89% |

The system generated **7 high-confidence insights** across 4 users and **explicitly abstained on 18 metrics** where evidence was insufficient. Notably, `deep_work_hours` was independently flagged as declining for users U2, U3, and U4 — a cross-user pattern the system surfaced without any cross-user analysis code.

---

## 🛠 Tech Stack

| Tool | Purpose |
|------|---------|
| **Python 3.11+** | Runtime |
| **pandas** | Data loading and manipulation |
| **numpy** | Numerical computation |
| **scipy** | Statistical functions (`linregress`, `zscore`) |
| **pytest** | Test framework |
| **pytest-cov** | Coverage reporting |

**No deep learning. No LLM APIs. No randomness. Purely statistical and deterministic.**

---

## 📄 License

This project was built as a technical demonstration for the Chronis AI/ML Internship Assessment.

---

<div align="center">

*Built with statistical rigor, engineering discipline, and the conviction that knowing when not to speak is as important as knowing what to say.*

</div>
