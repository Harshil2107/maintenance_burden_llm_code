"""
RQ3a: Hot/Cold File Analysis

For each PR, computes a file heat score — the average number of commits that
touched each changed file in the 90 days before the PR was merged. This answers
the question: "Do AI agents systematically work on colder (less active) files?"

The script clones each repo, checks out the PR, identifies changed files, and
counts prior commits for each file. Results are saved as a CSV and comparison
plots (boxplot + density) are generated.
"""

import json
import os
import re
import subprocess
import shutil
import csv
import sys
from collections import Counter
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from scipy import stats as sp_stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import functools
print = functools.partial(print, flush=True)

# ── Configuration ────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(SCRIPT_DIR, "..", "datasets",
                          "matched_pr_pairs_in_30_days_500st.json")
OUTPUT_CSV = os.path.join(SCRIPT_DIR, "file_heat_scores.csv")
PLOT_DIR   = os.path.join(SCRIPT_DIR, "plots_heat")
REPOS_DIR  = os.path.join(SCRIPT_DIR, "repos")

HEAT_WINDOW_DAYS = 90   # look-back window for file activity
MAX_PAIRS = None         # None = all pairs

SKIP_REPOS = {
    "https://api.github.com/repos/oven-sh/bun",
    "https://api.github.com/repos/microsoft/vscode",
    "https://api.github.com/repos/opencv/opencv",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def run_git(cmd, cwd, timeout=120):
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
    print(f"    Cloning {url} ...")
    run_git(f"git clone {url} {repo_path}", cwd=".", timeout=300)
    return os.path.isdir(repo_path)


def default_branch(repo_path):
    res = run_git("git symbolic-ref refs/remotes/origin/HEAD", repo_path)
    return res.split("/")[-1] if res else "main"


def checkout_pr(repo, pr, defbranch):
    run_git("git checkout -f HEAD", repo)
    br = f"pr-{pr}"
    run_git(f"git branch -D {br}", repo)
    if run_git(f"git fetch origin pull/{pr}/head:{br} --depth=50", repo) is None:
        return False
    run_git(f"git checkout {br}", repo)
    # Fetch enough history for heat computation
    run_git(f"git fetch origin {defbranch} --depth=200", repo)
    return True


def get_repo_id(repo_url):
    parts = repo_url.rstrip("/").split("/")
    return f"{parts[-2]}/{parts[-1]}"


# ── Heat Score Computation ────────────────────────────────────────────────────

def compute_file_heat(repo_path, merge_date_str):
    """
    For each changed file in the current HEAD commit, count the number of
    commits that touched it in the HEAT_WINDOW_DAYS before merge_date.
    Returns (mean_heat, file_count, file_heats_dict).
    """
    # Identify changed files
    diff = run_git("git diff --name-only HEAD^ HEAD", repo_path)
    if not diff:
        return None, 0, {}

    files = [f.strip() for f in diff.splitlines() if f.strip()]
    if not files:
        return None, 0, {}

    # Parse merge date
    try:
        dt = datetime.fromisoformat(merge_date_str.replace('Z', '+00:00'))
    except Exception:
        return None, 0, {}

    since = (dt - timedelta(days=HEAT_WINDOW_DAYS)).strftime("%Y-%m-%d")
    before = dt.strftime("%Y-%m-%d")

    heats = {}
    for filepath in files:
        # Count commits touching this file in the look-back window
        cmd = (f"git log --oneline --since='{since}' --before='{before}' "
               f"-- '{filepath}'")
        out = run_git(cmd, repo_path, timeout=30)
        if out:
            heats[filepath] = len(out.splitlines())
        else:
            heats[filepath] = 0

    if not heats:
        return None, 0, {}

    mean_heat = np.mean(list(heats.values()))
    return mean_heat, len(heats), heats


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE) as f:
        pairs = json.load(f)

    limit = MAX_PAIRS or len(pairs)
    print(f"Total PR pairs: {len(pairs)}  (processing: {limit})\n")

    rows = []
    done = 0

    for i, pair in enumerate(pairs):
        if done >= limit:
            break

        repo_url  = pair["repo_url"]
        repo_id   = get_repo_id(repo_url)
        repo_name = repo_url.split("/")[-1]
        repo_path = os.path.join(REPOS_DIR, repo_name)

        if repo_url in SKIP_REPOS:
            print(f"[{i+1}] Skipping blacklisted: {repo_name}")
            continue

        print(f"[{i+1}/{len(pairs)}] {repo_id}  (done={done}/{limit})")

        try:
            os.makedirs(REPOS_DIR, exist_ok=True)
            if not clone_repo(repo_url, repo_path):
                print(f"  ✗ Clone failed")
                continue

            db = default_branch(repo_path)

            # ── AI PR ──
            ai_pr = pair["ai_number"]
            ai_merge = pair.get("ai_merged_at", "")
            if ai_merge and checkout_pr(repo_path, ai_pr, db):
                ai_heat, ai_nfiles, _ = compute_file_heat(repo_path, ai_merge)
                if ai_heat is not None:
                    rows.append({
                        "repo": repo_id, "pr": ai_pr,
                        "author_type": "AI",
                        "mean_file_heat": round(ai_heat, 4),
                        "num_files_changed": ai_nfiles,
                        "task_type": pair.get("type", "unknown"),
                        "merge_date": ai_merge,
                    })
                    print(f"  AI  PR#{ai_pr}: heat={ai_heat:.2f} ({ai_nfiles} files)")
                else:
                    print(f"  AI  PR#{ai_pr}: no data")
            else:
                print(f"  AI  PR#{ai_pr}: checkout failed or no merge date")

            # ── Human PR ──
            hu_pr = pair["human_number"]
            hu_merge = pair.get("human_merged_at", "")
            if hu_merge and checkout_pr(repo_path, hu_pr, db):
                hu_heat, hu_nfiles, _ = compute_file_heat(repo_path, hu_merge)
                if hu_heat is not None:
                    rows.append({
                        "repo": repo_id, "pr": hu_pr,
                        "author_type": "Human",
                        "mean_file_heat": round(hu_heat, 4),
                        "num_files_changed": hu_nfiles,
                        "task_type": pair.get("type", "unknown"),
                        "merge_date": hu_merge,
                    })
                    print(f"  Hu  PR#{hu_pr}: heat={hu_heat:.2f} ({hu_nfiles} files)")
                else:
                    print(f"  Hu  PR#{hu_pr}: no data")
            else:
                print(f"  Hu  PR#{hu_pr}: checkout failed or no merge date")

            done += 1

        except Exception as e:
            print(f"  ✗ Error: {e}")

        finally:
            if os.path.exists(repo_path):
                shutil.rmtree(repo_path, ignore_errors=True)

    # ── Save CSV ──────────────────────────────────────────────────────────
    if not rows:
        print("No data collected.")
        return

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\n✅ Saved {len(df)} rows to {OUTPUT_CSV}")

    # ── Statistics ────────────────────────────────────────────────────────
    ai  = df[df["author_type"] == "AI"]["mean_file_heat"]
    hu  = df[df["author_type"] == "Human"]["mean_file_heat"]

    print(f"\n  AI  heat:  mean={ai.mean():.2f}  median={ai.median():.2f}  n={len(ai)}")
    print(f"  Hu  heat:  mean={hu.mean():.2f}  median={hu.median():.2f}  n={len(hu)}")

    if len(ai) >= 5 and len(hu) >= 5:
        stat, p = sp_stats.mannwhitneyu(ai, hu, alternative="two-sided")
        print(f"  Mann-Whitney U:  p = {p:.4e}")

        # Cliff's delta
        n1, n2 = len(ai), len(hu)
        ai_arr, hu_arr = ai.values, hu.values
        more = sum(1 for a in ai_arr for h in hu_arr if a > h)
        less = sum(1 for a in ai_arr for h in hu_arr if a < h)
        d = (more - less) / (n1 * n2)
        print(f"  Cliff's delta:   d = {d:.4f}")

    # ── Plots ─────────────────────────────────────────────────────────────
    generate_plots(df)


