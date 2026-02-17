import json
import os
import subprocess
import shutil
from collections import Counter
from datetime import datetime, timedelta

# Configuration
INPUT_FILE = "/Users/vikhas/Downloads/matched_pr_pairs.json"
OUTPUT_REPORT = "/Users/vikhas/.gemini/antigravity/brain/33304aa7-551d-49f3-a20e-24b9c3af7c20/churn_report.md"
REPO_DIR = "/Users/vikhas/.gemini/antigravity/scratch/repos"
TOP_N_REPOS = 20
CHURN_WINDOW_DAYS = 90

def run_cmd(cmd, cwd=None):
    try:
        result = subprocess.run(
            cmd, cwd=cwd, shell=True, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        # print(f"Error running cmd: {cmd}\n{e.stderr}")
        return None

def get_repo_name(url):
    # https://api.github.com/repos/owner/name -> owner/name
    parts = url.split('/')
    return f"{parts[-2]}/{parts[-1]}"

def clone_repo(repo_url, target_dir):
    # Convert api url to clone url if needed, or assumet https://github.com/owner/repo.git
    # Input: https://api.github.com/repos/liam-hq/liam
    # Output: https://github.com/liam-hq/liam.git
    
    clean_url = repo_url.replace("api.github.com/repos", "github.com")
    if not clean_url.endswith(".git"):
        clean_url += ".git"
        
    if os.path.exists(target_dir):
        print(f"Repo {target_dir} exists, updating...")
        run_cmd("git fetch --all", cwd=target_dir)
    else:
        print(f"Cloning {clean_url} to {target_dir}...")
        run_cmd(f"git clone {clean_url} {target_dir}")

def find_pr_commit(repo_dir, pr_number):
    # Try finding merge commit
    # 1. Look for "Merge pull request #123"
    cmd = f'git log --grep="Merge pull request #{pr_number}" --grep="Merge PR #{pr_number}" --grep="(#{pr_number})" -n 1 --format="%H"'
    commit = run_cmd(cmd, cwd=repo_dir)
    if commit: return commit
    return None

def analyze_pr_churn(repo_dir, pr_number, merge_date_str):
    commit = find_pr_commit(repo_dir, pr_number)
    
    if not commit:
        # print(f"  [Warn] Could not find commit for PR #{pr_number}")
        return None

    # 1. Identify modified files and initial lines added
    # Use parent of merge commit to comparison? 
    # For merge commits, we usually compare against the first parent (target branch).
    # git diff --numstat HEAD^1 HEAD
    
    # Check if it is a merge commit (2 parents)
    parents = run_cmd(f"git show -s --format='%P' {commit}", cwd=repo_dir).split()
    if len(parents) >= 2:
        # It's a merge commit, diff against first parent (base branch)
        base_commit = parents[0]
    else:
        # Squash merge or fast-forward, diff against previous commit
        base_commit = f"{commit}^"

    # Get files modified in this PR
    # Filter for source code extensions to avoid docs/json noise if desired? 
    # For now, keep all.
    diff_cmd = f"git diff --numstat {base_commit} {commit}"
    diff_output = run_cmd(diff_cmd, cwd=repo_dir)
    
    if not diff_output:
        return None

    files = []
    initial_additions = 0
    
    for line in diff_output.splitlines():
        parts = line.split()
        if len(parts) == 3:
            added, deleted, filepath = parts
            if added == '-': continue # Binary file
            initial_additions += int(added)
            files.append(filepath)

    if initial_additions == 0:
        return None

    # 2. Calculate Churn (modifications to these files in next 90 days)
    # Parse merge date
    try:
        # ISO format from JSON: 2025-06-26T05:38:34Z
        dt = datetime.fromisoformat(merge_date_str.replace('Z', '+00:00'))
    except:
        return None
        
    since = dt.isoformat()
    until = (dt + timedelta(days=CHURN_WINDOW_DAYS)).isoformat()
    
    churn_lines = 0
    
    for filepath in files:
        # Find commits changing this file in the window, EXCLUDING the original PR commit
        # We look at commits AFTER the merge.
        # git log --since=.. --until=.. --format="" --numstat -- filepath
        log_cmd = f"git log --since='{since}' --until='{until}' --format='' --numstat -- '{filepath}'"
        log_output = run_cmd(log_cmd, cwd=repo_dir)
        
        if log_output:
            for line in log_output.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2: # added, deleted, (optional name if rename)
                    a, d = parts[0], parts[1]
                    if a == '-': continue
                    churn_lines += int(a) + int(d)

    return {
        "initial_lines": initial_additions,
        "churn_lines": churn_lines,
        "ratio": churn_lines / initial_additions
    }

def main():
    if not os.path.exists(INPUT_FILE):
        print("Input file not found.")
        return

    with open(INPUT_FILE, 'r') as f:
        data = json.load(f)

    # 1. Identify Top Repos
    repo_counts = Counter(item['repo_url'] for item in data)
    top_repos = [url for url, count in repo_counts.most_common(TOP_N_REPOS)]
    
    print(f"Top {TOP_N_REPOS} Repositories selected for Pilot:")
    for url in top_repos:
        print(f" - {url} ({repo_counts[url]} pairs)")

    # 2. Process
    results = {
        "ai": {"churn": 0, "contrib": 0, "pairs": 0, "ratios": []},
        "human": {"churn": 0, "contrib": 0, "pairs": 0, "ratios": []}
    }
    
    os.makedirs(REPO_DIR, exist_ok=True)

    for repo_url in top_repos:
        repo_name = get_repo_name(repo_url)
        local_dir = os.path.join(REPO_DIR, repo_name.replace('/', '_'))
        
        clone_repo(repo_url, local_dir)
        
        repo_pairs = [p for p in data if p['repo_url'] == repo_url]
        
        print(f"Analyzing {len(repo_pairs)} pairs in {repo_name}...")
        
        for pair in repo_pairs:
            # AI Analysis
            ai_res = analyze_pr_churn(local_dir, pair['ai_number'], pair['ai_merged_at'])
            if ai_res:
                results["ai"]["churn"] += ai_res["churn_lines"]
                results["ai"]["contrib"] += ai_res["initial_lines"]
                results["ai"]["pairs"] += 1
                results["ai"]["ratios"].append(ai_res["ratio"])

            # Human Analysis
            human_res = analyze_pr_churn(local_dir, pair['human_number'], pair['human_merged_at'])
            if human_res:
                results["human"]["churn"] += human_res["churn_lines"]
                results["human"]["contrib"] += human_res["initial_lines"]
                results["human"]["pairs"] += 1
                results["human"]["ratios"].append(human_res["ratio"])

    # 3. Report
    ai_avg_ratio = sum(results["ai"]["ratios"]) / len(results["ai"]["ratios"]) if results["ai"]["ratios"] else 0
    human_avg_ratio = sum(results["human"]["ratios"]) / len(results["human"]["ratios"]) if results["human"]["ratios"] else 0
    
    report = f"""# Pilot Study: Post-Merge Churn Ratio

**Metric**: `(Lines Modified in 90 days post-merge) / (Lines Added in PR)`
**Scope**: Top {TOP_N_REPOS} Repositories

## Results

| Metric | AI Code | Human Code |
| :--- | :--- | :--- |
| **Pairs Analyzed** | {results['ai']['pairs']} | {results['human']['pairs']} |
| **Avg Churn Ratio** | **{ai_avg_ratio:.4f}** | **{human_avg_ratio:.4f}** |
| **Total Lines Contributed** | {results['ai']['contrib']} | {results['human']['contrib']} |
| **Total Lines Churned** | {results['ai']['churn']} | {results['human']['churn']} |

## Intepretation
- A **higher ratio** indicates that the code required more updates/fixes after merging.
- **AI Ratio**: {ai_avg_ratio:.2f}
- **Human Ratio**: {human_avg_ratio:.2f}

"""
    with open(OUTPUT_REPORT, 'w') as f:
        f.write(report)
        
    print(f"Analysis complete. Report saved to {OUTPUT_REPORT}")
    print(report)

if __name__ == "__main__":
    main()
