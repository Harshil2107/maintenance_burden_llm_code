"""
RQ1: AI vs Human Code Complexity Analysis (Pre/Post Delta)

This script iterates through matched AI/Human PR pairs, clones each repository
on demand, and performs a before-vs-after complexity delta analysis. For each PR
it identifies the changed files via git diff, measures their complexity at HEAD
(after the PR) and at HEAD^ (before the PR) using Lizard (all languages) and
Radon (Python), then computes Delta = After - Before. After analysis the
repository is immediately deleted to conserve disk space. Once all pairs are
processed, the script runs Mann-Whitney U and Cliff's Delta statistical tests
and generates comparison graphs (box-plots, bar charts, violin plots).
"""

import json
import os
import re
import shutil
import subprocess
import sys
import warnings
import pandas as pd
import numpy as np
from scipy import stats as sp_stats
import matplotlib
matplotlib.use('Agg')  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from radon.complexity import cc_visit, cc_rank
from radon.metrics import h_visit
from radon.raw import analyze as raw_analyze
import lizard

# Force unbuffered output
import functools
print = functools.partial(print, flush=True)

warnings.filterwarnings("ignore")

# ── Configuration ────────────────────────────────────────────────────────────
INPUT_FILE  = os.path.join(os.path.dirname(__file__), "..", "datasets", "matched_pr_pairs_in_30_days_500st.json")
OUTPUT_CSV  = "rq1_complexity_results.csv"
REPOS_DIR   = "repos"

# Repos to skip (huge/problematic)
SKIP_REPOS = {
    "https://api.github.com/repos/oven-sh/bun",
    "https://api.github.com/repos/joshuafuller/ATAK-Maps",
    "https://api.github.com/repos/microsoft/vscode",
    "https://api.github.com/repos/opencv/opencv",
}

# Extensions Lizard supports
SUPPORTED_EXTS = (
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".java", ".cpp", ".c", ".h", ".hpp",
    ".cs", ".go", ".rs", ".rb", ".swift",
    ".scala", ".lua", ".php", ".m", ".kt",
    ".zig",
)

# ── Git / System Helpers ─────────────────────────────────────────────────────

def run_git(cmd: str, cwd: str, timeout: int = 60) -> str | None:
    try:
        r = subprocess.run(cmd, cwd=cwd, shell=True, check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, timeout=timeout)
        return r.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None

def clone_repo(repo_url: str, repo_path: str) -> bool:
    # Fix API URL to Clone URL
    # Replace https://api.github.com/repos/User/Repo -> https://github.com/User/Repo
    original_url = repo_url
    repo_url = re.sub(r'https?://api\.github\.com/repos/', 'https://github.com/', repo_url)
    
    if repo_url != original_url:
        print(f"    Fixed URL: {original_url} -> {repo_url}")
    
    if os.path.exists(repo_path):
        return True
    print(f"    Cloning {repo_url} ...")
    ret = run_git(f"git clone --depth 1 {repo_url} {repo_path}", cwd=".")
    if ret is None:
        # Fallback to full clone if depth 1 fails (unlikely)
        ret = run_git(f"git clone {repo_url} {repo_path}", cwd=".")
    return os.path.isdir(repo_path)

def default_branch(repo_path: str) -> str:
    res = run_git("git symbolic-ref refs/remotes/origin/HEAD", repo_path)
    if res:
        return res.split("/")[-1]
    return "main"

def checkout_pr(repo: str, pr: int, defbranch: str) -> bool:
    """Fetch and checkout a PR branch."""
    run_git("git checkout -f HEAD", repo)
    br = f"pr-{pr}"
    run_git(f"git branch -D {br}", repo)
    # Fetch PR head
    if run_git(f"git fetch origin pull/{pr}/head:{br} --depth=10", repo) is None:
        return False
    run_git(f"git checkout {br}", repo)
    # Fetch base branch (usually main) for comparison if needed
    run_git(f"git fetch origin {defbranch} --depth=10", repo)
    return True

# ── Complexity Analysis ──────────────────────────────────────────────────────

