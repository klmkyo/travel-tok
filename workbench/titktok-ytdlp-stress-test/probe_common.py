from __future__ import annotations

import json
import re
import statistics
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.text import Text

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
            self.phase = description

    def hook(
        self,
        data: dict[str, Any],
        reporter: Reporter,
        interval: float,
        progress_label: str | None = None,
    ) -> None:
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
                self.phase = f"gallery {progress_label}" if progress_label else "transferring"
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
                        "progress_label": progress_label,
                    }
                elif now - self.reported_at >= interval:
                    self.reported_at = now
                    percent = (100 * downloaded / self.latest_total) if self.latest_total else None
                    event = {
                        "status": "downloading",
                        "bytes_so_far": self.completed_bytes + self.active_bytes,
                        "current_file_bytes": downloaded,
                        "current_file_percent": rounded(percent),
                        "speed_bytes_per_second": rounded(self.latest_speed),
                        "eta_seconds": self.latest_eta,
                        "elapsed_seconds": rounded(now - self.started),
                        "current_file_elapsed_seconds": rounded(data.get("elapsed")),
                        "progress_label": progress_label,
                    }

        if event is not None:
            status = event.pop("status")
            message = None
            if status == "downloading" and not reporter.console.is_terminal:
                message = (
                    f"#{self.number} "
                    f"{event['progress_label'] + ' ' if event['progress_label'] else ''}"
                    f"{size(event['current_file_bytes'] if event['progress_label'] else event['bytes_so_far'])} "
                    f"({event['current_file_percent'] if event['current_file_percent'] is not None else '?'}%) | "
                    f"{speed(event['speed_bytes_per_second'])} | "
                    f"elapsed {duration(event['current_file_elapsed_seconds'] if event['progress_label'] else event['elapsed_seconds'])}"
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
                "current_file_bytes": self.active_bytes,
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


class Outcome:
    attempt: Attempt
    metrics: dict[str, Any]
    error: str | None


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
