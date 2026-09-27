# /// script
# requires-python = ">=3.11"
# dependencies = ["yt-dlp[default,curl-cffi]", "rich>=13.7"]
# ///
"""TikTok download stress test via yt-dlp.

Discovers public videos from profiles or a URL list, then downloads them with
optional concurrency and a live Rich dashboard. Records JSONL telemetry and
media into a sibling `tiktok-probes/` directory.
"""

import argparse
import json
import random
import secrets
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from yt_dlp.version import __version__ as yt_dlp_version

from probe_common import Reporter, duration, size
from probe_dashboard import Dashboard
from probe_scheduler import run_with_dashboard

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "tiktok-probes"


def start_heartbeat(reporter: Reporter, dashboard: Dashboard, interval: float, stall: float) -> tuple[threading.Event, threading.Thread]:
    stop = threading.Event()
    reported_stalls: set[int] = set()
    discovery_stall_reported = False

    def loop() -> None:
        nonlocal discovery_stall_reported
        while not stop.wait(interval):
            snapshot = dashboard.snapshot()
            if snapshot["discovery_active"]:
                message = (
                    f"Discovering @{snapshot['profile']} on page {snapshot['discovery_page'] or '?'}; "
                    f"posts {snapshot['discovery_items_current_profile']}/{snapshot['discovery_target_current_profile']}; "
                    f"{snapshot['completed']} downloads done, "
                    f"{snapshot['active_count']}/{snapshot['concurrency']} active; "
                    f"discovery idle {duration(snapshot['discovery_seconds_since_activity'])}"
                )
            else:
                message = (
                    f"Heartbeat: {snapshot['completed']}/{snapshot['planned']} done; "
                    f"active {snapshot['active_count']}/{snapshot['concurrency']}; "
                    f"OK {snapshot['successful']} / FAIL {snapshot['failed']}; "
                    f"media {size(snapshot['total_media_bytes'])}"
                )
            reporter.event("heartbeat", message=None if reporter.console.is_terminal else message, **snapshot)
            if snapshot["discovery_active"]:
                idle = snapshot["discovery_seconds_since_activity"]
                if idle >= stall and not discovery_stall_reported:
                    discovery_stall_reported = True
                    reporter.event(
                        "possible_stall",
                        message=f"Discovery @{snapshot['profile']}: no extractor activity for {duration(idle)}",
                        stage="discovery", profile=snapshot["profile"],
                        page=snapshot["discovery_page"], seconds_since_activity=idle,
                    )
                elif idle < stall:
                    discovery_stall_reported = False
            for item in snapshot["active"]:
                number = item["attempt"]
                if item["seconds_since_activity"] >= stall and number not in reported_stalls:
                    reported_stalls.add(number)
                    reporter.event(
                        "possible_stall",
                        message=f"#{number} no extractor/transfer activity for {duration(item['seconds_since_activity'])}",
                        attempt=number,
                        phase=item["phase"],
                        seconds_since_activity=item["seconds_since_activity"],
                    )
                elif item["seconds_since_activity"] < stall:
                    reported_stalls.discard(number)
            reported_stalls.intersection_update(item["attempt"] for item in snapshot["active"])

    thread = threading.Thread(target=loop, name="telemetry", daemon=True)
    thread.start()
    return stop, thread


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TikTok download probe with live discovery, concurrency and JSONL telemetry.")
    parser.add_argument("--profile", action="append", help="Public TikTok username; repeat (default: configured creator list)")
    parser.add_argument("--urls-file", type=Path, help="One public TikTok post URL per line; skip discovery")
    parser.add_argument("--per-profile", type=int, default=250)
    parser.add_argument("--max-videos", type=int, default=0, help="0 = until sources are exhausted or the error limit is reached")
    parser.add_argument("--concurrency", type=int, default=4, help="Concurrent post downloads (default 4, max 16)")
    parser.add_argument("--discovery-timeout", type=float, default=0.0, help="Optional soft discovery timeout in seconds; 0 = disabled")
    parser.add_argument("--verbose-console", action="store_true", help="Show starts and extra discovery milestones, in addition to completion summaries")
    parser.add_argument(
        "--max-consecutive-errors",
        type=int,
        default=3,
        help="Stop scheduling after this many consecutive completed download failures (default 3)",
    )
    parser.add_argument("--continue-on-error", action="store_true", help="Keep testing after failures regardless of the consecutive-error limit")
    parser.add_argument("--progress-interval", type=float, default=3.0, help="Seconds between per-download JSONL progress records")
    parser.add_argument("--heartbeat-interval", type=float, default=10.0, help="Seconds between full JSONL snapshots / non-TTY status lines")
    parser.add_argument("--stall-seconds", type=float, default=30.0, help="Warn after this much inactivity")
    parser.add_argument("--window", type=int, default=5, help="Successful downloads per rolling/baseline window")
    parser.add_argument("--yt-dlp-debug", action="store_true", help="Also print raw yt-dlp debug logs (already recorded in JSONL)")
    parser.add_argument("--seed", type=int, help="Shuffle seed for repeatable input ordering")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    if (
        args.per_profile < 1
        or args.max_videos < 0
        or args.discovery_timeout < 0
        or args.max_consecutive_errors < 1
        or not 1 <= args.concurrency <= 16
        or args.progress_interval <= 0
        or args.heartbeat_interval <= 0
        or args.stall_seconds <= 0
        or args.window < 2
    ):
        parser.error("Invalid limits, concurrency, or intervals")
    return args


