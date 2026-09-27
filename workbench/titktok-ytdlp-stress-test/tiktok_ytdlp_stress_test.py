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
import concurrent.futures
import json
import queue
import random
import re
import secrets
import statistics
import sys
import threading
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
from yt_dlp.version import __version__ as yt_dlp_version

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "tiktok-probes"
DEFAULT_PROFILES = (
    "meme",
    "tworoamtheworld",
    "adventurers00",
    "theworldwithmymusic",
    "clidaexplores",
    "travelsruben",
    "gabriels.archive",
    "wawawandering__",
    "katiealysse",
    "aubruhhhh",
    "artetv1",
    "thesnapwalk",
    "beyondplaces",
    "laurschor",
    "matadornetwork",
    "maria.kaplon",
    "monagarbala",
    "heyitsmads11",
    "kseniainvienna",
    "kelseyinlondon",
    "chill_szn",
    "sralfilm",
    "norbertlepsik",
    "natalieinvienna",
    "maya_b__",
    "tobi.eulerrolle",
    "annaknowsvienna",
    "awayholics",
)


def classify_error(message: str) -> str:
    text = message.lower()
    if "no video formats found" in text:
        return "no_video_formats"
    if re.search(r"\b429\b", text) or "too many requests" in text or "rate limit" in text:
        return "rate_limited"
    if re.search(r"\b403\b", text) or "ip address is blocked" in text:
        return "access_denied"
    if "captcha" in text or "challenge" in text:
        return "challenge"
    if "login" in text or "sign in" in text:
        return "login_required"
    if re.search(r"\b404\b", text) or "not available" in text or "private" in text:
        return "unavailable"
    if "timed out" in text or "timeout" in text or "discovery of @" in text and "exceeded" in text:
        return "timeout"
    return "other"


def size(value: float | int | None) -> str:
    if value is None:
        return "?"
    for unit in ("B", "KiB", "MiB", "GiB"):
        if abs(value) < 1024 or unit == "GiB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return "?"


def speed(value: float | None) -> str:
    return f"{size(value)}/s" if value is not None else "?"


def duration(seconds: float | None) -> str:
    if seconds is None:
        return "?"
    if seconds < 60:
        return f"{seconds:.1f}s"
    return f"{int(seconds // 60)}m{int(seconds % 60):02d}s"


def rounded(value: float | None) -> float | None:
    return round(value, 3) if value is not None else None


def median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)]


class Reporter:
    def __init__(self, path: Path, console: Console) -> None:
        self.file = path.open("w", encoding="utf-8")
        self.console = console
        self.lock = threading.Lock()

    def event(self, name: str, *, message: str | None = None, **data: Any) -> None:
        now = datetime.now(timezone.utc)
        record = {
            "timestamp": now.isoformat(timespec="milliseconds"),
            "event": name,
            **data,
        }
        with self.lock:
            self.file.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            self.file.flush()
            if message is not None:
                label = Text(f"[{now.astimezone().strftime('%H:%M:%S')}] ", style="dim")
                style = (
                    "green" if name == "success" else
                    "red" if name in {"failure", "yt_dlp_error"} else
                    "yellow" if name in {"possible_stall", "possible_slowdown", "yt_dlp_warning"} else
                    None
                )
                label.append(message, style=style)
                self.console.print(label)

    def close(self) -> None:
        with self.lock:
            self.file.close()


class Attempt:
    def __init__(self, number: int, source: str, url: str) -> None:
        self.number = number
        self.source = source
        self.url = url
        self.started = time.monotonic()
        self.last_activity = self.started
        self.first_progress: float | None = None
        self.last_progress: float | None = None
        self.last_byte_change: float | None = None
        self.last_byte_count = 0
        self.reported_at = self.started
        self.completed_bytes = 0
        self.active_bytes = 0
        self.files = 0
        self.transfer_seconds = 0.0
        self.latest_speed: float | None = None
        self.latest_total: int | None = None
        self.latest_eta: float | None = None
        self.phase = "extracting metadata"
        self.lock = threading.Lock()

    def activity(self, description: str) -> None:
        with self.lock:
            self.last_activity = time.monotonic()
            if self.first_progress is None:
                self.phase = description

    def hook(self, data: dict[str, Any], reporter: Reporter, interval: float) -> None:
        status = data.get("status")
        if status not in {"downloading", "finished", "error"}:
            return

        now = time.monotonic()
        event: dict[str, Any] | None = None
        with self.lock:
            self.last_activity = now
            if status == "error":
                event = {"status": "error"}
            else:
                if self.first_progress is None:
                    self.first_progress = now
                self.last_progress = now
                downloaded = int(data.get("downloaded_bytes") or 0)
                if downloaded > self.last_byte_count:
                    self.last_byte_change = now
                    self.last_byte_count = downloaded
                self.active_bytes = downloaded
                self.latest_total = data.get("total_bytes") or data.get("total_bytes_estimate")
                self.latest_eta = data.get("eta")
                reported_speed = data.get("speed")
                if isinstance(reported_speed, (int, float)) and reported_speed > 0:
                    self.latest_speed = float(reported_speed)
                self.phase = "transferring"
                if status == "finished":
                    self.completed_bytes += downloaded or int(data.get("total_bytes") or 0)
                    self.active_bytes = 0
                    self.last_byte_count = 0
                    self.files += 1
                    self.transfer_seconds += float(data.get("elapsed") or 0)
                    self.phase = "finishing"
                    event = {
                        "status": "finished",
                        "part": self.files,
                        "part_bytes": downloaded,
                        "part_seconds": rounded(data.get("elapsed")),
                    }
                elif now - self.reported_at >= interval:
                    self.reported_at = now
                    percent = (100 * downloaded / self.latest_total) if self.latest_total else None
                    event = {
                        "status": "downloading",
                        "bytes_so_far": self.completed_bytes + self.active_bytes,
                        "current_file_percent": rounded(percent),
                        "speed_bytes_per_second": rounded(self.latest_speed),
                        "eta_seconds": self.latest_eta,
                        "elapsed_seconds": rounded(now - self.started),
                    }

        if event is not None:
            status = event.pop("status")
            message = None
            if status == "downloading" and not reporter.console.is_terminal:
                message = (
                    f"#{self.number} {size(event['bytes_so_far'])} "
                    f"({event['current_file_percent'] if event['current_file_percent'] is not None else '?'}%) | "
                    f"{speed(event['speed_bytes_per_second'])} | "
                    f"elapsed {duration(event['elapsed_seconds'])}"
                )
            reporter.event(f"transfer_{status}", message=message, attempt=self.number, **event)

    def snapshot(self) -> dict[str, Any]:
        now = time.monotonic()
        with self.lock:
            received = self.completed_bytes + self.active_bytes
            since_progress = now - (self.last_progress or self.started)
            return {
                "attempt": self.number,
                "source": self.source,
                "url": self.url,
                "phase": self.phase,
                "bytes": received,
                "elapsed_seconds": rounded(now - self.started),
                "seconds_to_first_progress": rounded(self.first_progress - self.started) if self.first_progress else None,
                "seconds_since_progress": rounded(since_progress),
                "seconds_since_activity": rounded(now - self.last_activity),
                "seconds_since_bytes": rounded(now - (self.last_byte_change or self.started)),
                "total_bytes": self.latest_total,
                "percent": rounded(100 * self.active_bytes / self.latest_total) if self.latest_total else None,
                "speed_bytes_per_second": rounded(self.latest_speed),
                "eta_seconds": self.latest_eta,
                "finished_files": self.files,
                "transfer_seconds": rounded(self.transfer_seconds) if self.files else None,
                "transfer_bytes_per_second": rounded(self.completed_bytes / self.transfer_seconds) if self.transfer_seconds > 0 else None,
            }


