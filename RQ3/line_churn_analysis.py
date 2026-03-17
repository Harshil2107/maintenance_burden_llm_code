import json
import os
import subprocess
import re
from collections import Counter
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil

# Configuration
INPUT_FILE = "/Users/vikhas/Documents/projects/winter/SE/maintainance_burden_llm_code/datasets/matched_pr_pairs_in_30_days_500st.json"
OUTPUT_REPORT = "/Users/vikhas/Documents/projects/winter/SE/maintainance_burden_llm_code/RQ3/line_churn_report_500st_full.md"
REPO_DIR = "/Users/vikhas/.gemini/antigravity/scratch/repos"
TOP_N_REPOS = 1000000  # Complete dataset
CHURN_WINDOW_DAYS = 90
CSV_EXPORT = "/Users/vikhas/Documents/projects/winter/SE/maintainance_burden_llm_code/RQ3/pr_level_metrics_500st_full.csv"

def run_cmd(cmd, cwd=None):
    try:
        result = subprocess.run(
            cmd, cwd=cwd, shell=True, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors='replace'
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None

def get_repo_name(url):
    parts = url.split('/')
    return f"{parts[-2]}/{parts[-1]}"

def clone_repo(repo_url, target_dir):
    clean_url = repo_url.replace("api.github.com/repos", "github.com")
    if not clean_url.endswith(".git"):
        clean_url += ".git"
    
    if os.path.exists(target_dir):
        # print(f"Repo {target_dir} exists, updating...")
        run_cmd("git fetch --all", cwd=target_dir)
    else:
        print(f"Cloning {clean_url} to {target_dir}...")
        run_cmd(f"git clone {clean_url} {target_dir}")

def find_pr_commit(repo_dir, pr_number):
    cmd = f'git log --grep="Merge pull request #{pr_number}" --grep="Merge PR #{pr_number}" --grep="(#{pr_number})" -n 1 --format="%H"'
    commit = run_cmd(cmd, cwd=repo_dir)
    return commit

def get_added_line_ranges(repo_dir, base_commit, merge_commit):
    """
    Returns a dict: { filepath: [(start_line, end_line), ...] }
    for all lines added in merge_commit relative to base_commit.
    """
    # git diff -U0 shows zero context, making parsing easier.
    # We look for @@ -old,cnt +new,cnt @@
    cmd = f"git diff -U0 {base_commit} {merge_commit}"
    diff_out = run_cmd(cmd, cwd=repo_dir)
    if not diff_out:
        return {}

    changes = {}
    current_file = None
    
    for line in diff_out.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:].strip() # Remove "+++ b/"
            changes[current_file] = []
        elif line.startswith("@@ ") and current_file:
            # Parse hunk header: @@ -10,0 +15,5 @@
            # We care about the +part (new file lines)
            match = re.search(r'\+(\d+)(?:,(\d+))?', line)
            if match:
                start = int(match.group(1))
                count = int(match.group(2)) if match.group(2) else 1
                
                # If count is 0, it is a pure deletion, ignore
                if count > 0:
                    # Range is inclusive
                    end = start + count - 1
                    changes[current_file].append((start, end))
                    
    return changes

