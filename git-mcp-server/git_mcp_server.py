"""
Git Workflow Assistant - MCP Server
Dynamic Multi-Repo Version
Works across multiple Antigravity windows

Install:
    pip install fastmcp

Run:
    python git_mcp_server.py
"""

import sys
import subprocess
from pathlib import Path
from typing import Optional

# Windows fix — prevents EOF/encoding errors with stdio transport
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from fastmcp import FastMCP

mcp = FastMCP(
    name="git-workflow-assistant",
    instructions="Provides rich Git context to help understand repo history, branches, diffs, and blame information.",
)


# ─────────────────────────────────────────
# Core Git Helpers
# ─────────────────────────────────────────

def _detect_repo_root(start_path: Optional[str] = None) -> Optional[str]:
    """
    Detect git repository root starting from a path.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            cwd=start_path or Path.cwd(),
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except Exception:
        return None


def _run_git(args: list[str], repo_path: Optional[str] = None) -> str:
    """
    Run git command inside detected repo.
    """
    try:
        repo_root = repo_path or _detect_repo_root()

        if not repo_root:
            return "[error] Not inside a git repository."

        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=repo_root,
        )

        if result.returncode != 0:
            return f"[git error] {result.stderr.strip()}"

        return result.stdout.strip()

    except FileNotFoundError:
        return "[error] git is not installed or not in PATH"
    except Exception as e:
        return f"[error] {str(e)}"


# ─────────────────────────────────────────
# TOOL 1 — Recent Commits
# ─────────────────────────────────────────
@mcp.tool()
def get_recent_commits(
    repo_path: Optional[str] = None,
    limit: int = 20,
    branch: str = "HEAD",
) -> str:
    limit = min(limit, 100)
    fmt = "%h | %as | %an | %s"

    output = _run_git(
        ["log", branch, f"--max-count={limit}", f"--pretty=format:{fmt}"],
        repo_path,
    )

    if not output or output.startswith("["):
        return output or "No commits found."

    header = f"{'Hash':<8} | {'Date':<12} | {'Author':<20} | Subject\n" + "-" * 80
    return header + "\n" + output


# ─────────────────────────────────────────
# TOOL 2 — Branch Diff
# ─────────────────────────────────────────
@mcp.tool()
def diff_branch(
    repo_path: Optional[str] = None,
    base: str = "main",
    target: str = "HEAD",
    stat_only: bool = False,
) -> str:
    if stat_only:
        return _run_git(["diff", "--stat", f"{base}...{target}"], repo_path)
    return _run_git(["diff", f"{base}...{target}"], repo_path)


# ─────────────────────────────────────────
# TOOL 3 — List Branches
# ─────────────────────────────────────────
@mcp.tool()
def list_branches(
    repo_path: Optional[str] = None,
    include_remote: bool = False,
) -> str:

    fmt = "%(refname:short)|%(objectname:short)|%(committerdate:short)|%(subject)"
    refs = ["refs/heads/"]

    if include_remote:
        refs.append("refs/remotes/")

    lines = []
    for ref in refs:
        raw = _run_git(
            ["for-each-ref", "--sort=-committerdate", f"--format={fmt}", ref],
            repo_path,
        )
        if raw and not raw.startswith("["):
            lines.append(raw)

    if not lines:
        return "No branches found."

    header = f"{'Branch':<35} | {'Hash':<8} | {'Date':<12} | Last Commit\n" + "-" * 90
    rows = []

    for block in lines:
        for line in block.splitlines():
            parts = line.split("|", 3)
            if len(parts) == 4:
                rows.append(
                    f"{parts[0]:<35} | {parts[1]:<8} | {parts[2]:<12} | {parts[3]}"
                )

    return header + "\n" + "\n".join(rows)


# ─────────────────────────────────────────
# TOOL 4 — Git Blame
# ─────────────────────────────────────────
@mcp.tool()
def get_blame(
    filepath: str,
    repo_path: Optional[str] = None,
    start_line: int = 1,
    end_line: int = 50,
) -> str:
    return _run_git(
        ["blame", f"-L{start_line},{end_line}", "--date=short", filepath],
        repo_path,
    )


# ─────────────────────────────────────────
# TOOL 5 — File History
# ─────────────────────────────────────────
@mcp.tool()
def get_file_history(
    filepath: str,
    repo_path: Optional[str] = None,
    limit: int = 15,
) -> str:

    limit = min(limit, 50)
    fmt = "%h | %as | %an | %s"

    output = _run_git(
        ["log", f"--max-count={limit}", f"--pretty=format:{fmt}", "--", filepath],
        repo_path,
    )

    if not output or output.startswith("["):
        return output or f"No commits found for {filepath}."

    header = f"History of: {filepath}\n{'Hash':<8} | {'Date':<12} | {'Author':<20} | Subject\n" + "-" * 80
    return header + "\n" + output


# ─────────────────────────────────────────
# TOOL 6 — Working Tree Status
# ─────────────────────────────────────────
@mcp.tool()
def get_working_tree_status(repo_path: Optional[str] = None) -> str:
    status = _run_git(["status", "--short"], repo_path)
    stat = _run_git(["diff", "--stat", "HEAD"], repo_path)

    parts = []

    if status and not status.startswith("["):
        parts.append("=== Working Tree Status ===\n" + status)

    if stat and not stat.startswith("["):
        parts.append("=== Diff Stat vs HEAD ===\n" + stat)

    return "\n\n".join(parts) if parts else "Working tree is clean."


# ─────────────────────────────────────────
# TOOL 7 — Search Commits
# ─────────────────────────────────────────
@mcp.tool()
def search_commits(
    keyword: str,
    repo_path: Optional[str] = None,
    limit: int = 20,
) -> str:

    limit = min(limit, 100)
    fmt = "%h | %as | %an | %s"

    output = _run_git(
        ["log", f"--max-count={limit}", f"--pretty=format:{fmt}", f"--grep={keyword}"],
        repo_path,
    )

    if not output or output.startswith("["):
        return output or f"No commits matching '{keyword}'."

    header = f"Commits matching '{keyword}':\n{'Hash':<8} | {'Date':<12} | {'Author':<20} | Subject\n" + "-" * 80
    return header + "\n" + output


# ─────────────────────────────────────────
# TOOL 8 — Tags
# ─────────────────────────────────────────
@mcp.tool()
def list_tags(
    repo_path: Optional[str] = None,
    limit: int = 20,
) -> str:

    raw = _run_git(
        ["tag", "--sort=-creatordate", "--format=%(refname:short) | %(creatordate:short) | %(subject)"],
        repo_path,
    )

    if not raw or raw.startswith("["):
        return raw or "No tags found."

    lines = raw.splitlines()[:limit]
    return "Recent tags:\n" + "\n".join(lines)


# ─────────────────────────────────────────
# ENTRY
# ─────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8000)