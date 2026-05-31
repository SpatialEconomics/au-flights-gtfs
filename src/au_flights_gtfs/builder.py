"""Construct GTFS tables from a list of flight segments and write them out."""

from __future__ import annotations

import csv
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .airlines import airline_color, airline_url
from .airports import AIRPORTS
from .config import Config
from .models import FlightSegment

# GTFS field orderings
_FIELDS = {
    "agency.txt": ["agency_id", "agency_name", "agency_url", "agency_timezone", "agency_lang"],
    "stops.txt": ["stop_id", "stop_code", "stop_name", "stop_lat", "stop_lon"],
    "routes.txt": ["route_id", "agency_id", "route_short_name", "route_long_name",
                   "route_type", "route_color", "route_text_color"],
    "calendar_dates.txt": ["service_id", "date", "exception_type"],
    "trips.txt": ["route_id", "service_id", "trip_id", "trip_headsign",
                  "direction_id", "shape_id"],
    "stop_times.txt": ["trip_id", "arrival_time", "departure_time", "stop_id",
                       "stop_sequence", "pickup_type", "drop_off_type"],
    "shapes.txt": ["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"],
    "feed_info.txt": ["feed_publisher_name", "feed_publisher_url", "feed_lang",
                      "feed_start_date", "feed_end_date", "feed_version"],
}


def sec_to_gtfs(sec: int) -> str:
    """Seconds since service-day midnight -> GTFS ``HH:MM:SS`` (may exceed 24h)."""
    return f"{sec // 3600:02d}:{(sec % 3600) // 60:02d}:{sec % 60:02d}"


