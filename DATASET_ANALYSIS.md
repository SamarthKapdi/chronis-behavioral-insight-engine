# Dataset Analysis

This document provides a comprehensive analysis of the official **Chronis Task A** assessment dataset located at `data/behavioral_data.csv`. The dataset is sourced from the file `Chronis_TaskA_Synthetic_Behavioral_Data_v2-2.csv` and contains **150 daily observations** across **5 users** (U1–U5), each with **30 days** of behavioral and activity metrics spanning from **2026-01-01** to **2026-01-30**.

---

## 1. Dataset Source Attribution

| Attribute          | Value                                                   |
|--------------------|---------------------------------------------------------|
| **Source File**    | `Chronis_TaskA_Synthetic_Behavioral_Data_v2-2.csv`      |
| **Local Path**     | `data/behavioral_data.csv`                              |
| **Dataset Type**   | Official Chronis assessment — synthetic behavioral data |
| **Total Rows**     | 151 (1 header + 150 data rows)                          |
| **Total Users**    | 5 (U1, U2, U3, U4, U5)                                 |
| **Days per User**  | 30 (2026-01-01 to 2026-01-30)                           |
| **Total Columns**  | 7                                                       |
| **Missing Values** | 0                                                       |

---

## 2. Schema

| Column              | Type    | Description                                   | Range / Values              |
|---------------------|---------|-----------------------------------------------|-----------------------------|
| `user_id`           | string  | Unique user identifier                        | U1, U2, U3, U4, U5         |
| `date`              | string  | Daily date in YYYY-MM-DD format               | 2026-01-01 to 2026-01-30   |
| `steps`             | int64   | Daily step count                              | ~4,000 – 12,000            |
| `sleep_hours`       | float64 | Hours of sleep per night                      | ~5.5 – 8.5                 |
| `screen_time_hours` | float64 | Daily screen time in hours                    | ~2.1 – 8.9                 |
| `deep_work_hours`   | float64 | Hours of focused/deep work per day            | ~0.5 – 6.0                 |
| `exercise_minutes`  | int64   | Minutes of exercise/physical activity per day | ~2 – 90                    |

---

## 3. Summary Statistics (All Users Combined)

| Statistic | steps       | sleep_hours | screen_time_hours | deep_work_hours | exercise_minutes |
|-----------|-------------|-------------|-------------------|-----------------|------------------|
| **count** | 150         | 150         | 150               | 150             | 150              |
| **mean**  | 7,962.46    | 7.08        | 5.72              | 3.39            | 44.49            |
| **std**   | 2,402.43    | 0.90        | 2.08              | 1.67            | 25.65            |
| **min**   | 4,020       | 5.50        | 2.10              | 0.50            | 2                |
| **25%**   | 5,848.50    | 6.30        | 3.93              | 1.90            | 22.00            |
| **50%**   | 7,769.00    | 7.10        | 5.90              | 3.45            | 45.00            |
| **75%**   | 9,950.75    | 7.98        | 7.58              | 4.90            | 66.00            |
| **max**   | 11,969      | 8.50        | 8.90              | 6.00            | 90               |

---

## 4. Missing Values

| Column              | Missing Count | Percentage |
|---------------------|---------------|------------|
| `user_id`           | 0             | 0.0%       |
| `date`              | 0             | 0.0%       |
| `steps`             | 0             | 0.0%       |
| `sleep_hours`       | 0             | 0.0%       |
| `screen_time_hours` | 0             | 0.0%       |
| `deep_work_hours`   | 0             | 0.0%       |
| `exercise_minutes`  | 0             | 0.0%       |

> **The dataset has zero missing values across all 150 rows and 7 columns.** No imputation or handling of missing data is required.

---

## 5. Per-User Summary Statistics

### 5.1 Steps

| User | Count | Mean     | Std      | Min   | 25%      | 50%     | 75%       | Max    |
|------|-------|----------|----------|-------|----------|---------|-----------|--------|
| U1   | 30    | 7,872.00 | 2,636.86 | 4,020 | 5,593.00 | 7,546.0 | 10,268.00 | 11,922 |
| U2   | 30    | 8,492.67 | 2,295.94 | 4,116 | 6,919.25 | 8,935.0 | 10,096.00 | 11,816 |
| U3   | 30    | 7,803.40 | 2,313.35 | 4,104 | 6,211.00 | 7,773.5 | 9,248.25  | 11,900 |
| U4   | 30    | 7,852.57 | 2,380.64 | 4,034 | 5,887.75 | 7,465.0 | 9,878.75  | 11,969 |
| U5   | 30    | 7,791.67 | 2,458.25 | 4,068 | 5,661.75 | 7,433.5 | 9,998.00  | 11,891 |

