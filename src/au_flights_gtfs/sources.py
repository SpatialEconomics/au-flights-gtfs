"""Flight data sources: the AviationStack API and a built-in fallback timetable."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

from .airlines import fallback_airline_name
from .airports import REGION_IATA
from .config import Config
from .models import FlightSegment


def hhmm_to_sec(hhmm: str) -> int | None:
    """
    Convert a time-of-day string to seconds since midnight, or ``None``.

    Accepts both the API's ``"HH:MM"`` form and the compact ``"HHMM"`` form
    used by the built-in fallback timetable.
    """
    try:
        s = hhmm.strip()
        if ":" in s:
            h, m = s.split(":")
        else:                       # compact "HHMM"
            h, m = s[:-2], s[-2:]
        return int(h) * 3600 + int(m) * 60
    except Exception:
        return None


class AviationStackSource:
    """
    Fetches future-schedule departures for every region airport from
    AviationStack, caches each response to disk, dedupes codeshares, and
    returns a list of :class:`FlightSegment`.
    """

    def __init__(self, config: Config):
        self.cfg = config

    # ── Networking ─────────────────────────────────────────────────────────────

    def fetch_airport_departures(self, iata: str) -> list[dict] | None:
        """
        Return the raw departure records for ``iata`` on ``cfg.fetch_date``.

        Uses an on-disk cache (one JSON per airport) so re-runs do not spend
        API quota. Returns ``None`` on hard failure.
        """
        cfg = self.cfg
        cfg.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cfg.cache_dir / f"{iata}_dep_{cfg.fetch_date}.json"

        if cache_file.exists():
            try:
                with cache_file.open(encoding="utf-8") as fh:
                    return json.load(fh).get("data", [])
            except Exception:
                pass  # corrupt cache -> refetch

        tries = 0
        while tries <= cfg.max_429_tries:
            try:
                resp = requests.get(
                    cfg.api_url,
                    params={
                        "access_key": cfg.api_key,
                        "iataCode": iata,
                        "type": "departure",
                        "date": cfg.fetch_date,
                    },
                    timeout=60,
                )
            except requests.RequestException as exc:
                print(f"    network error: {exc}", file=sys.stderr)
                return None

            if resp.status_code == 429:
                tries += 1
                print(f"    429 rate-limited (try {tries}/{cfg.max_429_tries}); "
                      f"waiting {cfg.retry_429:.0f}s", flush=True)
                time.sleep(cfg.retry_429)
                continue

            if resp.status_code != 200:
                try:
                    err = resp.json().get("error", {})
                except Exception:
                    err = resp.text[:200]
                print(f"    HTTP {resp.status_code}: {err}", file=sys.stderr)
                return None

            try:
                payload = resp.json()
            except Exception:
                print(f"    bad JSON: {resp.text[:200]}", file=sys.stderr)
                return None

            if isinstance(payload, dict) and payload.get("error"):
                print(f"    API error: {payload['error']}", file=sys.stderr)
                return None

            with cache_file.open("w", encoding="utf-8") as fh:
                json.dump(payload, fh)
            return payload.get("data", [])

        print("    giving up after repeated 429s", file=sys.stderr)
        return None

    # ── Collection / normalisation ───────────────────────────────────────────

    def collect(self, airports: "list[str] | None" = None) -> list[FlightSegment]:
        """Query every region airport and return deduped intra-region segments."""
        cfg = self.cfg
        airports = airports or sorted(REGION_IATA)
        raw: list[dict] = []

        for i, iata in enumerate(airports, 1):
            from .airports import AIRPORTS
            name = AIRPORTS.get(iata, {}).get("name", iata)[:34]
            print(f"  [{i:2d}/{len(airports)}] {iata} {name:34s}", end="  ", flush=True)

            recs = self.fetch_airport_departures(iata)
            if recs is None:
                print("FAILED")
                continue
            recs = [r for r in recs if isinstance(r, dict)]
            intra = [
                r for r in recs
                if isinstance(r.get("arrival"), dict) and isinstance(r.get("departure"), dict)
                and (r["arrival"].get("iataCode") or "").upper() in REGION_IATA
                and (r["departure"].get("iataCode") or "").upper() == iata
            ]
            print(f"{len(recs):4d} dep -> {len(intra):3d} intra-region")
            raw.extend(intra)

            # polite delay only after a genuine network fetch (fresh cache file)
            cache_file = cfg.cache_dir / f"{iata}_dep_{cfg.fetch_date}.json"
            if i < len(airports) and cache_file.exists() \
                    and (time.time() - cache_file.stat().st_mtime) < 5:
                time.sleep(cfg.ok_delay)

        return self.normalise_and_dedupe(raw)

    @staticmethod
    def normalise_and_dedupe(records: list[dict]) -> list[FlightSegment]:
        """
        Convert raw AviationStack records to :class:`FlightSegment` and collapse
        codeshare duplicates (same route + departure time = one physical flight),
        preferring the operating carrier (record with no ``codeshared`` block).
        """
        by_phys: dict[tuple, FlightSegment] = {}
        for r in records:
            if not isinstance(r, dict):
                continue
            dep = r.get("departure") or {}
            arr = r.get("arrival") or {}
            if not isinstance(dep, dict) or not isinstance(arr, dict):
                continue

            dep_iata = (dep.get("iataCode") or "").upper()
            arr_iata = (arr.get("iataCode") or "").upper()
            dep_sec = hhmm_to_sec(dep.get("scheduledTime", ""))
            arr_sec = hhmm_to_sec(arr.get("scheduledTime", ""))

            if dep_iata not in REGION_IATA or arr_iata not in REGION_IATA:
                continue
            if dep_iata == arr_iata or dep_sec is None or arr_sec is None:
                continue
            if arr_sec < dep_sec:        # arrival past midnight
                arr_sec += 24 * 3600

            airline = r.get("airline") if isinstance(r.get("airline"), dict) else {}
            flight = r.get("flight") if isinstance(r.get("flight"), dict) else {}
            is_codeshare = bool(r.get("codeshared"))

            seg = FlightSegment(
                dep_iata=dep_iata,
                arr_iata=arr_iata,
                dep_sec=dep_sec,
                arr_sec=arr_sec,
                airline_name=(airline.get("name") or "").title() or "Unknown Airline",
                airline_icao=(airline.get("icaoCode") or "").upper(),
                airline_iata=(airline.get("iataCode") or "").upper(),
                flight_icao=(flight.get("icaoNumber") or "").upper(),
                flight_iata=(flight.get("iataNumber") or "").upper(),
                flight_number=flight.get("number") or "",
                is_codeshare=is_codeshare,
            )

            key = (dep_iata, arr_iata, dep_sec)
            if key not in by_phys:
                by_phys[key] = seg
            elif by_phys[key].is_codeshare and not is_codeshare:
                by_phys[key] = seg     # prefer the operating carrier

        return list(by_phys.values())


# ── Built-in fallback timetable ────────────────────────────────────────────────
# Used only when the API is disabled or returns nothing. Format:
#   (callsign, dep_iata, arr_iata, dep_hhmm, arr_hhmm)
# Same callsign on consecutive connecting legs => a multi-stop trip.

_FALLBACK = [
    ("QFA400", "MEL", "SYD", "0600", "0745"), ("QFA402", "MEL", "SYD", "0700", "0845"),
    ("QFA404", "MEL", "SYD", "0800", "0945"), ("QFA406", "MEL", "SYD", "0900", "1045"),
    ("QFA408", "MEL", "SYD", "1000", "1145"), ("QFA410", "MEL", "SYD", "1100", "1245"),
    ("QFA412", "MEL", "SYD", "1200", "1345"), ("QFA414", "MEL", "SYD", "1300", "1445"),
    ("QFA416", "MEL", "SYD", "1400", "1545"), ("QFA418", "MEL", "SYD", "1500", "1645"),
    ("QFA420", "MEL", "SYD", "1600", "1745"), ("QFA422", "MEL", "SYD", "1700", "1845"),
    ("QFA424", "MEL", "SYD", "1800", "1945"), ("QFA426", "MEL", "SYD", "1900", "2045"),
    ("QFA401", "SYD", "MEL", "0605", "0750"), ("QFA403", "SYD", "MEL", "0705", "0850"),
    ("QFA405", "SYD", "MEL", "0805", "0950"), ("QFA407", "SYD", "MEL", "0905", "1050"),
    ("QFA409", "SYD", "MEL", "1005", "1150"), ("QFA411", "SYD", "MEL", "1105", "1250"),
    ("QFA413", "SYD", "MEL", "1205", "1350"), ("QFA415", "SYD", "MEL", "1305", "1450"),
    ("QFA417", "SYD", "MEL", "1405", "1550"), ("QFA419", "SYD", "MEL", "1505", "1650"),
    ("QFA421", "SYD", "MEL", "1605", "1750"), ("QFA423", "SYD", "MEL", "1705", "1850"),
    ("QFA425", "SYD", "MEL", "1805", "1950"), ("QFA427", "SYD", "MEL", "1905", "2050"),
    ("JST201", "MEL", "SYD", "0615", "0800"), ("JST203", "MEL", "SYD", "1015", "1200"),
    ("JST205", "MEL", "SYD", "1415", "1600"), ("JST207", "MEL", "SYD", "1815", "2000"),
    ("JST202", "SYD", "MEL", "0620", "0805"), ("JST204", "SYD", "MEL", "1020", "1205"),
    ("JST206", "SYD", "MEL", "1420", "1605"), ("JST208", "SYD", "MEL", "1820", "2005"),
    ("VOZ851", "MEL", "SYD", "0610", "0755"), ("VOZ853", "MEL", "SYD", "0910", "1055"),
    ("VOZ855", "MEL", "SYD", "1210", "1355"), ("VOZ857", "MEL", "SYD", "1510", "1655"),
    ("VOZ859", "MEL", "SYD", "1810", "1955"),
    ("VOZ850", "SYD", "MEL", "0615", "0800"), ("VOZ852", "SYD", "MEL", "0915", "1100"),
    ("VOZ854", "SYD", "MEL", "1215", "1400"), ("VOZ856", "SYD", "MEL", "1515", "1700"),
    ("VOZ858", "SYD", "MEL", "1815", "2000"),
    ("QFA1400", "MEL", "CBR", "0650", "0800"), ("QFA1402", "MEL", "CBR", "1050", "1200"),
    ("QFA1404", "MEL", "CBR", "1450", "1600"), ("QFA1406", "MEL", "CBR", "1850", "2000"),
    ("QFA1401", "CBR", "MEL", "0700", "0810"), ("QFA1403", "CBR", "MEL", "1100", "1210"),
    ("QFA1405", "CBR", "MEL", "1500", "1610"), ("QFA1407", "CBR", "MEL", "1900", "2010"),
    ("QFA1500", "SYD", "CBR", "0630", "0720"), ("QFA1502", "SYD", "CBR", "0930", "1020"),
    ("QFA1504", "SYD", "CBR", "1300", "1350"), ("QFA1506", "SYD", "CBR", "1700", "1750"),
    ("QFA1501", "CBR", "SYD", "0640", "0730"), ("QFA1503", "CBR", "SYD", "0940", "1030"),
    ("QFA1505", "CBR", "SYD", "1310", "1400"), ("QFA1507", "CBR", "SYD", "1710", "1800"),
    ("RXA6100", "MEL", "ABX", "0700", "0755"), ("RXA6102", "MEL", "ABX", "1700", "1755"),
    ("RXA6101", "ABX", "MEL", "0810", "0905"), ("RXA6103", "ABX", "MEL", "1810", "1905"),
    ("RXA7100", "SYD", "WGA", "0700", "0815"), ("RXA7102", "SYD", "WGA", "1700", "1815"),
    ("RXA7101", "WGA", "SYD", "0840", "0955"), ("RXA7103", "WGA", "SYD", "1840", "1955"),
    ("QLK2800", "SYD", "DBO", "0705", "0825"), ("QLK2802", "SYD", "DBO", "1505", "1625"),
    ("QLK2801", "DBO", "SYD", "0850", "1010"), ("QLK2803", "DBO", "SYD", "1650", "1810"),
    ("QLK2300", "SYD", "CFS", "0650", "0800"), ("QLK2302", "SYD", "CFS", "1650", "1800"),
    ("QLK2301", "CFS", "SYD", "0820", "0930"), ("QLK2303", "CFS", "SYD", "1820", "1930"),
    ("JST740", "SYD", "NTL", "0800", "0840"), ("JST741", "NTL", "SYD", "0900", "0940"),
    # multi-stop (chained by callsign): SYD -> ABX -> WGA and return
    ("RXA8100", "SYD", "ABX", "0700", "0820"), ("RXA8100", "ABX", "WGA", "0840", "0915"),
    ("RXA8101", "WGA", "ABX", "1600", "1635"), ("RXA8101", "ABX", "SYD", "1655", "1815"),
]


def build_fallback_flights() -> list[FlightSegment]:
    """Return the built-in realistic timetable as :class:`FlightSegment` objects."""
    out: list[FlightSegment] = []
    for cs, dep, arr, dh, ah in _FALLBACK:
        out.append(FlightSegment(
            dep_iata=dep,
            arr_iata=arr,
            dep_sec=hhmm_to_sec(dh),
            arr_sec=hhmm_to_sec(ah),
            airline_name=fallback_airline_name(cs),
            airline_icao=cs[:3],
            flight_icao=cs,
            flight_number=cs[3:],
        ))
    return out