def get_metrics_for_file(filepath: str) -> dict:
    """
    Compute complexity metrics for a file (Radon for Python, Lizard for others).
    Returns a dict of metrics.
    """
    if not os.path.exists(filepath):
        return {}
    
    metrics = {}
    
    # Lizard Analysis (available for all supported languages)
    try:
        liz = lizard.analyze_file(filepath)
        metrics["loc"] = liz.nloc
        metrics["cc_avg"] = liz.average_cyclomatic_complexity
        metrics["cc_max"] = max([f.cyclomatic_complexity for f in liz.function_list], default=0)
        metrics["num_funcs"] = len(liz.function_list)
        metrics["tokens"] = liz.token_count
    except Exception:
        pass

    # Radon Analysis (Python only)
    if filepath.endswith(".py"):
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                source = f.read()
            
            # Cyclic Complexity
            cc = cc_visit(source)
            if cc:
                metrics["radon_cc_avg"] = sum(c.complexity for c in cc) / len(cc)
                metrics["radon_cc_max"] = max(c.complexity for c in cc)
                metrics["radon_num_funcs"] = len(cc)
            
            # Halstead
            h = h_visit(source)
            metrics["h_volume"] = h.total.volume
            metrics["h_difficulty"] = h.total.difficulty
            metrics["h_effort"] = h.total.effort
            
            # Raw
            raw = raw_analyze(source)
            metrics["loc_raw"] = raw.loc
            metrics["lloc"] = raw.lloc
            metrics["sloc"] = raw.sloc
            metrics["comments"] = raw.comments
            
        except Exception:
            pass
            
    return metrics

def analyze_pr_delta(repo_path: str, pr_number: int, defbranch: str,
                     repo_name: str = "", pr_type: str = "") -> list[dict]:
    """
    Calculate (After - Before) complexity delta for changed files in a PR.
    Prints per-file complexity information.
    """
    if not checkout_pr(repo_path, pr_number, defbranch):
        print(f"      ✗ Could not checkout PR #{pr_number}")
        return []

    # 1. Identify changed files
    changed_files = run_git(f"git diff --name-only HEAD^ HEAD", repo_path)
    if not changed_files:
        print(f"      (no file changes detected)")
        return []
    
    files = [f for f in changed_files.splitlines() if f.strip() and f.endswith(SUPPORTED_EXTS)]
    if not files:
        print(f"      (no supported code files changed)")
        return []
    
    results = []

    # 2. Measure AFTER (at HEAD)
    metrics_after = {}
    for f in files:
        metrics_after[f] = get_metrics_for_file(os.path.join(repo_path, f))

    # 3. Checkout BEFORE (HEAD^)
    run_git("git checkout HEAD^", repo_path)
    
    # 4. Measure BEFORE (at HEAD^)
    metrics_before = {}
    for f in files:
        metrics_before[f] = get_metrics_for_file(os.path.join(repo_path, f))

    # 5. Calculate Delta & Print
    for f in files:
        ma = metrics_after.get(f, {})
        mb = metrics_before.get(f, {})
        
        row = {"filename": f, "lang": os.path.splitext(f)[1]}
        
        # Calculate deltas for all numeric keys
        all_keys = set(ma.keys()) | set(mb.keys())
        for k in all_keys:
            val_a = ma.get(k, 0)
            val_b = mb.get(k, 0)
            if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                row[f"delta_{k}"] = val_a - val_b
                row[f"post_{k}"] = val_a
                row[f"pre_{k}"] = val_b
        
        # ── Verbose per-file print ──
        is_new = not mb  # file didn't exist before
        cc_pre  = mb.get("cc_max", 0)
        cc_post = ma.get("cc_max", 0)
        cc_delta = cc_post - cc_pre
        loc_pre  = mb.get("loc", 0) or 0
        loc_post = ma.get("loc", 0) or 0
        loc_delta = loc_post - loc_pre
        tag = "[NEW]" if is_new else ""
        sign_cc  = "+" if cc_delta > 0 else ""
        sign_loc = "+" if loc_delta > 0 else ""
        short = os.path.basename(f)
        print(f"      {tag:>5} {short:<35} CC: {cc_pre}→{cc_post} (Δ{sign_cc}{cc_delta})  LOC: {loc_pre}→{loc_post} (Δ{sign_loc}{loc_delta})")
        
        results.append(row)

    return results

# ── Main ─────────────────────────────────────────────────────────────────────

