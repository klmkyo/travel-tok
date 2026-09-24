#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""Track which committed English sources each locale was last synced from."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
STATE_PATH = SCRIPT_DIR / "i18n" / "sync-state.json"

ASSETS: dict[str, dict[str, str]] = {
    "messages": {
        "label": "App messages",
        "source": "apps/mobile/src/features/i18n/messages/en.ts",
        "target_directory": "apps/mobile/src/features/i18n/messages",
        "target_suffix": ".ts",
    },
}


@dataclass(frozen=True)
class LocaleSync:
    target_file: str
    source_commit: str
    source_hash: str
    target_hash: str
    synced_at: str


def run_git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def get_repo_root() -> Path:
    return Path(run_git(Path.cwd(), "rev-parse", "--show-toplevel"))


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"assets": {}}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def get_locale_sync(state: dict[str, Any], asset_id: str, locale: str) -> LocaleSync | None:
    entry = state.get("assets", {}).get(asset_id, {}).get("locales", {}).get(locale)
    if entry is None:
        return None

    return LocaleSync(
        target_file=entry["target_file"],
        source_commit=entry["source_commit"],
        source_hash=entry["source_hash"],
        target_hash=entry["target_hash"],
        synced_at=entry["synced_at"],
    )


def file_hash(repo_root: Path, relative_path: str) -> str:
    return hashlib.sha256((repo_root / relative_path).read_bytes()).hexdigest()


def source_diff(repo_root: Path, source_file: str, baseline_commit: str) -> str:
    return run_git(repo_root, "diff", baseline_commit, "--", source_file)


def is_worktree_clean(repo_root: Path) -> bool:
    return not run_git(repo_root, "status", "--porcelain")


def is_source_committed(repo_root: Path, source_file: str) -> bool:
    result = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", source_file],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise subprocess.CalledProcessError(
        result.returncode,
        result.args,
        result.stdout,
        result.stderr,
    )


def discover_locales(repo_root: Path, asset: dict[str, str]) -> dict[str, str]:
    target_directory = repo_root / asset["target_directory"]
    target_suffix = asset["target_suffix"]
    source_file = asset["source"]

    return {
        target_file.stem: str(target_file.relative_to(repo_root))
        for target_file in sorted(target_directory.glob(f"*{target_suffix}"))
        if str(target_file.relative_to(repo_root)) != source_file
    }


def selected_locales(
    locales: dict[str, str], locale_filter: str | None
) -> dict[str, str]:
    if locale_filter is None:
        return locales
    if locale_filter not in locales:
        available = ", ".join(locales) or "none"
        raise SystemExit(f"Unknown locale '{locale_filter}'. Available locales: {available}.")
    return {locale_filter: locales[locale_filter]}


def format_status_line(
    repo_root: Path,
    source_file: str,
    target_file: str,
    sync: LocaleSync | None,
) -> str:
    if sync is None:
        return "never synced"

    if sync.target_file != target_file:
        return f"target file changed (was {sync.target_file})"
    if file_hash(repo_root, source_file) != sync.source_hash:
        return f"source out of date (baseline {sync.source_commit[:8]})"
    if file_hash(repo_root, target_file) != sync.target_hash:
        return "target changed since sync"
    return f"up to date (baseline {sync.source_commit[:8]})"


def cmd_status(repo_root: Path) -> int:
    state = load_state()

    for index, (asset_id, asset) in enumerate(ASSETS.items()):
        if index:
            print()

        print(f"{asset['label']}:")
        source_file = asset["source"]
        locales = discover_locales(repo_root, asset)
        if not locales:
            print("- no target locale files found")

        for locale, target_file in locales.items():
            sync = get_locale_sync(state, asset_id, locale)
            status = format_status_line(repo_root, source_file, target_file, sync)
            print(f"- {locale}: {status}")

    return 0


