from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from probe_common import Attempt, Outcome, Reporter, YtdlpLogger, duration, size
from probe_dashboard import Dashboard

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

        progress_label = f"image {image_index}/{len(images)}"
        reporter.event(
            "gallery_image_started",
            message=f"#{attempt.number} gallery {progress_label}: downloading",
            attempt=attempt.number,
            source=attempt.source,
            image_index=image_index,
            image_count=len(images),
            filename=destination.name,
        )
        attempt.activity(f"gallery {progress_label}")
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
                    }, reporter, args.progress_interval, progress_label=progress_label)
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
        }, reporter, args.progress_interval, progress_label=progress_label)
        reporter.event(
            "gallery_image_finished",
            message=(
                f"#{attempt.number} gallery {progress_label}: saved {size(downloaded)} "
                f"in {duration(elapsed)}"
            ),
            attempt=attempt.number,
            source=attempt.source,
            image_index=image_index,
            image_count=len(images),
            filename=destination.name,
            bytes=downloaded,
            elapsed_seconds=elapsed,
        )

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