def analyze_line_churn(repo_dir, pr_number, merge_date_str):
    commit = find_pr_commit(repo_dir, pr_number)
    if not commit: return None

    # Identify Base Commit
    parents = run_cmd(f"git show -s --format='%P' {commit}", cwd=repo_dir).split()
    if len(parents) >= 2:
        base_commit = parents[0]
    else:
        base_commit = f"{commit}^"

    # 1. Get Added Lines
    # { "src/main.py": [(10, 15), (50, 52)] }
    file_ranges = get_added_line_ranges(repo_dir, base_commit, commit)
    if not file_ranges:
        return None

    # 2. Determine Time Window
    try:
        dt = datetime.fromisoformat(merge_date_str.replace('Z', '+00:00'))
    except:
        return None
    
    # We need the commit hash that is closest to 90 days later
    until_date = dt + timedelta(days=CHURN_WINDOW_DAYS)
    
    # Check if repo has history up to that point
    # git rev-list -n 1 --before="2025-09-24" master
    # Ideally, we look at HEAD (or tip of default branch). 
    # If the repo is younger than 90 days from merge, we just take HEAD.
    # But git blame works with a range start..end.
    # We want start=MergeCommit, end=CommitAt90Days.
    
    # Find the commit ID for the 'until' date
    rev_cmd = f'git rev-list -n 1 --before="{until_date.isoformat()}" origin/HEAD'
    end_commit = run_cmd(rev_cmd, cwd=repo_dir)
    
    if not end_commit:
        # Fallback to current HEAD if date is in future or something
        end_commit = "HEAD"

    # 3. Blame Reverse + Frequency Analysis
    total_added = 0
    total_churned = 0
    total_change_events = 0 # Sum of how many times each added line block was changed

    for filepath, ranges in file_ranges.items():
        if not ranges: continue
        
        # Check if file exists in end_commit? If deleted, it's 100% churn.
        # git cat-file -e end_commit:filepath
        if run_cmd(f"git cat-file -e {end_commit}:{filepath}", cwd=repo_dir) is None:
            # File deleted! All lines churned.
            for (s, e) in ranges:
                count = e - s + 1
                total_added += count
                total_churned += count
                # If file is deleted, that's at least 1 change event (the deletion)
                # potentially more if it was modified before deletion. 
                # For simplicity/speed, let's just count the deletion as 1 event per block?
                # Or try to run log on it? 
                # git log -L might fail if file is gone in HEAD/end_commit? 
                # It usually tracks history. Let's try to run it anyway, but up to the deletion?
                # For now, safe fallback: 1 event per line? No, let's just say 1 event per block.
                total_change_events += 1 
            continue

        for (start, end) in ranges:
            count = end - start + 1
            total_added += count
            
            # --- Churn Frequency (git log -L) ---
            # We want to know how many commits touched this block between merge and end date.
            # git log -L start,end:file merge..end --format="%H"
            # Note: start,end are in terms of the merge commit (start point). 
            # Git log -L follows lines.
            
            log_cmd = f"git log -L {start},{end}:{filepath} {commit}..{end_commit} --format='%H'"
            log_out = run_cmd(log_cmd, cwd=repo_dir)
            
            if log_out:
                # Count distinct commits
                # Output contains diffs, so filter for hashes
                unique_commits = set()
                for line in log_out.splitlines():
                    # Hashes are 40 chars
                    if re.match(r'^[0-9a-f]{40}$', line.strip()):
                         unique_commits.add(line.strip())
                
                # The range is exclusive of start usually for .. range, but -L follows history.
                # If the merge commit itself shows up, exclude it.
                if commit in unique_commits:
                    unique_commits.remove(commit)
                
                total_change_events += len(unique_commits)

            # --- True Churn (git blame --reverse) ---
            # git blame --reverse START..END -L s,e -- file
            # Output lines start with CommitHash.
            # If CommitHash == START (the merge commit), it is unchanged.
            # Convert commit hash to short just in case
            
            full_end = run_cmd(f"git rev-parse {end_commit}", cwd=repo_dir)
            blame_cmd = f"git blame --reverse {commit}..{end_commit} -L {start},{end} --porcelain -- '{filepath}'"
            blame_out = run_cmd(blame_cmd, cwd=repo_dir)
            
            if not blame_out:
                continue
                
            # Parse porcelain output
            lines_churned_in_hunk = 0
            for line in blame_out.splitlines():
                if re.match(r'^[0-9a-f]{40} \d+ \d+', line):
                    line_hash = line.split()[0]
                    # If it points to the end commit, it survived -> Stable.
                    if line_hash != full_end:
                        lines_churned_in_hunk += 1
            
            total_churned += lines_churned_in_hunk

    if total_added == 0:
        return None

    return {
        "initial_lines": total_added,
        "churn_lines": total_churned,
        "ratio": total_churned / total_added,
        "change_events": total_change_events
    }

def process_repo(repo_url, repo_pairs, repo_dir_base):
    # Helper to process one repo
    repo_name = get_repo_name(repo_url)
    local_dir = os.path.join(repo_dir_base, repo_name.replace('/', '_'))
    
    # Clone (thread-safeish if dirs are different)
    clone_repo(repo_url, local_dir)
    
    repo_results = {
        "ai": {"churn": 0, "contrib": 0, "pairs": 0, "ratios": [], "events": 0},
        "human": {"churn": 0, "contrib": 0, "pairs": 0, "ratios": [], "events": 0},
        "raw_metrics": []
    }
    
    print(f"Processing {repo_name} ({len(repo_pairs)} pairs)...")
    
    for pair in repo_pairs:
        # AI
        try:
            ai_res = analyze_line_churn(local_dir, pair['ai_number'], pair['ai_merged_at'])
            if ai_res:
                repo_results["ai"]["churn"] += ai_res["churn_lines"]
                repo_results["ai"]["contrib"] += ai_res["initial_lines"]
                repo_results["ai"]["pairs"] += 1
                repo_results["ai"]["ratios"].append(ai_res["ratio"])
                repo_results["ai"]["events"] += ai_res["change_events"]
                repo_results["raw_metrics"].append({
                    "repo": repo_name,
                    "pr": pair['ai_number'],
                    "type": "AI",
                    "added": ai_res["initial_lines"],
                    "churned": ai_res["churn_lines"],
                    "events": ai_res["change_events"],
                    "ratio": ai_res["ratio"]
                })
        except Exception:
            pass
            
        # Human
        try:
            hu_res = analyze_line_churn(local_dir, pair['human_number'], pair['human_merged_at'])
            if hu_res:
                repo_results["human"]["churn"] += hu_res["churn_lines"]
                repo_results["human"]["contrib"] += hu_res["initial_lines"]
                repo_results["human"]["pairs"] += 1
                repo_results["human"]["ratios"].append(hu_res["ratio"])
                repo_results["human"]["events"] += hu_res["change_events"]
                repo_results["raw_metrics"].append({
                    "repo": repo_name,
                    "pr": pair['human_number'],
                    "type": "Human",
                    "added": hu_res["initial_lines"],
                    "churned": hu_res["churn_lines"],
                    "events": hu_res["change_events"],
                    "ratio": hu_res["ratio"]
                })
        except Exception:
            pass
            
    # Cleanup: Delete repo to save space
    if os.path.exists(local_dir):
        # specific safeguards to ensure we don't delete wrong things
        if "scratch/repos" in local_dir:
            shutil.rmtree(local_dir)
                
    return repo_results

