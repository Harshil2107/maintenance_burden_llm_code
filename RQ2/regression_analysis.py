"""
RQ2b: Regression Analysis — Does File Heat Explain Churn Differences?

Fits three OLS regression models to test whether author type (AI vs Human)
predicts churn after controlling for PR size, task type, language, and
file heat. The key question is whether the author_type coefficient shrinks
or loses significance when file heat is added as a covariate.

Prerequisites:
  - RQ2/plotting_csv/pr_level_metrics_500st.csv  (churn metrics)
  - RQ2/file_heat_scores.csv                     (from file_heat_analysis.py)
  - RQ2/covariates.csv                            (from extract_covariates.py)
"""

import os
import sys
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats as sp_stats

warnings.filterwarnings("ignore")

import functools
print = functools.partial(print, flush=True)

# ── Configuration ────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
CHURN_CSV    = os.path.join(SCRIPT_DIR, "plotting_csv",
                            "pr_level_metrics_500st.csv")
HEAT_CSV     = os.path.join(SCRIPT_DIR, "file_heat_scores.csv")
COVAR_CSV    = os.path.join(SCRIPT_DIR, "covariates.csv")
OUTPUT_DIR   = os.path.join(SCRIPT_DIR, "regression_results")


def load_and_merge():
    """Load all CSVs and merge into a single regression-ready dataframe."""

    # ── Churn data ────────────────────────────────────────────────────────
    churn = pd.read_csv(CHURN_CSV)
    print(f"Churn data: {len(churn)} rows")
    # Columns: repo, pr, type, added, churned, events, ratio
    churn = churn.rename(columns={"type": "author_type", "added": "lines_added",
                                   "churned": "churned_lines",
                                   "ratio": "churn_ratio"})

    # ── File heat data ────────────────────────────────────────────────────
    if os.path.exists(HEAT_CSV):
        heat = pd.read_csv(HEAT_CSV)
        print(f"Heat data: {len(heat)} rows")
        # Columns: repo, pr, author_type, mean_file_heat, ...
        heat = heat[["repo", "pr", "mean_file_heat"]]
    else:
        print(f"⚠ Heat CSV not found: {HEAT_CSV}. Models with heat will be skipped.")
        heat = None

    # ── Covariates data ───────────────────────────────────────────────────
    if os.path.exists(COVAR_CSV):
        covar = pd.read_csv(COVAR_CSV)
        print(f"Covariates data: {len(covar)} rows")
        # Columns: repo, pr, author_type, dominant_language, task_type, agent
        covar = covar[["repo", "pr", "dominant_language", "task_type"]]
    else:
        print(f"⚠ Covariates CSV not found: {COVAR_CSV}. Using fallback task_type.")
        covar = None

    # ── Merge ─────────────────────────────────────────────────────────────
    df = churn.copy()

    if covar is not None:
        df = df.merge(covar, on=["repo", "pr"], how="left")
    else:
        df["dominant_language"] = "Unknown"
        df["task_type"] = "unknown"

    if heat is not None:
        df = df.merge(heat, on=["repo", "pr"], how="left")

    print(f"Merged dataframe: {len(df)} rows")
    return df, heat is not None


def prepare_regression_df(df):
    """Clean and prepare the dataframe for regression."""

    # Log-transform churn metrics (add small constant for zeros)
    df["log_CR"] = np.log(df["churn_ratio"] + 0.01)

    # Churn frequency = events / lines_added
    df["RF"] = df["events"] / df["lines_added"].replace(0, np.nan)
    df["log_RF"] = np.log(df["RF"].fillna(0) + 0.01)

    # Encode categoricals
    df["author_type"] = pd.Categorical(df["author_type"])

    if "task_type" in df.columns:
        # Collapse rare task types into "other"
        type_counts = df["task_type"].value_counts()
        rare_types = type_counts[type_counts < 5].index
        df["task_type"] = df["task_type"].apply(
            lambda x: "other" if x in rare_types else x)
        df["task_type"] = pd.Categorical(df["task_type"])

    if "dominant_language" in df.columns:
        lang_counts = df["dominant_language"].value_counts()
        rare_langs = lang_counts[lang_counts < 5].index
        df["dominant_language"] = df["dominant_language"].apply(
            lambda x: "Other" if x in rare_langs else x)
        df["dominant_language"] = pd.Categorical(df["dominant_language"])

    # Log-transform lines_added
    df["log_lines_added"] = np.log(df["lines_added"] + 1)

    # Log-transform file heat if present
    if "mean_file_heat" in df.columns:
        df["log_file_heat"] = np.log(df["mean_file_heat"] + 1)

    # Drop rows with NaN in key columns
    key_cols = ["log_CR", "log_RF", "author_type", "log_lines_added"]
    df = df.dropna(subset=key_cols)

    print(f"Regression-ready: {len(df)} rows")
    print(f"  Author types: {dict(df['author_type'].value_counts())}")
    if "task_type" in df.columns:
        print(f"  Task types:   {dict(df['task_type'].value_counts())}")
    if "dominant_language" in df.columns:
        print(f"  Languages:    {dict(df['dominant_language'].value_counts())}")

    return df


def fit_model(formula, df, model_name, cluster_col="repo"):
    """Fit OLS model with clustered standard errors."""
    print(f"\n{'─'*60}")
    print(f"  {model_name}")
    print(f"  Formula: {formula}")
    print(f"{'─'*60}")

    try:
        # Reset index so groups align with model's internal data
        df_clean = df.dropna(subset=[cluster_col]).reset_index(drop=True)
        model = smf.ols(formula, data=df_clean).fit(
            cov_type="cluster",
            cov_kwds={"groups": df_clean[cluster_col]}
        )
        print(model.summary().tables[1])
        return model
    except Exception as e:
        print(f"  ✗ Model fitting failed: {e}")
        return None


