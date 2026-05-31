"""Command-line entry point: ``python -m au_flights_gtfs`` / ``au-flights-gtfs``."""

from __future__ import annotations

import argparse
import sys

from . import build_gtfs
from .config import Config

# Make the Windows console render Unicode output correctly
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main(argv: "list[str] | None" = None) -> int:
    p = argparse.ArgumentParser(
        prog="au-flights-gtfs",
        description="Build a GTFS feed of flights between VIC/NSW/ACT airports.",
    )
    p.add_argument("--api-key", help="AviationStack key (else $AVIATIONSTACK_KEY).")
    p.add_argument("--fetch-date", default=None, help="API query date YYYY-MM-DD.")
    p.add_argument("--service-date", default=None, help="GTFS calendar date YYYYMMDD.")
    p.add_argument("--output-dir", default=None, help="GTFS output folder.")
    p.add_argument("--zip-path", default=None, help="GTFS zip path.")
    p.add_argument("--no-api", action="store_true",
                   help="Skip the API and use the built-in fallback timetable.")
    args = p.parse_args(argv)

    kwargs: dict = {}
    if args.api_key:
        kwargs["api_key"] = args.api_key
    if args.fetch_date:
        kwargs["fetch_date"] = args.fetch_date
    if args.service_date:
        kwargs["service_date"] = args.service_date
        kwargs["service_id"] = f"SVC_{args.service_date}"
    if args.output_dir:
        kwargs["output_dir"] = args.output_dir
    if args.zip_path:
        kwargs["zip_path"] = args.zip_path
    if args.no_api:
        kwargs["use_api"] = False

    cfg = Config(**kwargs)

    banner = "VIC/NSW Flight GTFS Builder (AviationStack)"
    print("=" * len(banner)); print(banner); print("=" * len(banner))
    print(f"  Fetch date   : {cfg.fetch_date}")
    print(f"  Service date : {cfg.service_date}")
    print(f"  API enabled  : {cfg.use_api and bool(cfg.api_key)}\n")

    feed = build_gtfs(cfg, write=True)
    print()
    print(feed.summary())
    print(f"\n  Output dir   : {cfg.output_dir.resolve()}")
    print(f"  Zip file     : {cfg.zip_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
