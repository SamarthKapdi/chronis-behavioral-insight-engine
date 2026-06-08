# Task A Requirement Matrix

## Official Dataset Verification

**Status**: The official Chronis assessment dataset is now in use.
**File**: `Chronis_TaskA_Synthetic_Behavioral_Data_v2-2.csv` (copied to `data/behavioral_data.csv`)
**Schema**: `user_id, date, steps, sleep_hours, screen_time_hours, deep_work_hours, exercise_minutes`
**Rows**: 150 data rows (5 users x 30 days each)
**Users**: U1, U2, U3, U4, U5
**Missing Values**: None

---

## Requirements Compliance Matrix

| Requirement | Implemented? | Evidence | File |
|-------------|--------------|----------|------|
| **Core Components** |
| 1. Pattern Discovery | Yes | Rolling window comparisons + linear regression, run per-user for grouped datasets. | `src/pattern_detector.py` |
| 2. Anomaly Detection | Yes | Multi-method ensemble (Z-score, IQR, Rolling Deviation) with OR-logic, run per-user. | `src/anomaly_detector.py` |
| 3. Insight Generation | Yes | Translates high-confidence patterns and anomalies into safe, factual, natural-language insights. Each insight is tagged with its `user_id`. | `src/insight_generator.py` |
| 4. Evidence Sufficiency / Abstention | Yes | Calculates sample size, variance, and trend strength. Abstains if data is insufficient (<7 days) or low confidence (<0.60). | `src/confidence_engine.py`, `src/evidence_validator.py` |
| **Deliverables** |
| GitHub-ready repository | Yes | Full standard Python project structure with modular design and `.gitignore`. | Repository Root |
| `requirements.txt` | Yes | Minimal dependencies (`pandas`, `numpy`, `scipy`, `pytest`). | `requirements.txt` |
| Single-command execution | Yes | Pipeline runnable via `python src/main.py`. | `src/main.py` |
| Worked examples generated | Yes | E2E execution on official dataset generates `insights.json` (7), `anomalies.json` (3), `abstentions.json` (18), `patterns.json` (25), `report.md`. | `outputs/*` |
| Test suite using `pytest` | Yes | 56 tests passing with 89% coverage. | `tests/*` |
| `decisions.md` | Yes | Comprehensive engineering defense of all statistical and architectural choices. | `decisions.md` |
| `README.md` | Yes | Clear setup, execution instructions, architecture, methodology, and real output examples. | `README.md` |
| `DATASET_ANALYSIS.md` | Yes | Schema, summary statistics, per-user analysis, and observed patterns of the official dataset. | `DATASET_ANALYSIS.md` |
| **Architectural / Goal Requirements** |
| Dynamic Schema Adaptation | Yes | `data_loader.py` dynamically infers date, metric, and group columns at runtime. The same code processed both the old 7-metric single-user dataset and the new 5-metric 5-user dataset without any hardcoded changes. | `src/data_loader.py` |
| Multi-User Support | Yes | Automatically detects `user_id` grouping column and runs the full analysis pipeline per-user. Results are tagged with the originating user. | `src/data_loader.py`, `src/main.py` |
| Explainability | Yes | Uses transparent stats (regression, Z-score, percentages). Every insight includes confidence breakdown and reasoning chain. | `decisions.md`, `src/pattern_detector.py` |
| Engineering Quality | Yes | Fully typed, modular, dataclass-driven data models, consistent error handling, and robust logging. | `src/models.py`, `src/*.py` |
| Reliability | Yes | Graceful degradation on edge cases (e.g., all-NaN columns, flatline metrics, short datasets, multi-user grouping). | `src/main.py`, `src/confidence_engine.py` |
| Testability | Yes | Pure functions and isolated classes enable unit testing without complex mocking. | `tests/*` |
| Safe Insight Generation | Yes | Factual-only language policy enforced by `config.FORBIDDEN_TERMS`. | `src/config.py`, `src/insight_generator.py` |
