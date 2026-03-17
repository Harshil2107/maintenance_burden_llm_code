
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

CSV_FILE = "/Users/vikhas/Desktop/pr_churn_analysis/pr_level_metrics_500st.csv"
OUTPUT_DIR = "/Users/vikhas/Desktop/pr_churn_analysis/plots_500st"

def create_plots():
    if not os.path.exists(CSV_FILE):
        print(f"CSV file not found: {CSV_FILE}")
        return

    df = pd.read_csv(CSV_FILE)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Set aesthetics
    sns.set_theme(style="whitegrid")
    plt.rcParams.update({'font.size': 12})

    # 1. Churn Ratio Distribution (Boxplot)
    plt.figure(figsize=(10, 6))
    sns.boxplot(x="type", y="ratio", data=df, palette="muted")
    plt.title("Distribution of Churn Ratios: AI vs Human Code")
    plt.ylabel("Churn Ratio (Lines Rewritten / Lines Added)")
    plt.xlabel("Code Author Type")
    plt.savefig(os.path.join(OUTPUT_DIR, "churn_ratio_distribution_boxplot.png"))
    plt.close()

    # 2. Events vs Added Lines (Scatter plot)
    plt.figure(figsize=(10, 6))
    sns.scatterplot(x="added", y="events", hue="type", data=df, alpha=0.6)
    plt.title("Change Events vs. Lines Added")
    plt.xlabel("Total Lines Added per PR")
    plt.ylabel("Total Change Events (90 Days)")
    plt.savefig(os.path.join(OUTPUT_DIR, "events_vs_added_scatter.png"))
    plt.close()

    # 3. Events Per Line Distribution (KDE)
    # Calculate events per line for each PR
    df['events_per_line'] = df['events'] / df['added']
    plt.figure(figsize=(10, 6))
    sns.kdeplot(data=df, x="events_per_line", hue="type", fill=True, common_norm=False, palette="muted", alpha=.5, linewidth=0)
    plt.title("Frequency of Changes: Events Per Line Distribution")
    plt.xlabel("Events Per Line")
    plt.ylabel("Density")
    plt.savefig(os.path.join(OUTPUT_DIR, "events_per_line_kde.png"))
    plt.close()

    # 4. Total Churned Lines vs Added Lines
    plt.figure(figsize=(10, 6))
    sns.regplot(x="added", y="churned", data=df[df['type'] == 'AI'], label="AI Code", scatter_kws={'alpha':0.3})
    sns.regplot(x="added", y="churned", data=df[df['type'] == 'Human'], label="Human Code", scatter_kws={'alpha':0.3})
    plt.title("Churned Lines vs. Added Lines (Correlation)")
    plt.xlabel("Lines Added")
    plt.ylabel("Lines Churned")
    plt.legend()
    plt.savefig(os.path.join(OUTPUT_DIR, "churned_vs_added_correlation.png"))
    plt.close()

    print(f"Plots generated in {OUTPUT_DIR}")

if __name__ == "__main__":
    create_plots()
