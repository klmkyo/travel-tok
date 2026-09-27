from __future__ import annotations

import queue
import time
from collections.abc import Callable
from dataclasses import dataclass

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from probe_common import (
    Reporter,
    YtdlpLogger,
    classify_error,
    duration,
    rounded,
)
from probe_dashboard import Dashboard

DISCOVERY_QUEUE_DONE = object()

@dataclass
class DiscoveryFailure:
    profile: str
    detail: str
    category: str


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