MAX_PAIRS = 50  # Stop after this many successfully analysed pairs

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE) as f:
        pairs = json.load(f)

    print(f"Total PR pairs: {len(pairs)}  (will stop after {MAX_PAIRS})\n")

    all_records = []   # collect everything in memory
    done = 0

    for i, pair in enumerate(pairs):
        if done >= MAX_PAIRS:
            break

        repo_url = pair["repo_url"]
        repo_name = repo_url.split("/")[-1]

        if repo_url in SKIP_REPOS:
            print(f"[{i+1}] Skipping blacklisted: {repo_name}")
            continue

        repo_path = os.path.join(REPOS_DIR, repo_name)

        print(f"[{i+1}/{len(pairs)}] Processing {repo_name}  (done={done}/{MAX_PAIRS}) ...")

        try:
            os.makedirs(REPOS_DIR, exist_ok=True)
            if not clone_repo(repo_url, repo_path):
                print(f"  ✗ Failed to clone {repo_name}")
                if os.path.exists(repo_path):
                    shutil.rmtree(repo_path, ignore_errors=True)
                continue

            db = default_branch(repo_path)

            # AI PR
            ai_pr = pair["ai_number"]
            print(f"  ▸ Analyzing AI PR #{ai_pr} ({repo_name}) ...")
            ai_deltas = analyze_pr_delta(repo_path, ai_pr, db,
                                         repo_name=repo_name, pr_type="AI")
            for r in ai_deltas:
                r.update({"type": "AI", "pair_id": i, "repo": repo_name, "pr": ai_pr})

            # Human PR
            hu_pr = pair["human_number"]
            print(f"  ▸ Analyzing Human PR #{hu_pr} ({repo_name}) ...")
            hu_deltas = analyze_pr_delta(repo_path, hu_pr, db,
                                         repo_name=repo_name, pr_type="Human")
            for r in hu_deltas:
                r.update({"type": "Human", "pair_id": i, "repo": repo_name, "pr": hu_pr})

            batch = ai_deltas + hu_deltas
            if batch:
                all_records.extend(batch)
                print(f"  ✓ Collected {len(batch)} records  (total so far: {len(all_records)})")
                done += 1
            else:
                print("  - No supported files changed.")

        except Exception as e:
            print(f"  ✗ Error processing {repo_name}: {e}")

        finally:
            if os.path.exists(repo_path):
                print(f"  ⟳ Deleting {repo_name} to free space...")
                shutil.rmtree(repo_path, ignore_errors=True)

    print(f"\n{'='*80}")
    print(f"  Done!  Analysed {done} pairs  →  {len(all_records)} file-level records")
    print(f"{'='*80}")

    if not all_records:
        print("No data collected — nothing to plot.")
        return

    df = pd.DataFrame(all_records)
    # coerce numeric cols
    for c in df.columns:
        if c.startswith(("delta_", "pre_", "post_")):
            df[c] = pd.to_numeric(df[c], errors="coerce")

    print_stats(df)
    generate_graphs(df)


# ── Statistical Analysis ─────────────────────────────────────────────────────

def cliffs_delta(lst1, lst2):
    """Cliff's Delta effect size (range -1 to +1)."""
    lst1, lst2 = sorted(lst1), sorted(lst2)
    m, n = len(lst1), len(lst2)
    if m == 0 or n == 0:
        return 0.0
    j = 0
    t = 0
    for x in lst1:
        while j < n and lst2[j] < x:
            j += 1
        t += j * 2 - n + lst2.count(x)
    return t / (m * n)


def print_stats(df: pd.DataFrame):
    """Print statistical comparison of AI vs Human deltas."""
    print(f"\n  AI files : {len(df[df['type']=='AI'])}")
    print(f"  Human files : {len(df[df['type']=='Human'])}")

    metrics = [
        "delta_cc_max", "delta_cc_avg", "delta_loc", "delta_tokens",
        "delta_num_funcs", "delta_sloc",
        "delta_radon_cc_max", "delta_h_volume", "delta_h_effort", "delta_h_difficulty",
    ]

    print(f"\n{'Metric':<25} | {'AI Mean':>10} | {'Hu Mean':>10} | {'p-value':>10} | {'Cliff d':>8} | Sig")
    print("-" * 85)

    for m in metrics:
        if m not in df.columns:
            continue
        sub = df.dropna(subset=[m])
        ai = sub[sub["type"] == "AI"][m]
        hu = sub[sub["type"] == "Human"][m]

        if len(ai) < 5 or len(hu) < 5:
            print(f"{m:<25} | (insufficient data: AI={len(ai)}, Hu={len(hu)})")
            continue

        try:
            _, p = sp_stats.mannwhitneyu(ai, hu, alternative="two-sided")
        except ValueError:
            p = 1.0

        d = cliffs_delta(ai.tolist(), hu.tolist())
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""

        print(f"{m:<25} | {ai.mean():>10.2f} | {hu.mean():>10.2f} | {p:>10.3e} | {d:>8.3f} | {sig}")
    print()


# ── Graph Generation ─────────────────────────────────────────────────────────