def cmd_diff(
    repo_root: Path,
    asset_filter: str | None,
    locale_filter: str | None,
    *,
    force: bool,
) -> int:
    if not force and not is_worktree_clean(repo_root):
        raise SystemExit("Locale sync must start from a clean worktree.")

    state = load_state()
    printed_any = False
    exit_code = 0

    for asset_id, asset in ASSETS.items():
        if asset_filter and asset_id != asset_filter:
            continue

        source_file = asset["source"]
        locales = selected_locales(discover_locales(repo_root, asset), locale_filter)
        for locale, target_file in locales.items():
            sync = get_locale_sync(state, asset_id, locale)
            if sync is None:
                print(f"=== {asset_id}/{locale}: never synced (full sync required) ===")
                print(f"source: {source_file}")
                print(f"target: {target_file}")
                print()
                printed_any = True
                exit_code = 1
                continue

            if sync.target_file != target_file:
                print(f"=== {asset_id}/{locale}: target file changed ===")
                print(f"previous target: {sync.target_file}")
                print(f"current target: {target_file}")
                print()
                printed_any = True
                exit_code = 1
                continue

            if file_hash(repo_root, target_file) != sync.target_hash:
                print(f"=== {asset_id}/{locale}: target changed since sync ===")
                print(f"target: {target_file}")
                print()
                printed_any = True
                exit_code = 1

            if file_hash(repo_root, source_file) == sync.source_hash:
                continue

            print(f"=== {asset_id}/{locale} ===")
            print(f"baseline: {sync.source_commit} (synced {sync.synced_at})")
            print(f"source: {source_file}")
            print(f"target: {target_file}")
            print()
            print(source_diff(repo_root, source_file, sync.source_commit).rstrip())
            print()
            printed_any = True
            exit_code = 1

    if not printed_any:
        print("All tracked locales are up to date.")
    return exit_code


def mark_synced(repo_root: Path, asset_id: str, locale: str, target_file: str) -> None:
    asset = ASSETS[asset_id]
    source_file = asset["source"]
    if not is_source_committed(repo_root, source_file):
        raise SystemExit(f"{source_file} has uncommitted changes. Commit it before marking synced.")

    state = load_state()
    asset_state = state.setdefault("assets", {}).setdefault(
        asset_id,
        {"source_file": source_file, "locales": {}},
    )
    asset_state["source_file"] = source_file
    asset_state["locales"][locale] = {
        "target_file": target_file,
        "source_commit": run_git(repo_root, "rev-parse", "HEAD"),
        "source_hash": file_hash(repo_root, source_file),
        "target_hash": file_hash(repo_root, target_file),
        "synced_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    save_state(state)
    print(f"Marked {asset_id}/{locale} synced.")


def cmd_mark_synced(
    repo_root: Path, asset_filter: str | None, locale_filter: str | None
) -> int:
    asset_ids = [asset_filter] if asset_filter else list(ASSETS)
    for asset_id in asset_ids:
        locales = selected_locales(discover_locales(repo_root, ASSETS[asset_id]), locale_filter)
        for locale, target_file in locales.items():
            mark_synced(repo_root, asset_id, locale, target_file)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Show i18n source diffs since the last locale sync."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="Show sync status for all locale files")

    diff_parser = subparsers.add_parser("diff", help="Print source diffs for out-of-date locales")
    diff_parser.add_argument("--asset", choices=sorted(ASSETS))
    diff_parser.add_argument("--locale")
    diff_parser.add_argument(
        "--force",
        action="store_true",
        help="Allow inspection from a dirty worktree without recording a sync baseline.",
    )

    mark_parser = subparsers.add_parser("mark-synced", help="Mark the current translations as synced")
    mark_parser.add_argument("--asset", choices=sorted(ASSETS))
    mark_parser.add_argument("--locale")
    return parser


def main() -> int:
    try:
        repo_root = get_repo_root()
    except subprocess.CalledProcessError:
        print("Not inside a git repository.", file=sys.stderr)
        return 1

    args = build_parser().parse_args()
    if args.command == "status":
        return cmd_status(repo_root)
    if args.command == "diff":
        return cmd_diff(repo_root, args.asset, args.locale, force=args.force)
    if args.command == "mark-synced":
        return cmd_mark_synced(repo_root, args.asset, args.locale)
    raise AssertionError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