@dataclass
class Outcome:
    attempt: Attempt
    metrics: dict[str, Any]
    error: str | None


class Dashboard:
    def __init__(self, run_started: float, window: int, stall_seconds: float, console: Console) -> None:
        self.lock = threading.Lock()
        self.console = console
        self.run_started = run_started
        self.download_started: float | None = None
        self.window = window
        self.stall_seconds = stall_seconds
        self.phase = "starting"
        self.profile: str | None = None
        self.discovery_active = False
        self.discovery_started: float | None = None
        self.discovery_activity = run_started
        self.discovery_page: int | None = None
        self.discovery_items = 0
        self.discovery_target = 0
        self.discovery_detail = ""
        self.discovered = 0
        self.planned = 0
        self.launched = 0
        self.concurrency = 1
        self.active: dict[int, Attempt] = {}
        self.successful: list[dict[str, Any]] = []
        self.failed: list[dict[str, Any]] = []
        self.error_counts: Counter[str] = Counter()
        self.bytes = 0
        self.peak_active = 0
        self.active_time_area = 0.0
        self.active_time_last = run_started
        self.last_error: str | None = None

    def begin_discovery(self, profile: str, target: int) -> None:
        with self.lock:
            self.discovery_active = True
            self.phase = "streaming" if self.download_started is not None else "discovery"
            self.profile = profile
            self.discovery_started = time.monotonic()
            self.discovery_activity = self.discovery_started
            self.discovery_page = None
            self.discovery_items = 0
            self.discovery_target = target
            self.discovery_detail = "opening profile"

    def update_discovery(self, detail: str, page: int | None = None, items: int | None = None) -> None:
        with self.lock:
            self.discovery_activity = time.monotonic()
            self.discovery_detail = detail
            if page is not None:
                self.discovery_page = page
            if items is not None:
                self.discovery_items = max(self.discovery_items, items)

    def add_discovered(self, count: int) -> None:
        with self.lock:
            self.discovered += count

    def begin_downloads(self, planned: int | None, concurrency: int) -> None:
        with self.lock:
            self.phase = "streaming" if self.discovery_active else "downloads"
            if planned is not None:
                self.planned = planned
            self.concurrency = concurrency
            if self.download_started is None:
                self.download_started = time.monotonic()
                self.active_time_last = self.download_started

    def finish_discovery(self, planned: int | None = None) -> None:
        with self.lock:
            self.discovery_active = False
            if planned is not None:
                self.planned = planned
            if self.download_started is not None:
                self.phase = "downloads"

    def update_active_time(self) -> None:
        now = time.monotonic()
        self.active_time_area += len(self.active) * (now - self.active_time_last)
        self.active_time_last = now

    def launch(self, attempt: Attempt) -> None:
        with self.lock:
            self.update_active_time()
            self.active[attempt.number] = attempt
            self.launched += 1
            self.peak_active = max(self.peak_active, len(self.active))

    def complete(self, outcome: Outcome) -> None:
        with self.lock:
            self.update_active_time()
            self.active.pop(outcome.attempt.number, None)
            if outcome.error is None:
                self.successful.append(outcome.metrics)
                self.bytes += int(outcome.metrics["bytes"])
            else:
                category = classify_error(outcome.error)
                self.failed.append({**outcome.metrics, "category": category, "error": outcome.error})
                self.error_counts[category] += 1
                self.last_error = f"#{outcome.attempt.number}: {category}"

    def finish(self) -> None:
        with self.lock:
            self.update_active_time()
            self.discovery_active = False
            self.phase = "finished"

    def snapshot(self) -> dict[str, Any]:
        now = time.monotonic()
        with self.lock:
            active = list(self.active.values())
            successful = list(self.successful)
            failed = list(self.failed)
            done = len(successful) + len(failed)
            recent = successful[-self.window:]
            baseline = successful[:self.window]
            wall = max(now - (self.download_started or self.run_started), 0.001)
            recent_speeds = [v["transfer_bytes_per_second"] for v in recent if v["transfer_bytes_per_second"] is not None]
            baseline_speeds = [v["transfer_bytes_per_second"] for v in baseline if v["transfer_bytes_per_second"] is not None]
            recent_speed = median(recent_speeds)
            baseline_speed = median(baseline_speeds)
            recent_ttfp = median([v["seconds_to_first_progress"] for v in recent if v["seconds_to_first_progress"] is not None])
            baseline_ttfp = median([v["seconds_to_first_progress"] for v in baseline if v["seconds_to_first_progress"] is not None])
            speed_ratio = recent_speed / baseline_speed if baseline_speed and recent_speed and len(successful) >= self.window * 2 else None
            ttfp_ratio = recent_ttfp / baseline_ttfp if baseline_ttfp and recent_ttfp and len(successful) >= self.window * 2 else None
            details = {
                "phase": self.phase,
                "discovery_active": self.discovery_active,
                "profile": self.profile,
                "discovery_elapsed_seconds": rounded(now - self.discovery_started) if self.discovery_started is not None else None,
                "discovery_page": self.discovery_page,
                "discovery_items_current_profile": self.discovery_items,
                "discovery_target_current_profile": self.discovery_target,
                "discovery_detail": self.discovery_detail,
                "discovery_seconds_since_activity": rounded(now - self.discovery_activity),
                "discovered": self.discovered,
                "planned": self.planned,
                "launched": self.launched,
                "active_count": len(active),
                "concurrency": self.concurrency,
                "peak_active": self.peak_active,
                "average_active": rounded((self.active_time_area + (len(self.active) * (now - self.active_time_last))) / wall),
                "completed": done,
                "successful": len(successful),
                "failed": len(failed),
                "success_rate_percent": round(100 * len(successful) / done, 1) if done else None,
                "total_media_bytes": self.bytes,
                "wall_elapsed_seconds": rounded(wall),
                "wall_media_bytes_per_second": rounded(self.bytes / wall),
                "videos_per_minute": rounded(60 * len(successful) / wall),
                "median_elapsed_seconds": rounded(median([v["elapsed_seconds"] for v in successful])),
                "p95_elapsed_seconds": rounded(p95([v["elapsed_seconds"] for v in successful])),
                "median_first_progress_seconds": rounded(median([v["seconds_to_first_progress"] for v in successful if v["seconds_to_first_progress"] is not None])),
                "recent_window": len(recent),
                "recent_median_elapsed_seconds": rounded(median([v["elapsed_seconds"] for v in recent])),
                "recent_median_transfer_bytes_per_second": rounded(recent_speed),
                "baseline_median_transfer_bytes_per_second": rounded(baseline_speed),
                "transfer_speed_ratio_vs_baseline": rounded(speed_ratio),
                "first_progress_ratio_vs_baseline": rounded(ttfp_ratio),
                "possible_transfer_slowdown": speed_ratio is not None and speed_ratio <= 0.5,
                "possible_first_progress_slowdown": ttfp_ratio is not None and ttfp_ratio >= 2,
                "failure_categories": dict(self.error_counts),
                "last_error": self.last_error,
            }
        details["active"] = [attempt.snapshot() for attempt in active]
        details["active_received_bytes"] = sum(item["bytes"] for item in details["active"])
        details["active_transfer_bytes_per_second"] = rounded(sum(
            item["speed_bytes_per_second"] or 0
            for item in details["active"]
            if item["seconds_since_progress"] < 5
        ))
        details["possible_stalls"] = [item["attempt"] for item in details["active"] if item["seconds_since_activity"] >= self.stall_seconds]
        return details

    @property
    def console_width(self) -> int:
        return self.console.width

    @staticmethod
    def short_url(url: str) -> str:
        match = re.search(r"/@([^/?#]+)/video/(\d+)", url)
        return f"@{match.group(1)}/{match.group(2)}" if match else url

    def render(self) -> Panel:
        s = self.snapshot()
        elapsed = duration(time.monotonic() - self.run_started)
        if s["phase"] == "discovery":
            page = f"page {s['discovery_page']}" if s["discovery_page"] is not None else "page ?"
            lines = [
                Text(f"@{s['profile']}  •  {page}  •  elapsed {duration(s['discovery_elapsed_seconds'])}"),
                Text(f"Posts processed: {s['discovery_items_current_profile']}/{s['discovery_target_current_profile']}  •  finished profiles: {s['discovered']} URLs"),
                Text(f"Latest: {s['discovery_detail']}  •  last activity {duration(s['discovery_seconds_since_activity'])} ago"),
            ]
            if s["discovery_seconds_since_activity"] >= self.stall_seconds:
                lines.append(Text("No extractor activity recently; it may be waiting on a request.", style="yellow"))
            return Panel(Group(*lines), title=f"TikTok probe  •  {datetime.now().astimezone():%H:%M:%S}  •  discovering  •  {elapsed}", border_style="cyan")
        header = Table.grid(expand=True)
        header.add_column()
        progress = (
            f"Downloaded {s['completed']} so far  •  discovered {s['discovered']} unique URLs"
            if s["discovery_active"] else f"Done {s['completed']}/{s['planned']}"
        )
        header.add_row(
            f"{progress}  •  "
            f"OK {s['successful']} / FAIL {s['failed']}  •  "
            f"success {s['success_rate_percent'] if s['success_rate_percent'] is not None else '—'}%  •  "
            f"active {s['active_count']}/{s['concurrency']} (peak {s['peak_active']})"
        )
        if s["discovery_active"]:
            page = f"page {s['discovery_page']}" if s["discovery_page"] is not None else "page ?"
            header.add_row(
                f"Discovering @{s['profile']}  •  {page}  •  "
                f"posts {s['discovery_items_current_profile']}/{s['discovery_target_current_profile']}"
            )
        header.add_row(
            f"Saved {size(s['total_media_bytes'])}  •  "
            f"avg {speed(s['wall_media_bytes_per_second'])}  •  "
            f"live {speed(s['active_transfer_bytes_per_second'])}  •  "
            f"{s['videos_per_minute']}/min"
        )
        header.add_row(
            f"Last {s['recent_window']} median {duration(s['recent_median_elapsed_seconds'])}/video  •  "
            f"transfer {speed(s['recent_median_transfer_bytes_per_second'])}  •  "
            f"first progress {duration(s['median_first_progress_seconds'])}"
        )
        if s["transfer_speed_ratio_vs_baseline"] is not None:
            header.add_row(
                f"Vs first {self.window}: speed {s['transfer_speed_ratio_vs_baseline']:.2f}×  •  "
                f"first-progress time {s['first_progress_ratio_vs_baseline'] or 0:.2f}×"
            )
        narrow = self.console_width < 100
        table = Table(expand=True, show_header=True, box=None, padding=(0, 1))
        table.add_column("#", justify="right", no_wrap=True, width=4)
        table.add_column("Video / phase", ratio=3, overflow="ellipsis")
        table.add_column("Age", justify="right", width=8)
        table.add_column("Recv", justify="right", width=10)
        table.add_column("%", justify="right", width=5)
        table.add_column("Speed", justify="right", width=13)
        if not narrow:
            table.add_column("ETA", justify="right", width=8)
            table.add_column("Idle", justify="right", width=8)
        visible = sorted(s["active"], key=lambda item: item["attempt"])
        for active in visible[:8]:
            idle = active["seconds_since_activity"]
            phase = f"{active['phase']}  {self.short_url(active['url'])}"
            if narrow and idle >= self.stall_seconds:
                phase += f"  IDLE {duration(idle)}"
            cells = [
                str(active["attempt"]),
                Text(phase, style="yellow" if idle >= self.stall_seconds else None),
                duration(active["elapsed_seconds"]),
                size(active["bytes"]),
                f"{active['percent']:.0f}%" if active["percent"] is not None else "—",
                speed(active["speed_bytes_per_second"]),
            ]
            if not narrow:
                cells.append(duration(active["eta_seconds"]))
                cells.append(Text(duration(idle), style="yellow" if idle >= self.stall_seconds else None))
            table.add_row(*cells)
        if len(visible) > 8:
            table.add_row("…", f"{len(visible) - 8} more active downloads", *([""] * (4 + 2 * (not narrow))))
        note = ""
        if s["last_error"]:
            note += f"Last failure: {s['last_error']}.  "
        if s["possible_stalls"]:
            note += f"Possible stalls: {s['possible_stalls']}.  "
        if s["possible_transfer_slowdown"] or s["possible_first_progress_slowdown"]:
            note += "Possible slowdown vs initial window."
        renderables: list[Any] = [header]
        if s["active"]:
            renderables.append(table)
        renderables.append(Text(note or "Waiting for the next result...", style="yellow" if note else "dim"))
        return Panel(Group(*renderables), title=f"TikTok probe  •  {datetime.now().astimezone():%H:%M:%S}  •  {s['phase']}  •  {elapsed}", border_style="cyan")


