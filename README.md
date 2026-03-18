# Maintenance Burden of LLM-Generated Code

This repository contains the dataset generation scripts, analysis notebooks, and results for studying the maintenance burden and code stability of AI-generated code compared to human-authored code in open-source repositories.

The project investigates two primary research dimensions:
1. **Review Discussion Activity** (Review Burden)
2. **Code Churn & Stability Analysis** (Maintenance Burden)

## Repository Structure

```text
.
├── datasets/                           # Core dataset files (containing AI vs. Human PRs)
├── 250st/                              # Outputs and results for repositories with >= 250 stars
├── 500st/                              # Outputs and results for repositories with >= 500 stars
├── RQ2/                                # Code churn and post-merge stability analysis scripts
├── review_burdern_rq/                  # Review discussion and PR activity analysis notebooks
├── code_quality_analysis_appendix/     # Additional code quality metric analysis
└── create_dataset.ipynb                # Main notebook used for initial dataset collection and creation
```

## Dataset Creation

The root notebook `create_dataset.ipynb` handles the initial data pipeline. It is responsible for gathering pull requests from GitHub across various projects (categorized into repositories with ≥ 250 stars and ≥ 500 stars) and classifying them by author type (AI vs. Human).

## Research Questions & Analysis

### 1. Review Discussion Activity (`/review_burdern_rq`)
**RQ:** *Is AI authorship associated with higher review discussion activity in pull requests, and does this association persist when bot-generated activity is excluded?*

This module uses Jupyter notebooks to analyze review comments and reviewer metadata to determine if AI-authored PRs require more review effort than human-authored ones.
- **Methods used:** Descriptive statistics, Wilcoxon signed-rank paired tests, and Regression analysis controlling for PR size and language.
- For more detailed instructions on reproducing this analysis, see the [Review Burden README](./review_burdern_rq/README.md).

### 2. Code Churn & Stability Analysis (`/RQ2`)
**RQ:** *Does AI-generated code churn more or less than human code after merging?*

This directory contains Python scripts evaluating line-level churn via `git blame --reverse`. 
- **RQ2a:** Examines if AI agents work on colder (less active) files, which might inherently explain differences in churn.
- **RQ2b:** Applies hierarchical OLS regression models to see if author type predicts churn after controlling for file heat, PR size, language, and task type (feat vs. fix).
- **Key Findings:** Author type (AI vs. Human) is **not** a significant predictor of churn. File heat (prior activity) is the strongest predictor, and language also plays a significant role.
- For more detailed scripts and pipeline instructions, see the [RQ2 README](./RQ2/README.md).

## Getting Started

### Prerequisites
- Python 3.8+
- Jupyter Notebook
- A GitHub Personal Access Token (PAT) for API requests.

### Setup
Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/Harshil2107/maintenance_burden_llm_code.git
cd maintenance_burden_llm_code

python3 -m venv venv
source venv/bin/activate
pip install -r RQ2/requirements.txt # (and other dependencies as needed by Jupyter)
```

*(Note: Ensure you export your `GITHUB_TOKEN` in your environment or set it in the respective notebooks before running data collection modules.)*

## Reproducing the Results
Most of the intensive data-collection outputs are already provided in the repository.
- **To reproduce Review Burden findings:** Open the notebooks in `/review_burdern_rq` and run the experiment cells (which load pre-collected data).
- **To reproduce Code Churn findings:** Navigate to `/RQ2` and run the regression scripts against the provided CSVs (e.g., `python regression_analysis.py`).
