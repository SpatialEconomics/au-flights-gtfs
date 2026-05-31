"""Airline metadata: website URLs and brand colours, keyed by ICAO airline code."""

from __future__ import annotations

AIRLINE_URLS: dict[str, str] = {
    "QFA": "https://www.qantas.com",
    "QLK": "https://www.qantas.com/au/en/qantaslink.html",
    "JST": "https://www.jetstar.com",
    "VOZ": "https://www.virginaustralia.com",
    "RXA": "https://www.rex.com.au",
    "FD":  "https://www.flypelican.com.au",
}

#: (route_color, route_text_color) hex pairs, without leading '#'.
AIRLINE_COLORS: dict[str, tuple[str, str]] = {
    "QFA": ("EE0000", "FFFFFF"),
    "QLK": ("EE0000", "FFFFFF"),
    "JST": ("FF6600", "FFFFFF"),
    "VOZ": ("C8002D", "FFFFFF"),
    "RXA": ("005DAA", "FFFFFF"),
}

#: Friendly names for the built-in fallback timetable's callsign prefixes.
FALLBACK_AIRLINE_NAMES: dict[str, str] = {
    "QFA": "Qantas",
    "QLK": "QantasLink",
    "JST": "Jetstar",
    "VOZ": "Virgin Australia",
    "RXA": "Rex Airlines",
}

DEFAULT_URL = "https://www.aviationstack.com"
DEFAULT_COLOR = ("003087", "FFFFFF")


def airline_url(icao: str) -> str:
    return AIRLINE_URLS.get((icao or "").upper(), DEFAULT_URL)


def airline_color(icao: str) -> tuple[str, str]:
    return AIRLINE_COLORS.get((icao or "").upper(), DEFAULT_COLOR)


def fallback_airline_name(callsign: str) -> str:
    return FALLBACK_AIRLINE_NAMES.get(callsign[:3], f"Airline {callsign[:3]}")
