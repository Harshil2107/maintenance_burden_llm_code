import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os

# Configuration
FILES = [
    "/Users/vikhas/Desktop/pr_churn_analysis/pr_level_metrics.csv",
    "/Users/vikhas/Desktop/pr_churn_analysis/pr_level_metrics_250st.csv",
    "/Users/vikhas/Desktop/pr_churn_analysis/pr_level_metrics_500st.csv"
]
OUTPUT_REPORT = "/Users/vikhas/.gemini/antigravity/brain/7cc55c90-5e75-48a8-bc12-0ce44961f11c/rq3_churn_intensity_report.md"
PLOT_DIR = "/Users/vikhas/.gemini/antigravity/brain/7cc55c90-5e75-48a8-bc12-0ce44961f11c"

def analyze_rq3():
    dfs = []
    for f in FILES:
        if os.path.exists(f):
            print(f"Loading {f}...")
            dfs.append(pd.read_csv(f))
        else:
            print(f"Warning: {f} not found.")

    if not dfs:
        print("No data found!")
        return

    full_df = pd.concat(dfs, ignore_index=True)
    
    # FILTER: Conditional Churn (Exclude 0 churn)
    conditional_df = full_df[full_df['churned_lines'] > 0].copy()
    
    print(f"Total Rows: {len(full_df)}")
    print(f"Rows with Churn > 0: {len(conditional_df)}")
    
    # Calculate Events Intensity (Events / Added Lines)
    # Avoid division by zero if added=0 (though unlikely in this dataset)
    conditional_df['event_intensity'] = conditional_df.apply(
        lambda row: row['events'] / row['added'] if row['added'] > 0 else 0, axis=1
    )
    
    # Metrics Grouped by Type
    metrics = conditional_df.groupby('type')[['ratio', 'event_intensity']].describe()
    print("\nConditional Metrics (Churn > 0):")
    print(metrics)
    
    # Generate Report
    with open(OUTPUT_REPORT, 'w') as f:
        f.write("# RQ3: Conditional Churn Intensity Analysis\n\n")
        f.write("## Hypothesis\n")
        f.write("Since AI code might be 'perfect or broken', we test if AI code that *does* break requires more extensive rewriting than human code.\n\n")
        
        f.write("## Data Filter\n")
        f.write(f"- **Total PR Pairs Analyzed**: {len(full_df)}\n")
        f.write(f"- **PRs with >0 Churn**: {len(conditional_df)} ({len(conditional_df)/len(full_df)*100:.1f}%)\n\n")
        
        f.write("## Results (Conditioned on Churn > 0)\n\n")
        
        # Table
        f.write("| Metric | AI (Mean) | Human (Mean) | AI (Median) | Human (Median) |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
        
        ai_stats = conditional_df[conditional_df['type'] == 'AI']
        hu_stats = conditional_df[conditional_df['type'] == 'Human']
        
        f.write(f"| **Churn Ratio** | {ai_stats['ratio'].mean()*100:.2f}% | {hu_stats['ratio'].mean()*100:.2f}% | {ai_stats['ratio'].median()*100:.2f}% | {hu_stats['ratio'].median()*100:.2f}% |\n")
        f.write(f"| **Event Intensity** | {ai_stats['event_intensity'].mean():.4f} | {hu_stats['event_intensity'].mean():.4f} | {ai_stats['event_intensity'].median():.4f} | {hu_stats['event_intensity'].median():.4f} |\n\n")

        f.write("## Interpretation\n")
        if ai_stats['ratio'].mean() > hu_stats['ratio'].mean():
            f.write("- **Severity**: When AI code churns, it churns **more heavily** than human code.\n")
        else:
            f.write("- **Severity**: Even when churn occurs, AI code requires **less rewriting** on average than human code.\n")
            
        if ai_stats['event_intensity'].mean() > hu_stats['event_intensity'].mean():
            f.write("- **Frequency**: AI fixes require **more iterations** to get right.\n")
        else:
            f.write("- **Frequency**: AI fixes are applied with **fewer iterations**.\n")

    # Plotting
    plt.figure(figsize=(10, 6))
    sns.violinplot(data=conditional_df, x='type', y='ratio', palette='muted', inner='quartile')
    plt.title('Distribution of Churn Ratio (Only for Churned PRs)')
    plt.ylabel('Churn Ratio (Lines Modified / Lines Added)')
    plt.savefig(f"{PLOT_DIR}/rq3_conditional_churn_violin.png")
    
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=conditional_df, x='type', y='event_intensity', palette='pastel')
    plt.title('Event Intensity (Updates per Line) for Churned PRs')
    plt.ylim(0, 0.5) # Limit outliers for visibility
    plt.savefig(f"{PLOT_DIR}/rq3_event_intensity_boxplot.png")

    print(f"Report saved to {OUTPUT_REPORT}")

if __name__ == "__main__":
    analyze_rq3()