### 5.2 Sleep Hours

| User | Count | Mean | Std  | Min  | 25%  | 50%  | 75%  | Max  |
|------|-------|------|------|------|------|------|------|------|
| U1   | 30    | 7.10 | 0.90 | 5.50 | 6.40 | 7.00 | 8.10 | 8.40 |
| U2   | 30    | 7.14 | 0.91 | 5.70 | 6.50 | 7.10 | 8.13 | 8.40 |
| U3   | 30    | 6.94 | 0.90 | 5.70 | 6.20 | 6.70 | 7.88 | 8.50 |
| U4   | 30    | 7.02 | 0.99 | 5.50 | 6.05 | 7.30 | 7.85 | 8.50 |
| U5   | 30    | 7.19 | 0.84 | 5.60 | 6.40 | 7.15 | 8.00 | 8.40 |

### 5.3 Screen Time Hours

| User | Count | Mean | Std  | Min  | 25%  | 50%  | 75%  | Max  |
|------|-------|------|------|------|------|------|------|------|
| U1   | 30    | 5.92 | 2.28 | 2.10 | 4.18 | 6.30 | 7.68 | 8.90 |
| U2   | 30    | 5.75 | 1.94 | 2.50 | 3.95 | 6.15 | 7.33 | 8.90 |
| U3   | 30    | 5.50 | 2.21 | 2.30 | 3.70 | 4.90 | 7.88 | 8.90 |
| U4   | 30    | 5.69 | 2.21 | 2.10 | 3.73 | 5.95 | 7.60 | 8.90 |
| U5   | 30    | 5.73 | 1.87 | 2.60 | 4.33 | 5.65 | 7.20 | 8.90 |

### 5.4 Deep Work Hours

| User | Count | Mean | Std  | Min  | 25%  | 50%  | 75%  | Max  |
|------|-------|------|------|------|------|------|------|------|
| U1   | 30    | 3.88 | 1.73 | 0.60 | 2.13 | 4.40 | 5.38 | 6.00 |
| U2   | 30    | 3.13 | 1.68 | 0.70 | 1.75 | 2.95 | 4.55 | 6.00 |
| U3   | 30    | 3.04 | 1.63 | 0.80 | 1.33 | 3.05 | 4.78 | 5.60 |
| U4   | 30    | 3.37 | 1.63 | 0.70 | 2.10 | 3.50 | 4.68 | 6.00 |
| U5   | 30    | 3.55 | 1.67 | 0.50 | 2.38 | 3.70 | 5.05 | 5.90 |

### 5.5 Exercise Minutes

| User | Count | Mean  | Std   | Min | 25%   | 50%  | 75%   | Max |
|------|-------|-------|-------|-----|-------|------|-------|-----|
| U1   | 30    | 38.67 | 26.75 | 2   | 15.25 | 40.0 | 61.75 | 87  |
| U2   | 30    | 47.83 | 26.69 | 4   | 24.00 | 54.0 | 64.75 | 90  |
| U3   | 30    | 43.83 | 22.44 | 5   | 25.00 | 46.5 | 60.75 | 86  |
| U4   | 30    | 40.00 | 28.12 | 2   | 17.50 | 35.0 | 67.75 | 85  |
| U5   | 30    | 52.13 | 23.04 | 7   | 36.75 | 53.5 | 74.50 | 86  |

---

## 6. Observed Patterns

### 6.1 Cross-Variable Correlations

Correlations between numeric variables are notably **weak** across the dataset:

| Pair                                 | Correlation | Interpretation                       |
|--------------------------------------|-------------|--------------------------------------|
| sleep_hours ↔ exercise_minutes       | +0.204      | Weak positive — slightly more sleep on more active days |
| screen_time_hours ↔ exercise_minutes | +0.187      | Weak positive — no screen-vs-exercise trade-off observed |
| screen_time_hours ↔ sleep_hours      | +0.131      | Weak positive — minimal relationship  |
| deep_work_hours ↔ exercise_minutes   | +0.127      | Weak positive — negligible            |
| steps ↔ sleep_hours                  | +0.064      | Near zero — essentially independent   |
| steps ↔ screen_time_hours            | +0.002      | Near zero — no relationship           |
| steps ↔ deep_work_hours              | −0.043      | Near zero — essentially independent   |
| steps ↔ exercise_minutes             | −0.057      | Near zero — steps and exercise are independent |