class YtdlpLogger:
    def __init__(
        self,
        reporter: Reporter,
        dashboard: Dashboard,
        *,
        debug_stdout: bool,
        verbose_console: bool = False,
        discovery_timeout: float = 0.0,
        profile: str | None = None,
        attempt: Attempt | None = None,
    ) -> None:
        self.reporter = reporter
        self.dashboard = dashboard
        self.debug_stdout = debug_stdout
        self.verbose_console = verbose_console
        self.discovery_timeout = discovery_timeout
        self.discovery_started = time.monotonic()
        self.last_item_stdout = self.discovery_started
        self.profile = profile
        self.attempt = attempt
        self.last_page_stdout = 0.0

    def debug(self, message: str) -> None:
        if self.profile is not None and self.discovery_timeout:
            elapsed = time.monotonic() - self.discovery_started
            if elapsed >= self.discovery_timeout:
                raise TimeoutError(f"Discovery of @{self.profile} exceeded {self.discovery_timeout:g}s")
        message = re.sub(r"\x1b\[[0-9;]*m", "", message)
        self.reporter.event(
            "yt_dlp_debug",
            message=f"  yt-dlp: {message}" if self.debug_stdout else None,
            stage="discovery" if self.profile else "download",
            profile=self.profile,
            attempt=self.attempt.number if self.attempt else None,
            detail=message,
        )
        if self.profile is not None:
            match = re.search(r"Downloading page\s+(\d+)", message, re.IGNORECASE)
            item_match = re.search(r"Downloading (?:item|video)\s+(\d+)\s+of\s+", message, re.IGNORECASE)
            if item_match:
                count = int(item_match.group(1))
                self.dashboard.update_discovery(f"processing entry {count}", items=count)
                now = time.monotonic()
                show = (count == 1 or count % 25 == 0 or now - self.last_item_stdout >= 10)
                if show:
                    self.last_item_stdout = now
                self.reporter.event(
                    "discovery_item",
                    message=f"Discovery @{self.profile}: {count} post entries processed" if show and not self.debug_stdout else None,
                    profile=self.profile,
                    count=count,
                )
            if match:
                page = int(match.group(1))
                self.dashboard.update_discovery(f"fetching page {page}", page)
                now = time.monotonic()
                show = (self.last_page_stdout == 0 or now - self.last_page_stdout >= 5.0) and not self.debug_stdout
                if show:
                    self.last_page_stdout = now
                self.reporter.event(
                    "discovery_page",
                    message=f"Discovery @{self.profile}: fetching page {page}" if show else None,
                    profile=self.profile,
                    page=page,
                )
            elif not item_match and ("Downloading" in message or "Extracting" in message):
                self.dashboard.update_discovery(message.rsplit(": ", 1)[-1][-100:])
        elif self.attempt is not None:
            if "Downloading webpage" in message:
                self.attempt.activity("fetching webpage")
            elif "Downloading" in message and "video" not in message.lower():
                self.attempt.activity("resolving media")

    def warning(self, message: str) -> None:
        self.reporter.event("yt_dlp_warning", message=f"yt-dlp warning: {message}", detail=message,
                            profile=self.profile, attempt=self.attempt.number if self.attempt else None)

    def error(self, message: str) -> None:
        self.reporter.event("yt_dlp_error", message=f"yt-dlp error: {message}" if self.debug_stdout else None, detail=message,
                            profile=self.profile, attempt=self.attempt.number if self.attempt else None)


