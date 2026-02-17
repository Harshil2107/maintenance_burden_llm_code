import json
import os
import statistics
from collections import Counter

def load_data(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def analyze_dataset(data):
    stats = {
        "total_pairs": len(data),
        "ai_agents": Counter(),
        "pr_types": Counter(),
        "ai_body_lengths": [],
        "human_body_lengths": [],
        "ai_title_lengths": [],
        "human_title_lengths": [],
        "repos": Counter()
    }

    for pair in data:
        # Basic counts
        stats["ai_agents"][pair.get("agent", "Unknown")] += 1
        stats["pr_types"][pair.get("type", "Unknown")] += 1
        stats["repos"][pair.get("repo_url", "Unknown")] += 1

        # Content analysis
        ai_body = pair.get("ai_body") or ""
        human_body = pair.get("human_body") or ""
        
        stats["ai_body_lengths"].append(len(ai_body.split()))
        stats["human_body_lengths"].append(len(human_body.split()))

        ai_title = pair.get("ai_title") or ""
        human_title = pair.get("human_title") or ""

        stats["ai_title_lengths"].append(len(ai_title))
        stats["human_title_lengths"].append(len(human_title))

    return stats

def generate_report(stats, output_path):
    report = f"""# Matched PR Pairs Analysis Report

## 1. Overview
- **Total Pairs Analyzed**: {stats['total_pairs']}
- **Unique Repositories**: {len(stats['repos'])}

## 2. Distribution

### Top AI Agents
"""
    for agent, count in stats['ai_agents'].most_common(5):
        report += f"- {agent}: {count}\n"

    report += "\n### PR Types\n"
    for type_, count in stats['pr_types'].most_common(5):
        report += f"- {type_}: {count}\n"

    report += "\n## 3. Content Comparison\n"
    
    # Helper for stats
    def get_list_stats(lst):
        if not lst: return "N/A"
        return f"Avg: {statistics.mean(lst):.1f}, Median: {statistics.median(lst):.1f}, Max: {max(lst)}"

    report += "\n### Description Length (Word Count)\n"
    report += f"- **AI Generated**: {get_list_stats(stats['ai_body_lengths'])}\n"
    report += f"- **Human Authored**: {get_list_stats(stats['human_body_lengths'])}\n"

    report += "\n### Title Length (Characters)\n"
    report += f"- **AI Generated**: {get_list_stats(stats['ai_title_lengths'])}\n"
    report += f"- **Human Authored**: {get_list_stats(stats['human_title_lengths'])}\n"

    with open(output_path, 'w') as f:
        f.write(report)
    
    print(f"Report generated at {output_path}")

if __name__ == "__main__":
    input_file = "/Users/vikhas/Downloads/matched_pr_pairs.json"
    output_file = "/Users/vikhas/.gemini/antigravity/brain/33304aa7-551d-49f3-a20e-24b9c3af7c20/analysis_report.md"
    
    try:
        data = load_data(input_file)
        stats = analyze_dataset(data)
        generate_report(stats, output_file)
    except FileNotFoundError:
        print(f"Error: Could not find input file at {input_file}")
    except Exception as e:
        print(f"An error occurred: {e}")
