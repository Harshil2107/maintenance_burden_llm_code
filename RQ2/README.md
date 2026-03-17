# RQ2: Code Churn & Stability Analysis

## Research Questions

- **RQ2 (Base):** Does AI-generated code churn more or less than human code after merging?
- **RQ2a:** Do AI agents work on colder (less active) files, which could explain lower churn?
- **RQ2b:** After controlling for file heat, PR size, language, and task type, does author type still predict churn?

## Prerequisites

```bash
cd RQ2
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the Full Pipeline

### Step 1: Base Churn Analysis (already completed)

Computes churn ratio and churn frequency for each PR using `git blame --reverse`.

```bash
python line_churn_analysis.py
```

> **Note:** This step was already run. Pre-computed results are in `plotting_csv/pr_level_metrics_500st.csv` (312 rows). Only re-run if you need fresh data.

**Output:** `plotting_csv/pr_level_metrics_500st.csv`

### Step 2: Extract Covariates

Clones each repo, runs `git diff` to determine dominant language per PR, and extracts task type (feat/fix) from the dataset.

```bash
python extract_covariates.py
```

**Runtime:** ~2-3 hours (clones repos with `--depth 1`)
**Output:** `covariates.csv` (640 rows — language, task type, repo ID per PR)

### Step 3: File Heat Analysis (RQ2a)

Computes a "file heat score" per PR — the average number of commits touching the changed files in the 90 days before the PR was merged. Generates comparison plots.

```bash
python file_heat_analysis.py
```

**Runtime:** ~4-6 hours (clones repos and runs `git log` per file)
**Output:**
- `file_heat_scores.csv` (594 rows)
- `plots_heat/file_heat_boxplot.png`
- `plots_heat/file_heat_density.png`

### Step 4: Regression Analysis (RQ2b)

Merges churn data + covariates + file heat scores, then fits 3 OLS regression models with clustered standard errors to test whether author type predicts churn.

```bash
python regression_analysis.py
```

**Runtime:** < 10 seconds
**Output:** `regression_results/regression_report.md`

## Scripts

| Script | Purpose |
|--------|---------|
| `line_churn_analysis.py` | Line-level churn via `git blame --reverse` |
| `churn_analysis.py` | Basic 90-day post-merge churn ratio (pilot) |
| `analyze_rq2.py` | Conditional churn intensity analysis + plots |
| `extract_covariates.py` | Extract dominant language & task type per PR |
| `file_heat_analysis.py` | RQ2a — file heat scores (commits in 90d pre-merge) |
| `regression_analysis.py` | RQ2b — hierarchical OLS regression |

## Key Findings (N=268)

- **Author type (AI vs Human) is not a significant predictor of churn** in any model (p > 0.4).
- **File heat is the strongest predictor** — files with more prior activity churn more (p < 0.003).
- **Language matters** — Python churns least; Go and Rust churn more.
- **Task type (feat vs fix) does not predict churn** (p > 0.5).