def discover_profile(
    profile: str, count: int, reporter: Reporter, dashboard: Dashboard,
    debug: bool, discovery_timeout: float,
    on_candidate: Callable[[str], None] | None = None,
) -> list[str]:
    with YoutubeDL({
        "quiet": True,
        "verbose": True,
        "extract_flat": "in_playlist",
        "lazy_playlist": True,
        "playlistend": count,
        "retries": 0,
        "extractor_retries": 0,
        "sleep_interval_requests": 0,
        "socket_timeout": 20,
        "logger": YtdlpLogger(
            reporter, dashboard, debug_stdout=debug,
            discovery_timeout=discovery_timeout, profile=profile,
        ),
    }) as ydl:
        info = ydl.extract_info(f"https://www.tiktok.com/@{profile}", download=False)

    if not isinstance(info, dict):
        raise ValueError(f"No playlist returned for @{profile}")
    urls: list[str] = []
    for item in info.get("entries") or []:
        if isinstance(item, dict):
            url = item.get("webpage_url") or item.get("url")
            if isinstance(url, str) and "/video/" in url:
                urls.append(url)
                if on_candidate is not None:
                    on_candidate(url)
    return urls


@dataclass
class DiscoveryFailure:
    profile: str
    detail: str
    category: str


def discover_profiles(
    profiles: list[str],
    count: int,
    reporter: Reporter,
    dashboard: Dashboard,
    debug: bool,
    discovery_timeout: float,
    on_candidate: Callable[[str, str], None],
) -> DiscoveryFailure | None:
    for raw_profile in profiles:
        profile = raw_profile.lstrip("@")
        dashboard.begin_discovery(profile, count)
        reporter.event(
            "discovery_started",
            message=f"Discovering up to {count} posts from @{profile}...",
            profile=profile,
            requested=count,
        )
        started = time.monotonic()

        def collect(url: str) -> None:
            on_candidate(profile, url)

        try:
            urls = discover_profile(
                profile,
                count,
                reporter,
                dashboard,
                debug,
                discovery_timeout,
                on_candidate=collect,
            )
        except (DownloadError, ValueError, TimeoutError) as exc:
            detail = str(exc)
            elapsed = rounded(time.monotonic() - started) or 0.0
            reporter.event(
                "failure",
                message=f"Discovery failed ({classify_error(detail)}): {detail}",
                stage="discovery",
                profile=profile,
                category=classify_error(detail),
                detail=detail,
                elapsed_seconds=elapsed,
            )
            return DiscoveryFailure(profile, detail, classify_error(detail))

        elapsed = rounded(time.monotonic() - started) or 0.0
        reporter.event(
            "discovery_finished",
            message=f"Found {len(urls)} posts from @{profile} in {duration(elapsed)}",
            profile=profile,
            count=len(urls),
            elapsed_seconds=elapsed,
        )
        if not urls:
            detail = f"No video URLs found for @{profile}"
            reporter.event(
                "failure",
                message=detail,
                stage="discovery",
                profile=profile,
                category="empty",
                detail=detail,
            )
            return DiscoveryFailure(profile, detail, "empty")
    return None


