"""
RQ2 Data Preparation — Extract Covariates

Extracts per-PR covariates from the matched PR pairs dataset:
  - Dominant language (majority file extension in git diff)
  - Task type (feat/fix/etc. from the dataset 'type' field)
  - Repo identifier (owner/name) for clustered standard errors

Outputs covariates.csv that can be joined with existing churn metrics.
"""

import json
import os
import re
import subprocess
import shutil
import sys
from collections import Counter

import functools
print = functools.partial(print, flush=True)

# ── Configuration ────────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE  = os.path.join(SCRIPT_DIR, "..", "datasets",
                           "matched_pr_pairs_in_30_days_500st.json")
OUTPUT_CSV  = os.path.join(SCRIPT_DIR, "covariates.csv")
REPOS_DIR   = os.path.join(SCRIPT_DIR, "repos")

# Map file extensions to language names
EXT_TO_LANG = {
    ".py": "Python", ".pyx": "Python",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".hpp": "C++",
    ".c": "C", ".h": "C",
    ".cs": "C#",
    ".swift": "Swift",
    ".kt": "Kotlin", ".kts": "Kotlin",
    ".scala": "Scala",
    ".php": "PHP",
    ".lua": "Lua",
    ".m": "Objective-C",
    ".zig": "Zig",
    ".dart": "Dart",
    ".vue": "Vue",
    ".svelte": "Svelte",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def run_git(cmd, cwd, timeout=60):
    try:
        r = subprocess.run(cmd, cwd=cwd, shell=True, check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, timeout=timeout)
        return r.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def clone_repo(repo_url, repo_path):
    url = re.sub(r'https?://api\.github\.com/repos/', 'https://github.com/',
                 repo_url)
    if os.path.exists(repo_path):
        return True
    run_git(f"git clone --depth 1 {url} {repo_path}", cwd=".")
    return os.path.isdir(repo_path)


def checkout_pr(repo, pr, defbranch):
    run_git("git checkout -f HEAD", repo)
    br = f"pr-{pr}"
    run_git(f"git branch -D {br}", repo)
    if run_git(f"git fetch origin pull/{pr}/head:{br} --depth=10", repo) is None:
        return False
    run_git(f"git checkout {br}", repo)
    return True


def default_branch(repo_path):
    res = run_git("git symbolic-ref refs/remotes/origin/HEAD", repo_path)
    if res:
        return res.split("/")[-1]
    return "main"


def dominant_language(repo_path):
    """Return the dominant source-code language from changed files in HEAD."""
    diff = run_git("git diff --name-only HEAD^ HEAD", repo_path)
    if not diff:
        return "Unknown"

    lang_counts = Counter()
    for f in diff.splitlines():
        ext = os.path.splitext(f)[1].lower()
        lang = EXT_TO_LANG.get(ext)
        if lang:
            lang_counts[lang] += 1

    if not lang_counts:
        return "Other"

    top_lang, top_count = lang_counts.most_common(1)[0]
    total = sum(lang_counts.values())
    if top_count / total >= 0.5:
        return top_lang
    return "Mixed"


def get_repo_id(repo_url):
    """Extract owner/name from repo URL."""
    parts = repo_url.rstrip("/").split("/")
    return f"{parts[-2]}/{parts[-1]}"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE) as f:
        pairs = json.load(f)

    print(f"Total PR pairs: {len(pairs)}")

    import csv
    rows = []
    processed = 0

    for i, pair in enumerate(pairs):
        repo_url  = pair["repo_url"]
        repo_id   = get_repo_id(repo_url)
        repo_name = repo_url.split("/")[-1]
        repo_path = os.path.join(REPOS_DIR, repo_name)
        task_type = pair.get("type", "unknown")

        print(f"[{i+1}/{len(pairs)}] {repo_id} ...")

        try:
            os.makedirs(REPOS_DIR, exist_ok=True)
            if not clone_repo(repo_url, repo_path):
                print(f"  ✗ Clone failed")
                continue

            db = default_branch(repo_path)

            # AI PR
            ai_pr = pair["ai_number"]
            if checkout_pr(repo_path, ai_pr, db):
                ai_lang = dominant_language(repo_path)
            else:
                ai_lang = "Unknown"

            rows.append({
                "repo": repo_id,
                "pr": ai_pr,
                "author_type": "AI",
                "dominant_language": ai_lang,
                "task_type": task_type,
                "agent": pair.get("ai_agent", pair.get("agent", "")),
            })

            # Human PR
            hu_pr = pair["human_number"]
            if checkout_pr(repo_path, hu_pr, db):
                hu_lang = dominant_language(repo_path)
            else:
                hu_lang = "Unknown"

            rows.append({
                "repo": repo_id,
                "pr": hu_pr,
                "author_type": "Human",
                "dominant_language": hu_lang,
                "task_type": task_type,
                "agent": "",
            })

            processed += 1
            print(f"  ✓ AI={ai_lang}, Human={hu_lang}, type={task_type}")

        except Exception as e:
            print(f"  ✗ Error: {e}")

        finally:
            if os.path.exists(repo_path):
                shutil.rmtree(repo_path, ignore_errors=True)

    # Write CSV
    if rows:
        with open(OUTPUT_CSV, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
        print(f"\n✅ Saved {len(rows)} rows to {OUTPUT_CSV}")
    else:
        print("No data collected.")


if __name__ == "__main__":
    main()
