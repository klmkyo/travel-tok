from __future__ import annotations

import re
import threading
import time
from collections import Counter
from datetime import datetime
from typing import Any

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from probe_common import Attempt, Outcome, duration, median, p95, rounded, size, speed

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
                size(
                    active["current_file_bytes"]
                    if active["phase"].startswith("gallery image")
                    else active["bytes"]
                ),
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