> **Key Insight:** The behavioral variables in this dataset are largely **uncorrelated**, suggesting they vary independently across users and days. There is no strong trade-off pattern (e.g., more screen time ≠ less exercise) in the data.

### 6.2 Temporal Patterns (Early vs. Late Month)

Comparing the first half (days 1–15) to the second half (days 16–30) of the observation period:

| Metric            | Early (1–15) | Late (16–30) | Δ Change  |
|-------------------|--------------|--------------|-----------|
| steps             | 8,036.91     | 7,888.01     | −148.90   |
| sleep_hours       | 7.03         | 7.12         | +0.09     |
| screen_time_hours | 5.53         | 5.91         | +0.38     |
| deep_work_hours   | 3.43         | 3.36         | −0.07     |
| exercise_minutes  | 40.81        | 48.17        | +7.36     |

> **Key Insight:** There is a modest increase in screen time (+0.38 hrs) and exercise minutes (+7.36 min) in the second half of the month. Steps show a slight decrease. Overall, no dramatic temporal trends are present — the data is relatively **stationary** across the 30-day window.

### 6.3 Per-User Behavioral Profiles

- **U2** has the highest average step count (8,493) and exercises moderately (47.8 min/day).
- **U5** is the most physically active by exercise duration (52.1 min/day) despite average step counts.
- **U1** logs the most deep work hours (3.88 hrs/day) but the least exercise (38.7 min/day).
- **U3** has the lowest average sleep (6.94 hrs) and the lowest deep work (3.04 hrs).
- **U4** exhibits the highest variability in exercise (std = 28.1) and achieved the single-highest step count in the dataset (11,969).

### 6.4 Distribution Characteristics

- **Steps** span a wide range (~4,000–12,000) with a roughly uniform spread, as evidenced by the large standard deviation (2,402) relative to the mean (7,962).
- **Sleep hours** are tightly clustered (std = 0.90) around 7.1 hours, with no extreme outliers.
- **Screen time** shows substantial variability (std = 2.08) across a 2.1–8.9 hour range, with a roughly symmetric distribution around the median (5.9 hrs).
- **Deep work hours** are broadly distributed (0.5–6.0), with the distribution slightly right-skewed (median 3.45 < mean 3.39 is approximately centered).
- **Exercise minutes** have the highest relative variability (CV ≈ 57.7%), ranging from near-zero (2 min) to 90 minutes, indicating highly inconsistent exercise habits across and within users.

---

## 7. Assumptions

1. **Multi-User Dataset:** The dataset represents 5 distinct users (U1–U5), each contributing exactly 30 daily observations. All analysis should account for potential between-user variability.

2. **Synthetic Data:** This is an official synthetic dataset generated for the Chronis Task A assessment. The data is not derived from real human subjects, and any patterns reflect the data generation process rather than real-world behavioral dynamics.

3. **Complete Data:** The dataset has zero missing values across all 1,050 cells (150 rows × 7 columns). No imputation or missingness-handling strategies are needed.

4. **Daily Granularity:** Each row represents one calendar day for one user. All 30 days (2026-01-01 through 2026-01-30) are present for each user, with no duplicates or gaps.

5. **Independence Assumption:** Given the weak correlations observed (all |r| < 0.21), behavioral metrics can be treated as approximately independent for modeling purposes, though temporal autocorrelation within users has not been fully assessed.

6. **Plausible Metric Ranges:** All recorded values fall within realistic ranges:
   - Steps: 4,020–11,969 (moderately to very active)
   - Sleep: 5.5–8.5 hours (within normal adult range)
   - Screen time: 2.1–8.9 hours (typical modern usage)
   - Deep work: 0.5–6.0 hours (varying focus levels)
   - Exercise: 2–90 minutes (sedentary to highly active days)

7. **No Obvious Anomalies:** Unlike real-world data, this synthetic dataset does not exhibit extreme outliers, measurement errors, or implausible values. All observations appear well-behaved within their respective ranges.

8. **Stationarity:** No strong temporal trends were detected across the 30-day window, supporting the assumption that the underlying data-generating process is approximately stationary.
