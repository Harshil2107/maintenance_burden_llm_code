"""
Complete plotting analysis for PR-level churn metrics (full dataset).
Generates all plots + statistical summary for RQ3 analysis.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
from scipy import stats

# ─── Configuration ────────────────────────────────────────────────────
CSV_FILE = "/Users/vikhas/Documents/projects/winter/SE/maintainance_burden_llm_code/RQ3/pr_level_metrics_500st_full.csv"
OUTPUT_DIR = "/Users/vikhas/Documents/projects/winter/SE/maintainance_burden_llm_code/RQ3/plots_500st_full"

def load_data():
    df = pd.read_csv(CSV_FILE)
    # Derive useful columns
    df['events_per_line'] = df['events'] / df['added'].replace(0, np.nan)
    df['events_per_line'] = df['events_per_line'].fillna(0)
    return df

def print_summary(df):
    """Print descriptive statistics."""
    print("=" * 60)
    print("DATASET SUMMARY")
    print("=" * 60)
    print(f"Total PRs: {len(df)}")
    print(f"  AI PRs:    {len(df[df['type'] == 'AI'])}")
    print(f"  Human PRs: {len(df[df['type'] == 'Human'])}")
    print(f"Unique repos: {df['repo'].nunique()}")
    print()

    for t in ['AI', 'Human']:
        sub = df[df['type'] == t]
        print(f"\n--- {t} Code ---")
        print(f"  Churn Ratio    mean={sub['ratio'].mean():.4f}  median={sub['ratio'].median():.4f}  std={sub['ratio'].std():.4f}")
        print(f"  Lines Added    mean={sub['added'].mean():.1f}  median={sub['added'].median():.1f}")
        print(f"  Lines Churned  mean={sub['churned'].mean():.1f}  median={sub['churned'].median():.1f}")
        print(f"  Events         mean={sub['events'].mean():.1f}  median={sub['events'].median():.1f}")
        print(f"  Zero-churn PRs: {len(sub[sub['churned'] == 0])} ({len(sub[sub['churned'] == 0])/len(sub)*100:.1f}%)")

    # Mann-Whitney U test on churn ratio
    ai_ratios = df[df['type'] == 'AI']['ratio']
    hu_ratios = df[df['type'] == 'Human']['ratio']
    stat, pval = stats.mannwhitneyu(ai_ratios, hu_ratios, alternative='two-sided')
    print(f"\nMann-Whitney U test (churn ratio): U={stat:.1f}, p={pval:.6f}")

    # Effect size (Cliff's delta)
    n1, n2 = len(ai_ratios), len(hu_ratios)
    diff_count = sum(1 for a in ai_ratios for h in hu_ratios if a > h) - \
                 sum(1 for a in ai_ratios for h in hu_ratios if a < h)
    cliffs_d = diff_count / (n1 * n2)
    print(f"Cliff's delta: {cliffs_d:.4f}")
    print("=" * 60)


def plot_1_boxplot(df, output_dir):
    """1. Churn Ratio Distribution – Boxplot."""
    plt.figure(figsize=(10, 6))
    sns.boxplot(x="type", y="ratio", data=df, palette="muted", order=["AI", "Human"])
    plt.title("Distribution of Churn Ratios: AI vs Human Code")
    plt.ylabel("Churn Ratio (Lines Churned / Lines Added)")
    plt.xlabel("Code Author Type")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "churn_ratio_distribution_boxplot.png"), dpi=150)
    plt.close()
    print("  ✓ churn_ratio_distribution_boxplot.png")


def plot_2_scatter_events(df, output_dir):
    """2. Events vs Added Lines – Scatter."""
    plt.figure(figsize=(10, 6))
    sns.scatterplot(x="added", y="events", hue="type", data=df, alpha=0.6,
                    hue_order=["AI", "Human"])
    plt.title("Change Events vs. Lines Added")
    plt.xlabel("Total Lines Added per PR")
    plt.ylabel("Total Change Events (90 Days)")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "events_vs_added_scatter.png"), dpi=150)
    plt.close()
    print("  ✓ events_vs_added_scatter.png")


def plot_3_kde_events_per_line(df, output_dir):
    """3. Events Per Line Distribution – KDE."""
    plt.figure(figsize=(10, 6))
    sns.kdeplot(data=df, x="events_per_line", hue="type", fill=True,
                common_norm=False, palette="muted", alpha=0.5, linewidth=0,
                hue_order=["AI", "Human"])
    plt.title("Frequency of Changes: Events Per Line Distribution")
    plt.xlabel("Events Per Line")
    plt.ylabel("Density")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "events_per_line_kde.png"), dpi=150)
    plt.close()
    print("  ✓ events_per_line_kde.png")


def plot_4_correlation(df, output_dir):
    """4. Churned Lines vs Added Lines – Regression."""
    plt.figure(figsize=(10, 6))
    sns.regplot(x="added", y="churned", data=df[df['type'] == 'AI'],
                label="AI Code", scatter_kws={'alpha': 0.3})
    sns.regplot(x="added", y="churned", data=df[df['type'] == 'Human'],
                label="Human Code", scatter_kws={'alpha': 0.3})
    plt.title("Churned Lines vs. Added Lines (Correlation)")
    plt.xlabel("Lines Added")
    plt.ylabel("Lines Churned")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "churned_vs_added_correlation.png"), dpi=150)
    plt.close()
    print("  ✓ churned_vs_added_correlation.png")


def plot_5_violin(df, output_dir):
    """5. Churn Ratio – Violin (conditional on churn>0)."""
    cond = df[df['churned'] > 0].copy()
    plt.figure(figsize=(10, 6))
    sns.violinplot(data=cond, x='type', y='ratio', palette='muted',
                   inner='quartile', order=["AI", "Human"])
    plt.title('Distribution of Churn Ratio (Only for Churned PRs)')
    plt.ylabel('Churn Ratio (Lines Churned / Lines Added)')
    plt.xlabel("Code Author Type")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "churn_ratio_violin_conditional.png"), dpi=150)
    plt.close()
    print("  ✓ churn_ratio_violin_conditional.png")


def plot_6_event_intensity_boxplot(df, output_dir):
    """6. Event Intensity boxplot (conditional on churn>0)."""
    cond = df[df['churned'] > 0].copy()
    cond['event_intensity'] = cond['events'] / cond['added'].replace(0, np.nan)
    cond['event_intensity'] = cond['event_intensity'].fillna(0)
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=cond, x='type', y='event_intensity', palette='pastel',
                order=["AI", "Human"])
    plt.title('Event Intensity (Updates per Line) for Churned PRs')
    plt.ylabel('Events / Lines Added')
    plt.xlabel("Code Author Type")
    plt.ylim(0, cond['event_intensity'].quantile(0.95) * 1.2)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "event_intensity_boxplot_conditional.png"), dpi=150)
    plt.close()
    print("  ✓ event_intensity_boxplot_conditional.png")


def plot_7_zero_churn_bar(df, output_dir):
    """7. Proportion of zero-churn PRs – grouped bar chart."""
    counts = df.groupby('type')['churned'].apply(
        lambda x: pd.Series({
            'Zero Churn': (x == 0).sum(),
            'Has Churn': (x > 0).sum()
        })
    ).unstack()

    pcts = counts.div(counts.sum(axis=1), axis=0) * 100

    fig, ax = plt.subplots(figsize=(8, 6))
    pcts.plot(kind='bar', stacked=True, ax=ax, color=['#66c2a5', '#fc8d62'])
    plt.title("Proportion of Zero-Churn vs Churned PRs")
    plt.ylabel("Percentage (%)")
    plt.xlabel("Code Author Type")
    plt.xticks(rotation=0)
    for i, (idx, row) in enumerate(pcts.iterrows()):
        cumsum = 0
        for col in pcts.columns:
            val = row[col]
            ax.text(i, cumsum + val / 2, f"{val:.1f}%", ha='center', va='center', fontsize=11)
            cumsum += val
    plt.legend(title="Churn Status")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "zero_churn_proportion.png"), dpi=150)
    plt.close()
    print("  ✓ zero_churn_proportion.png")


def plot_8_per_repo_median(df, output_dir):
    """8. Per-repo median churn ratio – Heatmap / grouped bar."""
    repo_medians = df.groupby(['repo', 'type'])['ratio'].median().unstack(fill_value=0)
    repo_medians = repo_medians.sort_values('AI', ascending=False)

    fig, ax = plt.subplots(figsize=(12, max(6, len(repo_medians) * 0.4)))
    repo_medians.plot(kind='barh', ax=ax, color=['#1f77b4', '#ff7f0e'])
    plt.title("Median Churn Ratio per Repository")
    plt.xlabel("Median Churn Ratio")
    plt.ylabel("")
    plt.legend(title="Type")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "per_repo_median_churn.png"), dpi=150)
    plt.close()
    print("  ✓ per_repo_median_churn.png")


def plot_9_log_scatter(df, output_dir):
    """9. Log-scale scatter of added vs churned."""
    plot_df = df[df['churned'] > 0].copy()
    plt.figure(figsize=(10, 6))
    sns.scatterplot(x="added", y="churned", hue="type", data=plot_df, alpha=0.5,
                    hue_order=["AI", "Human"])
    plt.xscale('log')
    plt.yscale('log')
    plt.title("Lines Added vs Lines Churned (Log Scale)")
    plt.xlabel("Lines Added (log)")
    plt.ylabel("Lines Churned (log)")
    # Identity line
    lims = [max(plt.xlim()[0], plt.ylim()[0]), min(plt.xlim()[1], plt.ylim()[1])]
    plt.plot(lims, lims, 'k--', alpha=0.3, label='y=x')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "log_added_vs_churned.png"), dpi=150)
    plt.close()
    print("  ✓ log_added_vs_churned.png")


def plot_10_histogram_ratio(df, output_dir):
    """10. Overlapping histogram of churn ratio."""
    plt.figure(figsize=(10, 6))
    bins = np.linspace(0, 1, 21)
    plt.hist(df[df['type'] == 'AI']['ratio'], bins=bins, alpha=0.5, label='AI', color='#1f77b4', edgecolor='black')
    plt.hist(df[df['type'] == 'Human']['ratio'], bins=bins, alpha=0.5, label='Human', color='#ff7f0e', edgecolor='black')
    plt.title("Churn Ratio Histogram: AI vs Human")
    plt.xlabel("Churn Ratio")
    plt.ylabel("Count")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "churn_ratio_histogram.png"), dpi=150)
    plt.close()
    print("  ✓ churn_ratio_histogram.png")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    sns.set_theme(style="whitegrid")
    plt.rcParams.update({'font.size': 12})

    print(f"Loading data from {CSV_FILE}...")
    df = load_data()

    print_summary(df)

    print("\nGenerating plots...")
    plot_1_boxplot(df, OUTPUT_DIR)
    plot_2_scatter_events(df, OUTPUT_DIR)
    plot_3_kde_events_per_line(df, OUTPUT_DIR)
    plot_4_correlation(df, OUTPUT_DIR)
    plot_5_violin(df, OUTPUT_DIR)
    plot_6_event_intensity_boxplot(df, OUTPUT_DIR)
    plot_7_zero_churn_bar(df, OUTPUT_DIR)
    plot_8_per_repo_median(df, OUTPUT_DIR)
    plot_9_log_scatter(df, OUTPUT_DIR)
    plot_10_histogram_ratio(df, OUTPUT_DIR)

    print(f"\n✅ All 10 plots saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