def generate_graphs(df: pd.DataFrame):
    """Create comparison graphs and save as PNG files."""
    out_dir = "graphs"
    os.makedirs(out_dir, exist_ok=True)

    ai = df[df["type"] == "AI"]
    hu = df[df["type"] == "Human"]

    # ── 1. Box-plots for key delta metrics ────────────────────────────────
    box_metrics = [
        ("delta_cc_max",       "Δ Max Cyclomatic Complexity"),
        ("delta_loc",          "Δ Lines of Code (LOC)"),
        ("delta_sloc",         "Δ Source Lines of Code (SLOC)"),
        ("delta_h_volume",     "Δ Halstead Volume"),
        ("delta_h_difficulty", "Δ Halstead Difficulty"),
        ("delta_num_funcs",    "Δ Number of Functions"),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle("AI vs Human — Complexity Delta Box-Plots", fontsize=16, fontweight="bold")
    axes = axes.flatten()

    for idx, (col, label) in enumerate(box_metrics):
        ax = axes[idx]
        ai_vals = ai[col].dropna()
        hu_vals = hu[col].dropna()

        if len(ai_vals) == 0 and len(hu_vals) == 0:
            ax.set_visible(False)
            continue

        bp = ax.boxplot(
            [ai_vals, hu_vals],
            labels=["AI", "Human"],
            patch_artist=True,
            showfliers=False,        # hide extreme outliers for clarity
            widths=0.5,
        )
        bp["boxes"][0].set_facecolor("#4C72B0")
        bp["boxes"][1].set_facecolor("#DD8452")
        ax.set_title(label, fontsize=11)
        ax.axhline(0, color="grey", linewidth=0.8, linestyle="--")
        ax.set_ylabel("Delta value")

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    path1 = os.path.join(out_dir, "boxplots_ai_vs_human.png")
    plt.savefig(path1, dpi=150)
    plt.close()
    print(f"📊 Saved box-plots  → {path1}")

    # ── 2. Grouped bar chart of mean deltas ───────────────────────────────
    bar_metrics = [
        ("delta_cc_max",   "CC Max"),
        ("delta_cc_avg",   "CC Avg"),
        ("delta_loc",      "LOC"),
        ("delta_sloc",     "SLOC"),
        ("delta_h_volume", "Halstead\nVolume"),
        ("delta_num_funcs","Num\nFuncs"),
    ]

    labels, ai_means, hu_means = [], [], []
    for col, lbl in bar_metrics:
        if col not in df.columns:
            continue
        a = ai[col].dropna()
        h = hu[col].dropna()
        if len(a) < 2 or len(h) < 2:
            continue
        labels.append(lbl)
        ai_means.append(a.mean())
        hu_means.append(h.mean())

    if labels:
        x = np.arange(len(labels))
        w = 0.35
        fig, ax = plt.subplots(figsize=(10, 6))
        bars1 = ax.bar(x - w/2, ai_means, w, label="AI",    color="#4C72B0")
        bars2 = ax.bar(x + w/2, hu_means, w, label="Human", color="#DD8452")
        ax.set_ylabel("Mean Delta")
        ax.set_title("AI vs Human — Mean Complexity Delta", fontsize=14, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.axhline(0, color="grey", linewidth=0.8, linestyle="--")
        ax.legend()

        # value labels on bars
        for bar in bars1:
            ax.annotate(f"{bar.get_height():.1f}",
                        xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                        ha="center", va="bottom" if bar.get_height() >= 0 else "top",
                        fontsize=8)
        for bar in bars2:
            ax.annotate(f"{bar.get_height():.1f}",
                        xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                        ha="center", va="bottom" if bar.get_height() >= 0 else "top",
                        fontsize=8)

        plt.tight_layout()
        path2 = os.path.join(out_dir, "bar_mean_deltas.png")
        plt.savefig(path2, dpi=150)
        plt.close()
        print(f"📊 Saved bar chart  → {path2}")

    # ── 3. Violin plot for CC distribution ────────────────────────────────
    cc_col = "delta_cc_max"
    if cc_col in df.columns:
        ai_cc = ai[cc_col].dropna()
        hu_cc = hu[cc_col].dropna()
        if len(ai_cc) > 2 and len(hu_cc) > 2:
            fig, ax = plt.subplots(figsize=(8, 6))
            parts = ax.violinplot([ai_cc, hu_cc], positions=[1, 2], showmeans=True, showmedians=True)
            parts["bodies"][0].set_facecolor("#4C72B0")
            parts["bodies"][1].set_facecolor("#DD8452")
            ax.set_xticks([1, 2])
            ax.set_xticklabels(["AI", "Human"])
            ax.set_ylabel("Δ Max Cyclomatic Complexity")
            ax.set_title("AI vs Human — CC Delta Distribution", fontsize=14, fontweight="bold")
            ax.axhline(0, color="grey", linewidth=0.8, linestyle="--")
            plt.tight_layout()
            path3 = os.path.join(out_dir, "violin_cc_delta.png")
            plt.savefig(path3, dpi=150)
            plt.close()
            print(f"📊 Saved violin plot → {path3}")

    print(f"\n✅  All graphs saved to ./{out_dir}/")


if __name__ == "__main__":
    main()
