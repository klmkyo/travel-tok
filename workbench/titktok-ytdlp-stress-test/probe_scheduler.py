from __future__ import annotations

import argparse
import concurrent.futures
import queue
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.live import Live

from probe_common import (
    Attempt,
    DEFAULT_PROFILES,
    Outcome,
    Reporter,
    classify_error,
    duration,
    size,
    speed,
)
from probe_dashboard import Dashboard
from probe_discovery import (
    DISCOVERY_QUEUE_DONE,
    DiscoveryFailure,
    stream_profile_candidates,
)
from probe_downloads import download_one

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
