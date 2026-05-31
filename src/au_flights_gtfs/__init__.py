"""
au_flights_gtfs
===============
Build a GTFS feed of scheduled flights between Victorian, NSW (and ACT)
airports from AviationStack future-schedule data.

Quick start
-----------
    from au_flights_gtfs import Config, build_gtfs

    cfg  = Config(api_key="YOUR_AVIATIONSTACK_KEY")
    feed = build_gtfs(cfg)          # fetch + build + write folder + zip
    print(feed.summary())

See the notebook in ``notebooks/build_au_flights_gtfs.ipynb`` for an
end-to-end, step-by-step example.
"""

from __future__ import annotations

from .config import Config
from .models import FlightSegment
from .airports import AIRPORTS, REGION_IATA, airport
from .sources import AviationStackSource, build_fallback_flights
from .builder import GTFSBuilder, GTFSFeed

__all__ = [
    "Config",
    "FlightSegment",
    "AIRPORTS",
    "REGION_IATA",
    "airport",
    "AviationStackSource",
    "build_fallback_flights",
    "GTFSBuilder",
    "GTFSFeed",
    "build_gtfs",
]

__version__ = "0.1.0"


def build_gtfs(config: "Config | None" = None, *, write: bool = True) -> "GTFSFeed":
    """
    End-to-end convenience pipeline:

      1. Fetch real schedules from AviationStack (falls back to a built-in
         timetable if the API is disabled or returns nothing).
      2. Build the GTFS tables.
      3. Optionally write the ``.txt`` files and a ``.zip`` archive.

    Parameters
    ----------
    config : Config, optional
        Configuration. If omitted, a default ``Config`` is created (which
        reads the API key from the ``AVIATIONSTACK_KEY`` environment variable).
    write : bool
        If True (default), write the GTFS folder and zip to disk.

    Returns
    -------
    GTFSFeed
        The built feed (tables + counts), already written to disk if ``write``.
    """
    config = config or Config()

    flights = []
    source_label = "Built-in fallback timetable"

    if config.use_api and config.api_key:
        source = AviationStackSource(config)
        flights = source.collect()
        if flights:
            source_label = f"AviationStack flightsFuture (real schedule for {config.fetch_date})"

    if not flights:
        flights = build_fallback_flights()
        source_label = "Built-in fallback timetable"

    feed = GTFSBuilder(config).build(flights, source_label=source_label)

    if write:
        feed.write(config.output_dir)
        feed.to_zip(config.zip_path, config.output_dir)

    return feed