def build_results_table(models, model_names):
    """Build a formatted comparison table across models."""
    if not any(models):
        print("No models to compare.")
        return ""

    # Collect all predictors
    all_params = set()
    for m in models:
        if m:
            all_params.update(m.params.index)
    all_params = sorted(all_params)

    # Header
    col_width = 18
    header = f"{'Predictor':<30}"
    for name in model_names:
        header += f" | {name:>{col_width}}"
    sep = "─" * len(header)

    lines = [sep, header, sep]

    for param in all_params:
        row = f"{param:<30}"
        for m in models:
            if m and param in m.params:
                coef = m.params[param]
                pval = m.pvalues[param]
                sig = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else ""
                row += f" | {coef:>14.4f}{sig:>3}"
            else:
                row += f" | {'─':>{col_width}}"
        lines.append(row)

    lines.append(sep)

    # Model stats
    row_n  = f"{'N':<30}"
    row_r2 = f"{'R²':<30}"
    row_r2a = f"{'Adj. R²':<30}"
    for m in models:
        if m:
            row_n  += f" | {m.nobs:>{col_width}.0f}"
            row_r2 += f" | {m.rsquared:>{col_width}.4f}"
            row_r2a += f" | {m.rsquared_adj:>{col_width}.4f}"
        else:
            row_n  += f" | {'─':>{col_width}}"
            row_r2 += f" | {'─':>{col_width}}"
            row_r2a += f" | {'─':>{col_width}}"

    lines.extend([row_n, row_r2, row_r2a, sep])

    table = "\n".join(lines)
    print(f"\n{table}")
    return table


def save_results(table_text, models, model_names):
    """Save regression results to a markdown report."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report_path = os.path.join(OUTPUT_DIR, "regression_report.md")

    with open(report_path, "w") as f:
        f.write("# RQ2b: Regression Analysis Results\n\n")
        f.write("## Research Question\n")
        f.write("Does AI code churn less because it's genuinely more stable, ")
        f.write("or because it lands in less active (colder) parts of the codebase?\n\n")
        f.write("## Models\n")
        f.write("| Model | Formula | Purpose |\n")
        f.write("|-------|---------|----------|\n")
        f.write("| Model 1 | `log_CR ~ author_type + log_lines_added + task_type + language` | Baseline |\n")
        f.write("| Model 2 | `log_CR ~ ... + log_file_heat` | Does file heat explain the AI effect? |\n")
        f.write("| Model 3 | `log_RF ~ ... + log_file_heat` | Confirm with churn frequency |\n\n")
        f.write("## Comparison Table\n\n")
        f.write("```\n")
        f.write(table_text)
        f.write("\n```\n\n")
        f.write("*Significance: \\*p<0.05, \\*\\*p<0.01, \\*\\*\\*p<0.001*\n\n")

        for m, name in zip(models, model_names):
            if m:
                f.write(f"## {name} — Full Summary\n\n```\n")
                f.write(str(m.summary()))
                f.write("\n```\n\n")

    print(f"\n✅ Report saved to {report_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    df, has_heat = load_and_merge()
    df = prepare_regression_df(df)

    # Build a single clean dataset for all models — drop rows with NaN in
    # any column that appears in any formula, so all models use the same N.
    required_cols = ["log_CR", "log_RF", "author_type", "log_lines_added", "repo"]
    if "task_type" in df.columns:
        required_cols.append("task_type")
    if "dominant_language" in df.columns:
        required_cols.append("dominant_language")
    if has_heat and "log_file_heat" in df.columns:
        required_cols.append("log_file_heat")

    df_clean = df.dropna(subset=required_cols).reset_index(drop=True)
    print(f"Clean subset for all models: {len(df_clean)} rows")

    models = []
    names  = []

    # ── Build formula ─────────────────────────────────────────────────────
    formula_base = "log_CR ~ C(author_type) + log_lines_added"
    if "task_type" in df_clean.columns and df_clean["task_type"].nunique() > 1:
        formula_base += " + C(task_type)"
    if "dominant_language" in df_clean.columns and df_clean["dominant_language"].nunique() > 1:
        formula_base += " + C(dominant_language)"

    # ── Model 1: Baseline (without file heat) ─────────────────────────────
    m1 = fit_model(formula_base, df_clean, "Model 1: CR Baseline")
    models.append(m1)
    names.append("CR Baseline")

    # ── Model 2: With file heat ───────────────────────────────────────────
    if has_heat and "log_file_heat" in df_clean.columns:
        formula2 = formula_base + " + log_file_heat"
        m2 = fit_model(formula2, df_clean, "Model 2: CR + File Heat")
        models.append(m2)
        names.append("CR + Heat")
    else:
        print("\n⚠ Skipping Model 2 (no heat data)")
        models.append(None)
        names.append("CR + Heat")

    # ── Model 3: Churn frequency (RF) with heat ──────────────────────────
    if has_heat and "log_file_heat" in df_clean.columns:
        formula3 = formula2.replace("log_CR", "log_RF")
        m3 = fit_model(formula3, df_clean, "Model 3: RF + File Heat")
        models.append(m3)
        names.append("RF + Heat")
    else:
        formula3_base = formula_base.replace("log_CR", "log_RF")
        m3 = fit_model(formula3_base, df_clean, "Model 3: RF Baseline")
        models.append(m3)
        names.append("RF Baseline")

    # ── Results Table ─────────────────────────────────────────────────────
    table = build_results_table(models, names)
    save_results(table, models, names)


if __name__ == "__main__":
    main()