DISCOVERY_QUEUE_DONE = object()


def stream_profile_candidates(
    profiles: list[str],
    count: int,
    reporter: Reporter,
    dashboard: Dashboard,
    debug: bool,
    discovery_timeout: float,
    candidate_queue: queue.Queue[tuple[str, str] | object],
) -> DiscoveryFailure | None:
    seen_urls: set[str] = set()

    def add_candidate(profile: str, url: str) -> None:
        if url in seen_urls:
            return
        seen_urls.add(url)
        dashboard.add_discovered(1)
        candidate_queue.put((profile, url))

    try:
        return discover_profiles(
            profiles,
            count,
            reporter,
            dashboard,
            debug,
            discovery_timeout,
            on_candidate=add_candidate,
        )
    finally:
        candidate_queue.put(DISCOVERY_QUEUE_DONE)


def _download_tiktok_gallery(
    ydl: YoutubeDL,
    attempt: Attempt,
    run_dir: Path,
    reporter: Reporter,
    args: argparse.Namespace,
) -> bool:
    """Download photo-mode assets when yt-dlp finds no video format."""
    video_id_match = re.search(r"/video/(\d+)", attempt.url)
    if video_id_match is None:
        return False

    video_id = video_id_match.group(1)
    tiktok_ie = ydl.get_info_extractor("TikTok")
    item, status = tiktok_ie._extract_web_data_and_status(attempt.url, video_id, fatal=False)
    if status != 0:
        return False

    image_post = item.get("imagePost")
    images = image_post.get("images") if isinstance(image_post, dict) else None
    if not isinstance(images, list) or not images:
        return False

    reporter.event(
        "gallery_detected",
        message=f"Found a TikTok photo gallery with {len(images)} images; downloading in order.",
        attempt=attempt.number,
        source=attempt.source,
        url=attempt.url,
        image_count=len(images),
    )

    for image_index, image in enumerate(images, start=1):
        image_url_data = image.get("imageURL") if isinstance(image, dict) else None
        if not isinstance(image_url_data, dict):
            image_url_data = image.get("displayImage") if isinstance(image, dict) else None
        image_urls = image_url_data.get("urlList") if isinstance(image_url_data, dict) else None
        if not isinstance(image_urls, list) or not image_urls:
            return False

        image_url = next((url for url in image_urls if isinstance(url, str) and url.startswith("https://")), None)
        if image_url is None:
            return False

        extension_match = re.search(r"\.(jpe?g|png|webp)(?:$|\?)", image_url, re.IGNORECASE)
        extension = extension_match.group(1).lower() if extension_match else "jpg"
        if extension == "jpeg":
            extension = "jpg"
        destination = run_dir / f"TikTok-{video_id}-photo-{image_index:02d}.{extension}"
        temporary_path = destination.with_name(f"{destination.name}.part")

        attempt.activity(f"downloading gallery photo {image_index}/{len(images)}")
        started = time.monotonic()
        downloaded = 0
        try:
            with ydl.urlopen(image_url) as response, temporary_path.open("wb") as output:
                content_length = response.headers.get("Content-Length")
                total_bytes = int(content_length) if content_length and content_length.isdigit() else None
                while chunk := response.read(128 * 1024):
                    output.write(chunk)
                    downloaded += len(chunk)
                    elapsed = max(time.monotonic() - started, 0.001)
                    attempt.hook({
                        "status": "downloading",
                        "downloaded_bytes": downloaded,
                        "total_bytes": total_bytes,
                        "speed": downloaded / elapsed,
                        "elapsed": elapsed,
                    }, reporter, args.progress_interval)
            temporary_path.replace(destination)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

        elapsed = max(time.monotonic() - started, 0.001)
        attempt.hook({
            "status": "finished",
            "downloaded_bytes": downloaded,
            "total_bytes": downloaded,
            "speed": downloaded / elapsed,
            "elapsed": elapsed,
        }, reporter, args.progress_interval)

    return True


