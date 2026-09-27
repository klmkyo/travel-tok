from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from probe_common import Attempt, Outcome, Reporter, YtdlpLogger, duration, size
from probe_dashboard import Dashboard


def _write_gallery_subtitles(
    ydl: YoutubeDL,
    info: dict[str, Any],
    video_id: str,
    run_dir: Path,
    attempt: Attempt,
    reporter: Reporter,
) -> list[dict[str, Any]]:
    subtitle_tracks = info.get("subtitles")
    if not isinstance(subtitle_tracks, dict):
        return []

    saved_subtitles: list[dict[str, Any]] = []
    for language, tracks in subtitle_tracks.items():
        if not isinstance(tracks, list) or not tracks:
            continue

        # TikTok orders subtitle formats from lowest to highest preference.
        track = tracks[-1]
        if not isinstance(track, dict):
            continue
        language_slug = re.sub(r"[^A-Za-z0-9._-]+", "_", str(language))
        extension = re.sub(r"[^A-Za-z0-9]+", "", str(track.get("ext") or "srt")) or "srt"
        filename = f"TikTok-{video_id}.{language_slug}.{extension}"
        destination = run_dir / filename

        try:
            if isinstance(track.get("data"), str):
                content = track["data"].encode("utf-8")
            elif isinstance(track.get("url"), str):
                with ydl.urlopen(track["url"]) as response:
                    content = response.read()
            else:
                continue
            destination.write_bytes(content)
        except Exception as exc:
            reporter.event(
                "subtitle_download_failed",
                message=f"#{attempt.number} couldn't save the {language} subtitle track: {exc}",
                attempt=attempt.number,
                language=language,
                filename=filename,
                detail=str(exc),
            )
            continue

        reporter.event(
            "subtitle_saved",
            message=f"#{attempt.number} saved {language} subtitles to {filename}",
            attempt=attempt.number,
            language=language,
            filename=filename,
            bytes=len(content),
        )
        saved_subtitles.append({
            "language": language,
            "filename": filename,
            "filesize": len(content),
        })

    return saved_subtitles


def _download_tiktok_gallery(
    ydl: YoutubeDL,
    attempt: Attempt,
    run_dir: Path,
    reporter: Reporter,
    args: argparse.Namespace,
) -> dict[str, Any] | None:
    """Download photo-mode assets when yt-dlp finds no video format."""
    video_id_match = re.search(r"/video/(\d+)", attempt.url)
    if video_id_match is None:
        return None

    video_id = video_id_match.group(1)
    tiktok_ie = ydl.get_info_extractor("TikTok")
    item, status = tiktok_ie._extract_web_data_and_status(attempt.url, video_id, fatal=False)
    if status != 0:
        return None

    image_post = item.get("imagePost")
    images = image_post.get("images") if isinstance(image_post, dict) else None
    if not isinstance(images, list) or not images:
        return None

    info = tiktok_ie._parse_aweme_video_web(item, attempt.url, video_id)
    info.update({
        "webpage_url": attempt.url,
        "extractor": "TikTok",
        "extractor_key": "TikTok",
    })
    gallery_images: list[dict[str, Any]] = []

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
            return None

        image_url = next((url for url in image_urls if isinstance(url, str) and url.startswith("https://")), None)
        if image_url is None:
            return None

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
        gallery_images.append({
            "index": image_index,
            "filename": destination.name,
            "filesize": downloaded,
        })

    info["gallery_images"] = gallery_images
    info["subtitle_files"] = _write_gallery_subtitles(
        ydl,
        info,
        video_id,
        run_dir,
        attempt,
        reporter,
    )
    info_path = run_dir / f"TikTok-{video_id}.info.json"
    info_path.write_text(
        json.dumps(ydl.sanitize_info(info), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return info


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
            "writeinfojson": True,
            "writesubtitles": True,
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
                gallery_info = _download_tiktok_gallery(ydl, attempt, run_dir, reporter, args)
                if gallery_info is None:
                    raise
                result = gallery_info
        if result is None or attempt.snapshot()["finished_files"] == 0:
            error = "No completed media transfer was reported"
    except DownloadError as exc:
        error = str(exc)
    except Exception as exc:
        error = f"Unexpected {type(exc).__name__}: {exc}"
    return Outcome(attempt, attempt.snapshot(), error)