@dataclass
class GTFSFeed:
    """The built GTFS feed: one list of dict-rows per table, plus metadata."""

    tables: dict[str, list[dict]] = field(default_factory=dict)
    source_label: str = ""
    service_date: str = ""

    # ── Output ─────────────────────────────────────────────────────────────────

    def write(self, output_dir: Path) -> Path:
        """Write each table to a ``.txt`` file in ``output_dir``."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        for fname, fields in _FIELDS.items():
            rows = self.tables.get(fname, [])
            with (output_dir / fname).open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
                w.writeheader()
                w.writerows(rows)
        return output_dir

    def to_zip(self, zip_path: Path, output_dir: Path) -> Path:
        """Package the written ``.txt`` files in ``output_dir`` into a zip."""
        zip_path = Path(zip_path)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for txt in sorted(Path(output_dir).glob("*.txt")):
                zf.write(txt, txt.name)
        return zip_path

    # ── Reporting ────────────────────────────────────────────────────────────

    def counts(self) -> dict[str, int]:
        return {name.replace(".txt", ""): len(rows) for name, rows in self.tables.items()}

    def summary(self) -> str:
        c = self.counts()
        lines = [
            "-- GTFS feed summary --------------------------------------------",
            f"  Source       : {self.source_label}",
            f"  Service date : {self.service_date}",
            f"  Agencies     : {c.get('agency', 0)}",
            f"  Stops        : {c.get('stops', 0)}",
            f"  Routes       : {c.get('routes', 0)}",
            f"  Trips        : {c.get('trips', 0)}",
            f"  Stop times   : {c.get('stop_times', 0)}",
            f"  Shape points : {c.get('shapes', 0)}",
        ]
        return "\n".join(lines)


class GTFSBuilder:
    """Turns :class:`FlightSegment` objects into a :class:`GTFSFeed`."""

    def __init__(self, config: Config):
        self.cfg = config

    # ── Multi-leg chaining ─────────────────────────────────────────────────────

    def group_into_trips(self, flights: list[FlightSegment]) -> list[list[FlightSegment]]:
        """Chain segments sharing a flight code into connecting multi-stop trips."""
        gap_max = self.cfg.max_layover_minutes * 60
        by_flight: dict[str, list[FlightSegment]] = defaultdict(list)
        for f in flights:
            by_flight[f.flight_code].append(f)

        trips: list[list[FlightSegment]] = []
        for segs in by_flight.values():
            segs = sorted(segs, key=lambda x: x.dep_sec)
            used = [False] * len(segs)
            for i, seg in enumerate(segs):
                if used[i]:
                    continue
                chain = [seg]
                used[i] = True
                while True:
                    last = chain[-1]
                    extended = False
                    for j, cand in enumerate(segs):
                        if used[j]:
                            continue
                        gap = cand.dep_sec - last.arr_sec
                        if cand.dep_iata == last.arr_iata and 0 <= gap <= gap_max:
                            chain.append(cand)
                            used[j] = True
                            extended = True
                            break
                    if not extended:
                        break
                trips.append(chain)
        return trips

    # ── Shapes ─────────────────────────────────────────────────────────────────

    def _shape_points(self, stops: list[str]) -> list[tuple[float, float]]:
        n = self.cfg.shape_points_per_segment
        pts: list[tuple[float, float]] = []
        for i in range(len(stops) - 1):
            a, b = AIRPORTS[stops[i]], AIRPORTS[stops[i + 1]]
            for k in range(n):
                t = k / (n - 1)
                pts.append((a["lat"] + t * (b["lat"] - a["lat"]),
                            a["lon"] + t * (b["lon"] - a["lon"])))
        return pts

    # ── Build ──────────────────────────────────────────────────────────────────

    def build(self, flights: list[FlightSegment], source_label: str = "") -> GTFSFeed:
        cfg = self.cfg

        # keep only flights wholly within the catalogue with sane times
        flights = [
            f for f in flights
            if f.dep_iata in AIRPORTS and f.arr_iata in AIRPORTS
            and f.dep_sec is not None and f.arr_sec is not None
            and f.arr_sec > f.dep_sec
        ]

        trip_groups = self.group_into_trips(flights)

        agencies: dict[str, dict] = {}
        routes: dict[str, dict] = {}
        trip_rows: list[dict] = []
        stop_time_rows: list[dict] = []
        shape_rows: list[dict] = []
        shapes_seen: set[str] = set()
        used_stops: set[str] = set()

        for t_idx, segs in enumerate(trip_groups):
            if not segs:
                continue
            first, last = segs[0], segs[-1]
            agency_id = first.agency_id

            stops = [s.dep_iata for s in segs] + [last.arr_iata]
            if not all(s in AIRPORTS for s in stops):
                continue
            dep_secs = [s.dep_sec for s in segs]
            arr_secs = [s.arr_sec for s in segs]
            used_stops.update(stops)

            # agency
            if agency_id not in agencies:
                agencies[agency_id] = {
                    "agency_id": agency_id,
                    "agency_name": first.airline_name or f"Airline {agency_id}",
                    "agency_url": airline_url(agency_id),
                    "agency_timezone": "Australia/Sydney",
                    "agency_lang": "en",
                }

            # route (per agency + unordered city pair)
            pair = tuple(sorted([stops[0], stops[-1]]))
            route_id = f"{agency_id}_{pair[0]}_{pair[1]}"
            if route_id not in routes:
                color, txt = airline_color(agency_id)
                routes[route_id] = {
                    "route_id": route_id,
                    "agency_id": agency_id,
                    "route_short_name": f"{pair[0]}-{pair[1]}",
                    "route_long_name": f"{AIRPORTS[pair[0]]['name']} - {AIRPORTS[pair[1]]['name']}",
                    "route_type": "1100",       # GTFS Extended: Air Service
                    "route_color": color,
                    "route_text_color": txt,
                }

            # shape
            shape_id = "shp_" + "_".join(stops)
            if shape_id not in shapes_seen:
                shapes_seen.add(shape_id)
                for seq, (lat, lon) in enumerate(self._shape_points(stops)):
                    shape_rows.append({
                        "shape_id": shape_id,
                        "shape_pt_lat": f"{lat:.6f}",
                        "shape_pt_lon": f"{lon:.6f}",
                        "shape_pt_sequence": str(seq),
                    })

            # trip
            flightcode = first.flight_iata or first.flight_icao or f"T{t_idx}"
            trip_id = f"T{t_idx:05d}_{flightcode}"
            dest = AIRPORTS[stops[-1]]
            trip_rows.append({
                "route_id": route_id,
                "service_id": cfg.service_id,
                "trip_id": trip_id,
                "trip_headsign": f"{stops[-1]} {dest['name'].split(' (')[0]}",
                "direction_id": "0",
                "shape_id": shape_id,
            })

            # stop_times
            n = len(stops)
            for sq, stop in enumerate(stops):
                if sq == 0:
                    arr_t = dep_t = dep_secs[0]; pu, do = "0", "1"
                elif sq == n - 1:
                    arr_t = dep_t = arr_secs[-1]; pu, do = "1", "0"
                else:
                    arr_t = arr_secs[sq - 1]; dep_t = dep_secs[sq]; pu, do = "0", "0"
                stop_time_rows.append({
                    "trip_id": trip_id,
                    "arrival_time": sec_to_gtfs(arr_t),
                    "departure_time": sec_to_gtfs(dep_t),
                    "stop_id": AIRPORTS[stop]["icao"],
                    "stop_sequence": str(sq + 1),
                    "pickup_type": pu,
                    "drop_off_type": do,
                })

        stop_rows = [
            {"stop_id": v["icao"], "stop_code": k, "stop_name": v["name"],
             "stop_lat": v["lat"], "stop_lon": v["lon"]}
            for k, v in AIRPORTS.items() if k in used_stops
        ]

        tables = {
            "agency.txt": list(agencies.values()),
            "stops.txt": stop_rows,
            "routes.txt": list(routes.values()),
            "calendar_dates.txt": [
                {"service_id": cfg.service_id, "date": cfg.service_date, "exception_type": "1"}
            ],
            "trips.txt": trip_rows,
            "stop_times.txt": stop_time_rows,
            "shapes.txt": shape_rows,
            "feed_info.txt": [{
                "feed_publisher_name": "VIC/NSW Flights GTFS",
                "feed_publisher_url": "https://www.aviationstack.com",
                "feed_lang": "en",
                "feed_start_date": cfg.service_date,
                "feed_end_date": cfg.service_date,
                "feed_version": "1.0",
            }],
        }

        return GTFSFeed(tables=tables, source_label=source_label, service_date=cfg.service_date)