def download_one(
    attempt: Attempt,
    reporter: Reporter,
    dashboard: Dashboard,
    run_dir: Path,
    args: argparse.Namespace,
) -> Outcome:
    error: str | None = None
    try:
        with YoutubeDL({
            "quiet": True,
            "verbose": True,
            "noplaylist": True,
            "format": "best",
            "outtmpl": str(run_dir / "%(extractor_key)s-%(id)s.%(ext)s"),
            "progress_hooks": [lambda progress: attempt.hook(progress, reporter, args.progress_interval)],
            "logger": YtdlpLogger(
                reporter, dashboard, debug_stdout=args.yt_dlp_debug,
                verbose_console=args.verbose_console, attempt=attempt,
            ),
            "retries": 0,
            "fragment_retries": 0,
            "extractor_retries": 0,
            "file_access_retries": 0,
            "skip_unavailable_fragments": False,
            "concurrent_fragment_downloads": 1,
            "sleep_interval_requests": 0,
            "socket_timeout": 20,
        }) as ydl:
            try:
                result = ydl.extract_info(attempt.url, download=True)
            except DownloadError as exc:
                if "No video formats found" not in str(exc):
                    raise
                if not _download_tiktok_gallery(ydl, attempt, run_dir, reporter, args):
                    raise
                result = {"_type": "gallery"}
        if result is None or attempt.snapshot()["finished_files"] == 0:
            error = "No completed media transfer was reported"
    except DownloadError as exc:
        error = str(exc)
    except Exception as exc:
        error = f"Unexpected {type(exc).__name__}: {exc}"
    return Outcome(attempt, attempt.snapshot(), error)


@dataclass
class RunInputs:
    candidate_queue: queue.Queue[tuple[str, str] | object]
    streaming: bool
    profiles: list[str]
    planned: int | None
    stop_reason: str = "sources_exhausted"
    exit_code: int = 0