def main():
    print(f"Starting Parallel Line-Level Churn Analysis (Top {TOP_N_REPOS} Repos)...")
    
    with open(INPUT_FILE, 'r') as f:
        data = json.load(f)

    # 1. Identify Top Repos
    repo_counts = Counter(item['repo_url'] for item in data)
    top_repos = [url for url, count in repo_counts.most_common(TOP_N_REPOS)]
    
    os.makedirs(REPO_DIR, exist_ok=True)
    
    final_results = {
        "ai": {"churn": 0, "contrib": 0, "pairs": 0, "ratios": [], "events": 0},
        "human": {"churn": 0, "contrib": 0, "pairs": 0, "ratios": [], "events": 0}
    }
    all_raw_metrics = []
    
    # Parallel Execution
    MAX_WORKERS = 8
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(process_repo, url, [p for p in data if p['repo_url'] == url], REPO_DIR): url for url in top_repos}
        
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                repo_res = future.result()
                # Merge
                for agent in ["ai", "human"]:
                    final_results[agent]["churn"] += repo_res[agent]["churn"]
                    final_results[agent]["contrib"] += repo_res[agent]["contrib"]
                    final_results[agent]["pairs"] += repo_res[agent]["pairs"]
                    final_results[agent]["ratios"].extend(repo_res[agent]["ratios"])
                    final_results[agent]["events"] += repo_res[agent]["events"]
                all_raw_metrics.extend(repo_res["raw_metrics"])
            except Exception as e:
                print(f"Repo {url} generated an exception: {e}")

    # Save to CSV
    import csv
    if all_raw_metrics:
        with open(CSV_EXPORT, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=all_raw_metrics[0].keys())
            writer.writeheader()
            writer.writerows(all_raw_metrics)
        print(f"Saved raw metrics to {CSV_EXPORT}")

    # Report
    results = final_results
    ai_avg = sum(results["ai"]["ratios"]) / len(results["ai"]["ratios"]) if results["ai"]["ratios"] else 0
    hu_avg = sum(results["human"]["ratios"]) / len(results["human"]["ratios"]) if results["human"]["ratios"] else 0
    
    ai_events_per_line = results['ai']['events'] / results['ai']['contrib'] if results['ai']['contrib'] else 0
    hu_events_per_line = results['human']['events'] / results['human']['contrib'] if results['human']['contrib'] else 0
    
    report = f"""# Line-Level True Churn Report (Full Dataset)

**Metric 1**: `(Specific Lines Modified in 90 days) / (Lines Added)`
**Metric 2**: `(Total Change Events) / (Lines Added)` (Frequency)
**Scope**: All Repositories (Top {TOP_N_REPOS} attempted)

## Results

| Metric | AI Code | Human Code |
| :--- | :--- | :--- |
| **Pairs Analyzed** | {results['ai']['pairs']} | {results['human']['pairs']} |
| **Lines Contributed** | {results['ai']['contrib']} | {results['human']['contrib']} |
| **Specific Lines Rewritten** | {results['ai']['churn']} | {results['human']['churn']} |
| **Avg Churn Ratio** | **{ai_avg:.2%}** | **{hu_avg:.2%}** |
| **Total Change Events** | {results['ai']['events']} | {results['human']['events']} |
| **Events Per Line** | **{ai_events_per_line:.4f}** | **{hu_events_per_line:.4f}** |

*Note: A ratio of 100% means every single line added was rewritten or deleted within 90 days.*
*Events Per Line indicates how frequently the added code blocks were modified.*
"""
    print(report)
    with open(OUTPUT_REPORT, 'w') as f:
        f.write(report)
    print(f"Saved to {OUTPUT_REPORT}")

if __name__ == "__main__":
    main()