def generate_plots(df):
    os.makedirs(PLOT_DIR, exist_ok=True)

    ai = df[df["author_type"] == "AI"]["mean_file_heat"]
    hu = df[df["author_type"] == "Human"]["mean_file_heat"]

    # 1. Boxplot
    fig, ax = plt.subplots(figsize=(8, 5))
    bp = ax.boxplot([ai, hu], tick_labels=["AI", "Human"],
                    patch_artist=True, showfliers=False, widths=0.5)
    bp["boxes"][0].set_facecolor("#4C72B0")
    bp["boxes"][1].set_facecolor("#DD8452")
    ax.set_ylabel("Mean File Heat (commits in 90d pre-merge)")
    ax.set_title("File Activity Before PR — AI vs Human", fontweight="bold")
    ax.axhline(ai.median(), color="#4C72B0", linestyle="--", alpha=0.5)
    ax.axhline(hu.median(), color="#DD8452", linestyle="--", alpha=0.5)
    plt.tight_layout()
    p1 = os.path.join(PLOT_DIR, "file_heat_boxplot.png")
    plt.savefig(p1, dpi=150)
    plt.close()
    print(f"📊 Saved boxplot → {p1}")

    # 2. Density / KDE plot
    fig, ax = plt.subplots(figsize=(8, 5))
    ai.plot.kde(ax=ax, label="AI", color="#4C72B0", lw=2)
    hu.plot.kde(ax=ax, label="Human", color="#DD8452", lw=2)
    ax.set_xlabel("Mean File Heat (commits in 90d pre-merge)")
    ax.set_ylabel("Density")
    ax.set_title("File Heat Distribution — AI vs Human", fontweight="bold")
    ax.legend()
    ax.set_xlim(left=0)
    plt.tight_layout()
    p2 = os.path.join(PLOT_DIR, "file_heat_density.png")
    plt.savefig(p2, dpi=150)
    plt.close()
    print(f"📊 Saved density plot → {p2}")


if __name__ == "__main__":
    main()