def write_run_summary(
    run_dir: Path,
    log_path: Path,
    stop_reason: str,
    args: argparse.Namespace,
    reporter: Reporter,
    dashboard: Dashboard,
) -> None:
    dashboard.finish()
    snapshot = dashboard.snapshot()
    result = {key: value for key, value in snapshot.items() if key != "active"}
    success_rate = snapshot["success_rate_percent"]
    success_rate_label = f"{success_rate}%" if success_rate is not None else "—"
    reporter.event(
        "summary",
        message=(
            f"DONE: {stop_reason}  •  {snapshot['successful']}/{snapshot['completed']} OK "
            f"({success_rate_label}) • {size(snapshot['total_media_bytes'])} "
            f"• {duration(snapshot['wall_elapsed_seconds'])}  •  "
            f"{snapshot['videos_per_minute']}/min  •  "
            f"peak {snapshot['peak_active']}/{args.concurrency}, "
            f"avg {snapshot['average_active']} active"
        ),
        reason=stop_reason,
        **result,
    )

    summary_path = run_dir / "summary.json"
    summary_path.write_text(
        json.dumps({"reason": stop_reason, "yt_dlp_version": yt_dlp_version, **result}, indent=2) + "\n",
        encoding="utf-8",
    )
    reporter.event("results_path", message=f"Details: {log_path}  •  Summary: {summary_path}")
    reporter.close()


def main() -> int:
    args = parse_args()
    console = Console(highlight=False)
    rng = random.Random(args.seed)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.output / f"{run_id}-{secrets.token_hex(3)}"
    run_dir.mkdir(parents=True)
    log_path = run_dir / "results.jsonl"
    reporter = Reporter(log_path, console)
    dashboard = Dashboard(time.monotonic(), args.window, args.stall_seconds, console)
    stop_reason = "sources_exhausted"
    exit_code = 0
    reporter.event(
        "start",
        message=f"yt-dlp {yt_dlp_version}  •  concurrency {args.concurrency}  •  {run_dir}",
        yt_dlp_version=yt_dlp_version,
        options={key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
    )
    failure_policy = (
        "continue after all download failures"
        if args.continue_on_error
        else f"stop after {args.max_consecutive_errors} consecutive download failures"
    )
    reporter.event(
        "settings",
        message=(
            f"No inter-request delay; retries OFF; "
            f"{failure_policy}; diagnostics → JSONL"
        ),
    )
    stop_heartbeat, heartbeat = start_heartbeat(
        reporter,
        dashboard,
        args.heartbeat_interval,
        args.stall_seconds,
    )

    try:
        result = run_with_dashboard(
            args,
            console,
            reporter,
            dashboard,
            run_dir,
            rng,
        )
        stop_reason, exit_code = result.stop_reason, result.exit_code
    except KeyboardInterrupt:
        stop_reason, exit_code = "interrupted", 130
        reporter.event("interrupted", message="Interrupted by user.")
    except Exception as exc:
        stop_reason, exit_code = "unexpected_exception", 2
        reporter.event(
            "failure",
            message=f"Unexpected error: {type(exc).__name__}: {exc}",
            stage="runner",
            category="other",
            detail=repr(exc),
        )
    finally:
        stop_heartbeat.set()
        heartbeat.join(timeout=2)
        write_run_summary(
            run_dir,
            log_path,
            stop_reason,
            args,
            reporter,
            dashboard,
        )

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