def prepare_run_inputs(
    args: argparse.Namespace,
    rng: random.Random,
    reporter: Reporter,
    dashboard: Dashboard,
) -> RunInputs:
    candidate_queue: queue.Queue[tuple[str, str] | object] = queue.Queue()
    if args.urls_file is None:
        profiles = args.profile or list(DEFAULT_PROFILES)
        rng.shuffle(profiles)
        dashboard.begin_downloads(None, args.concurrency)
        reporter.event(
            "queue_ready",
            message=(
                f"Starting downloads during profile discovery; choosing a random "
                f"available account, then a random post from that account; "
                f"concurrency {args.concurrency}."
            ),
            concurrency=args.concurrency,
        )
        return RunInputs(candidate_queue, True, profiles, None)

    urls = [
        line.strip()
        for line in args.urls_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    reporter.event(
        "discovery_finished",
        message=f"Loaded {len(urls)} URLs from {args.urls_file}",
        source="file",
        count=len(urls),
    )

    candidates = [("file", url) for url in urls]
    rng.shuffle(candidates)
    unique_candidates: list[tuple[str, str]] = []
    seen_urls: set[str] = set()
    for candidate in candidates:
        if candidate[1] in seen_urls:
            continue
        seen_urls.add(candidate[1])
        unique_candidates.append(candidate)

    dashboard.add_discovered(len(unique_candidates))
    planned = min(len(unique_candidates), args.max_videos) if args.max_videos else len(unique_candidates)
    if planned == 0:
        reporter.event(
            "failure",
            message="No video URLs to test.",
            stage="discovery",
            category="empty",
        )
        return RunInputs(candidate_queue, False, [], 0, "no_urls", 2)

    for candidate in unique_candidates[:planned]:
        candidate_queue.put(candidate)
    candidate_queue.put(DISCOVERY_QUEUE_DONE)
    dashboard.begin_downloads(planned, args.concurrency)
    reporter.event(
        "queue_ready",
        message=(
            f"Queued {len(unique_candidates)} unique URLs; testing up to {planned} "
            f"with concurrency {args.concurrency}."
        ),
        discovered=len(unique_candidates),
        planned=planned,
        concurrency=args.concurrency,
    )
    return RunInputs(candidate_queue, False, [], planned)


@dataclass
class SchedulerResult:
    discovery_failure: DiscoveryFailure | None
    launched: int
    stop_reason: str = "sources_exhausted"
    exit_code: int = 0


class DownloadScheduler:
    def __init__(
        self,
        args: argparse.Namespace,
        inputs: RunInputs,
        reporter: Reporter,
        dashboard: Dashboard,
        run_dir: Path,
        rng: random.Random,
    ) -> None:
        self.args = args
        self.inputs = inputs
        self.reporter = reporter
        self.dashboard = dashboard
        self.run_dir = run_dir
        self.rng = rng
        self.inflight: dict[concurrent.futures.Future[Outcome], Attempt] = {}
        self.seen_urls: set[str] = set()
        self.available_by_profile: dict[str, list[str]] = {}
        self.next_attempt = 0
        self.stop_scheduling = False
        self.queue_finished = False
        self.slowdown_reported = False
        self.consecutive_failures = 0
        self.discovery_failure: DiscoveryFailure | None = None
        self.stop_reason = "sources_exhausted"
        self.exit_code = 0
        self.producer_future: concurrent.futures.Future[DiscoveryFailure | None] | None = None

    def run(self) -> SchedulerResult:
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.args.concurrency) as download_executor, \
                concurrent.futures.ThreadPoolExecutor(max_workers=1) as discovery_executor:
            if self.inputs.streaming:
                self.producer_future = discovery_executor.submit(
                    stream_profile_candidates,
                    self.inputs.profiles,
                    self.args.per_profile,
                    self.reporter,
                    self.dashboard,
                    self.args.yt_dlp_debug,
                    self.args.discovery_timeout,
                    self.inputs.candidate_queue,
                )

            self._run_scheduler_loop(download_executor)

        return SchedulerResult(
            discovery_failure=self.discovery_failure,
            launched=self.next_attempt,
            stop_reason=self.stop_reason,
            exit_code=self.exit_code,
        )

    def _run_scheduler_loop(self, executor: concurrent.futures.ThreadPoolExecutor) -> None:
        while not self.queue_finished or self.inflight:
            self._read_and_schedule_candidate(executor)
            self._complete_ready_downloads()

    def _read_and_schedule_candidate(self, executor: concurrent.futures.ThreadPoolExecutor) -> None:
        has_download_slot = len(self.inflight) < self.args.concurrency
        if self.queue_finished or (not has_download_slot and not self.stop_scheduling):
            return

        if self.stop_scheduling:
            self._discard_queued_candidate()
            return

        self._collect_available_candidates()
        candidate = self._choose_available_candidate()
        if candidate is not None:
            self._start_download(candidate, executor)
            return

        if self.queue_finished:
            return

        try:
            queued_candidate = self.inputs.candidate_queue.get(timeout=0.1)
        except queue.Empty:
            return
        self._add_candidate_to_pool(queued_candidate)
        self._collect_available_candidates()

        candidate = self._choose_available_candidate()
        if candidate is not None:
            self._start_download(candidate, executor)

    def _discard_queued_candidate(self) -> None:
        try:
            candidate = self.inputs.candidate_queue.get(timeout=0.1)
        except queue.Empty:
            return

        if candidate is DISCOVERY_QUEUE_DONE:
            self._finish_discovery()

    def _collect_available_candidates(self) -> None:
        while True:
            try:
                candidate = self.inputs.candidate_queue.get_nowait()
            except queue.Empty:
                return
            self._add_candidate_to_pool(candidate)

    def _add_candidate_to_pool(self, candidate: tuple[str, str] | object) -> None:
        if candidate is DISCOVERY_QUEUE_DONE:
            self._finish_discovery()
            return
        if not isinstance(candidate, tuple):
            return

        profile, url = candidate
        self.available_by_profile.setdefault(profile, []).append(url)

    def _choose_available_candidate(self) -> tuple[str, str] | None:
        available_profiles = [
            profile for profile, urls in self.available_by_profile.items() if urls
        ]
        if not available_profiles:
            return None

        profile = self.rng.choice(available_profiles)
        urls = self.available_by_profile[profile]
        url = urls.pop(self.rng.randrange(len(urls)))
        if not urls:
            del self.available_by_profile[profile]
        return profile, url

    def _finish_discovery(self) -> None:
        self.queue_finished = True
        if not self.inputs.streaming:
            return

        if self.producer_future is None:
            raise RuntimeError("Streaming discovery finished before its producer started")

        self.discovery_failure = self.producer_future.result()
        discovered = self.dashboard.snapshot()["discovered"]
        planned = min(discovered, self.args.max_videos) if self.args.max_videos else discovered
        self.inputs.planned = planned
        self.dashboard.finish_discovery(planned)

    def _start_download(
        self,
        candidate: tuple[str, str],
        executor: concurrent.futures.ThreadPoolExecutor,
    ) -> None:
        source, url = candidate
        can_launch = not self.args.max_videos or self.next_attempt < self.args.max_videos
        if url in self.seen_urls or not can_launch:
            return

        self.seen_urls.add(url)
        self.next_attempt += 1
        attempt = Attempt(self.next_attempt, source, url)
        self.dashboard.launch(attempt)
        total_label = str(self.inputs.planned) if self.inputs.planned is not None else "?"
        self.reporter.event(
            "attempt_started",
            message=(
                f"#{self.next_attempt}/{total_label}  START {url}"
                if self.args.verbose_console or not self.reporter.console.is_terminal
                else None
            ),
            attempt=self.next_attempt,
            source=source,
            url=url,
            concurrency=self.args.concurrency,
        )
        future = executor.submit(
            download_one, attempt, self.reporter, self.dashboard, self.run_dir, self.args,
        )
        self.inflight[future] = attempt

    def _complete_ready_downloads(self) -> None:
        if not self.inflight:
            return

        completed, _ = concurrent.futures.wait(
            self.inflight,
            timeout=0.2,
            return_when=concurrent.futures.FIRST_COMPLETED,
        )

        finished: list[tuple[Attempt, Outcome]] = []
        for future in completed:
            attempt = self.inflight.pop(future)
            try:
                outcome = future.result()
            except Exception as exc:
                outcome = Outcome(
                    attempt,
                    attempt.snapshot(),
                    f"Unexpected worker {type(exc).__name__}: {exc}",
                )
            finished.append((attempt, outcome))

        finished.sort(
            key=lambda item: item[0].started + (item[1].metrics["elapsed_seconds"] or 0),
        )
        for attempt, outcome in finished:
            self._record_outcome(attempt, outcome)

    def _record_outcome(self, attempt: Attempt, outcome: Outcome) -> None:
        self.dashboard.complete(outcome)
        stats = self.dashboard.snapshot()
        if outcome.error is not None:
            self.consecutive_failures += 1
            self._report_failure(attempt, outcome)
            self._stop_after_failure()
        else:
            self.consecutive_failures = 0
            self._report_success(attempt, outcome, stats)
        self.reporter.event(
            "stats",
            **{key: value for key, value in stats.items() if key != "active"},
        )

    def _report_failure(self, attempt: Attempt, outcome: Outcome) -> None:
        category = classify_error(outcome.error or "")
        self.reporter.event(
            "failure",
            message=(
                f"#{attempt.number}  FAIL [{category}] after "
                f"{duration(outcome.metrics['elapsed_seconds'])}  •  {outcome.error}"
            ),
            stage="download",
            category=category,
            detail=outcome.error,
            **outcome.metrics,
        )

    def _stop_after_failure(self) -> None:
        if (
            self.args.continue_on_error
            or self.stop_scheduling
            or self.consecutive_failures < self.args.max_consecutive_errors
        ):
            return

        self.stop_scheduling = True
        self.stop_reason, self.exit_code = "consecutive_download_failures", 1
        self.reporter.event(
            "stop_scheduling",
            message=(
                f"Stopping new downloads after {self.consecutive_failures} consecutive failures; "
                "allowing discovery and "
                f"{len(self.inflight)} in-flight download(s) to finish."
            ),
            inflight=len(self.inflight),
            consecutive_failures=self.consecutive_failures,
            failure_limit=self.args.max_consecutive_errors,
        )

    def _report_success(
        self,
        attempt: Attempt,
        outcome: Outcome,
        stats: dict[str, Any],
    ) -> None:
        self.reporter.event(
            "success",
            message=(
                f"#{attempt.number} OK {size(outcome.metrics['bytes'])} in "
                f"{duration(outcome.metrics['elapsed_seconds'])}"
                f"  •  first {duration(outcome.metrics['seconds_to_first_progress'])}"
                f"  •  {speed(outcome.metrics['transfer_bytes_per_second'])}"
                f"  •  {stats['success_rate_percent']}%"
            ),
            **outcome.metrics,
        )
        self._report_slowdown_change(attempt, stats)

    def _report_slowdown_change(self, attempt: Attempt, stats: dict[str, Any]) -> None:
        slowdown_now = (
            stats["possible_transfer_slowdown"]
            or stats["possible_first_progress_slowdown"]
        )
        if slowdown_now == self.slowdown_reported:
            return

        self.slowdown_reported = slowdown_now
        self.reporter.event(
            "possible_slowdown" if slowdown_now else "slowdown_cleared",
            message=(
                f"{'Possible slowdown' if slowdown_now else 'Slowdown cleared'}: "
                f"last {self.args.window} transfer speed "
                f"{stats['transfer_speed_ratio_vs_baseline']}× baseline; "
                f"first-progress delay {stats['first_progress_ratio_vs_baseline']}×"
            ),
            attempt=attempt.number,
            transfer_speed_ratio=stats["transfer_speed_ratio_vs_baseline"],
            first_progress_ratio=stats["first_progress_ratio_vs_baseline"],
        )


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


