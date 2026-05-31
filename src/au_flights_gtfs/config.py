"""Configuration for the GTFS flight-feed builder."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    """
    All tunable settings for fetching and building the feed.

    Date handling
    -------------
    AviationStack's ``flightsFuture`` endpoint only serves dates roughly a week
    or more into the future, and historical dates require a paid plan. Australian
    airline timetables are weekday-based, so we fetch a valid future Wednesday and
    stamp the GTFS calendar with the same date.

      * ``fetch_date``   - date queried from the API (``YYYY-MM-DD``)
      * ``service_date`` - date written into the GTFS calendar (``YYYYMMDD``)

    The API key is read from the ``AVIATIONSTACK_KEY`` environment variable by
    default; never hard-code it into committed source.
    """

    # ── Credentials ───────────────────────────────────────────────────────────
    api_key: str = field(default_factory=lambda: os.getenv("AVIATIONSTACK_KEY", ""))

    # ── Behaviour ─────────────────────────────────────────────────────────────
    use_api: bool = True

    # ── Dates ─────────────────────────────────────────────────────────────────
    fetch_date: str = "2026-06-10"        # queried from API (a valid Wednesday)
    service_date: str = "20260610"        # stamped into GTFS calendar_dates.txt
    service_id: str = "SVC_20260610"

    # ── API ───────────────────────────────────────────────────────────────────
    api_url: str = "http://api.aviationstack.com/v1/flightsFuture"

    # ── Paths ─────────────────────────────────────────────────────────────────
    cache_dir: Path = Path("aviationstack_cache")
    output_dir: Path = Path("gtfs_flights")
    zip_path: Path = Path("gtfs_flights.zip")

    # ── Rate-limit handling (the free plan is aggressive) ──────────────────────
    ok_delay: float = 30.0                # seconds between successful API calls
    retry_429: float = 60.0               # seconds to wait after a 429
    max_429_tries: int = 4                # give up on an airport after this many 429s

    # ── Trip/shape construction ────────────────────────────────────────────────
    max_layover_minutes: int = 90         # max gap to chain multi-leg flights
    shape_points_per_segment: int = 20    # interpolated points per straight leg

    def __post_init__(self) -> None:
        self.cache_dir = Path(self.cache_dir)
        self.output_dir = Path(self.output_dir)
        self.zip_path = Path(self.zip_path)
