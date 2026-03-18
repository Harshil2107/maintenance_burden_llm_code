# Review Discussion Activity

This directory contains the analysis notebooks and results for the following research question:

> **RQ:** Is AI authorship associated with higher review discussion activity in pull requests, and does this association persist when bot-generated activity is excluded?

## Notebooks

Two notebooks are provided, one per dataset:

| Notebook | Dataset |
|---|---|
| `review_burden_250st.ipynb` | Repositories with ≥ 250 stars |
| `review_burden_500st.ipynb` | Repositories with ≥ 500 stars |

Each notebook covers:

1. **Data collection** — fetches review comments and reviewer metadata from the GitHub API
2. **Descriptive statistics** — compares AI-authored vs. human-authored PRs across review activity metrics
3. **Wilcoxon signed-rank tests** — paired statistical tests for each metric
4. **Regression analysis** — models controlling for covariates (PR size, language, etc.)
5. **Visualizations** — distribution plots and coefficient plots

## Prerequisites

A GitHub personal access token is required to speed up API data collection. Set it as the `GITHUB_TOKEN` variable at the top of each notebook.

## Running the Analysis

The **data collection cells** do not need to be re-run as all the required input data is already committed to this repository.

To reproduce the results, you can run the **experiment cells** (Wilcoxon tests and regression analysis) as these load the pre-collected data directly.

## Output Files

| File | Description |
|---|---|
| `wilcoxon_paired_tests_250st.csv` | Wilcoxon test results for the 250-star dataset |
| `wilcoxon_paired_tests_500st.csv` | Wilcoxon test results for the 500-star dataset |
| `regression_summary_250st.csv` | Regression model summaries for the 250-star dataset |
| `regression_summary_500st.csv` | Regression model summaries for the 500-star dataset |