def run_with_dashboard(
    args: argparse.Namespace,
    console: Console,
    reporter: Reporter,
    dashboard: Dashboard,
    run_dir: Path,
    rng: random.Random,
) -> SchedulerResult:
    with Live(
        get_renderable=dashboard.render,
        console=console,
        refresh_per_second=2,
        transient=True,
        auto_refresh=console.is_terminal,
    ):
        inputs = prepare_run_inputs(args, rng, reporter, dashboard)
        if inputs.exit_code != 0:
            dashboard.finish()
            return SchedulerResult(None, 0, inputs.stop_reason, inputs.exit_code)

        scheduler = DownloadScheduler(
            args,
            inputs,
            reporter,
            dashboard,
            run_dir,
            rng,
        )
        result = scheduler.run()
        result = finalize_scheduler_result(result, args, dashboard, reporter)
        dashboard.finish()
        return result


def finalize_scheduler_result(
    result: SchedulerResult,
    args: argparse.Namespace,
    dashboard: Dashboard,
    reporter: Reporter,
) -> SchedulerResult:
    if result.exit_code != 0:
        return result

    if result.discovery_failure is not None:
        result.stop_reason = "discovery_failure"
        result.exit_code = 2
    elif result.launched == 0:
        reporter.event(
            "failure",
            message="No video URLs to test.",
            stage="discovery",
            category="empty",
        )
        result.stop_reason = "no_urls"
        result.exit_code = 2
    elif result.stop_reason == "sources_exhausted":
        if args.max_videos and result.launched >= args.max_videos:
            result.stop_reason = "max_videos_reached"
        elif dashboard.failed:
            result.stop_reason = "completed_with_failures"
            result.exit_code = 1

    return result


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
