"""Airport catalogue for Victoria, New South Wales and the ACT.

Keyed by IATA code (AviationStack's ``flightsFuture`` uses IATA). The ICAO code
is kept because it is used as the GTFS ``stop_id``. Coordinates are approximate
terminal/runway centres.
"""

from __future__ import annotations

AIRPORTS: dict[str, dict] = {
    # ── Victoria ──────────────────────────────────────────────────────────────
    "MEL": {"icao": "YMML", "name": "Melbourne Airport (Tullamarine)", "lat": -37.6733, "lon": 144.8433, "state": "VIC"},
    "AVV": {"icao": "YMAV", "name": "Avalon Airport",                  "lat": -38.0394, "lon": 144.4692, "state": "VIC"},
    "MQL": {"icao": "YMBA", "name": "Mildura Airport",                 "lat": -34.2292, "lon": 142.0861, "state": "VIC"},
    "ABX": {"icao": "YMAY", "name": "Albury Airport",                  "lat": -36.0678, "lon": 146.9581, "state": "VIC"},
    "HSM": {"icao": "YHSM", "name": "Horsham Airport",                 "lat": -36.6697, "lon": 142.1731, "state": "VIC"},
    "SWH": {"icao": "YSWH", "name": "Swan Hill Airport",               "lat": -35.3758, "lon": 143.5333, "state": "VIC"},
    "PTJ": {"icao": "YPOD", "name": "Portland Airport",                "lat": -38.3181, "lon": 141.4708, "state": "VIC"},
    # ── New South Wales ───────────────────────────────────────────────────────
    "SYD": {"icao": "YSSY", "name": "Sydney Kingsford Smith Airport",  "lat": -33.9461, "lon": 151.1772, "state": "NSW"},
    "NTL": {"icao": "YWLM", "name": "Newcastle Airport (Williamtown)", "lat": -32.7950, "lon": 151.8342, "state": "NSW"},
    "WGA": {"icao": "YSWG", "name": "Wagga Wagga Airport",             "lat": -35.1653, "lon": 147.4658, "state": "NSW"},
    "GFF": {"icao": "YGTH", "name": "Griffith Airport",                "lat": -34.2508, "lon": 146.0678, "state": "NSW"},
    "DBO": {"icao": "YDBO", "name": "Dubbo City Regional Airport",     "lat": -32.2167, "lon": 148.5747, "state": "NSW"},
    "BHQ": {"icao": "YBHI", "name": "Broken Hill Airport",            "lat": -31.9942, "lon": 141.4722, "state": "NSW"},
    "MIM": {"icao": "YMER", "name": "Merimbula Airport",               "lat": -36.9086, "lon": 149.9011, "state": "NSW"},
    "CFS": {"icao": "YCFS", "name": "Coffs Harbour Airport",           "lat": -30.3206, "lon": 153.1158, "state": "NSW"},
    "PQQ": {"icao": "YPMQ", "name": "Port Macquarie Airport",         "lat": -31.4358, "lon": 152.8636, "state": "NSW"},
    "TMW": {"icao": "YSTW", "name": "Tamworth Airport",                "lat": -31.0839, "lon": 150.8469, "state": "NSW"},
    "ARM": {"icao": "YANB", "name": "Armidale Airport",               "lat": -30.5281, "lon": 151.6172, "state": "NSW"},
    "BHS": {"icao": "YBTH", "name": "Bathurst Airport",                "lat": -33.4094, "lon": 149.6517, "state": "NSW"},
    "DGE": {"icao": "YWMD", "name": "Mudgee Airport",                  "lat": -32.5625, "lon": 149.6106, "state": "NSW"},
    "TRO": {"icao": "YTMR", "name": "Taree Airport",                   "lat": -31.8886, "lon": 152.5144, "state": "NSW"},
    "NRA": {"icao": "YNAR", "name": "Narrandera Airport",             "lat": -34.7022, "lon": 146.5119, "state": "NSW"},
    "OAG": {"icao": "YORG", "name": "Orange Airport",                  "lat": -33.0381, "lon": 148.9528, "state": "NSW"},
    "IVR": {"icao": "YIVO", "name": "Inverell Airport",               "lat": -29.8883, "lon": 151.1439, "state": "NSW"},
    "WOL": {"icao": "YSHL", "name": "Shellharbour Airport (Wollongong)","lat": -34.5614, "lon": 150.7889, "state": "NSW"},
    "MRZ": {"icao": "YMOR", "name": "Moree Airport",                   "lat": -29.4989, "lon": 149.8450, "state": "NSW"},
    "NAA": {"icao": "YNBR", "name": "Narrabri Airport",               "lat": -30.3192, "lon": 149.8267, "state": "NSW"},
    "LDH": {"icao": "YLHI", "name": "Lord Howe Island Airport",        "lat": -31.5383, "lon": 159.0769, "state": "NSW"},
    "COJ": {"icao": "YCOM", "name": "Coonamble Airport",               "lat": -30.9831, "lon": 148.3764, "state": "NSW"},
    "BNK": {"icao": "YBNA", "name": "Ballina Byron Gateway Airport",   "lat": -28.8339, "lon": 153.5622, "state": "NSW"},
    # ── ACT ────────────────────────────────────────────────────────────────────
    "CBR": {"icao": "YSCB", "name": "Canberra Airport",                "lat": -35.3069, "lon": 149.1950, "state": "ACT"},
}

#: Set of all IATA codes in the region — used to filter flights to intra-region.
REGION_IATA: set[str] = set(AIRPORTS)


def airport(iata: str) -> dict | None:
    """Return the airport record for an IATA code, or ``None`` if unknown."""
    return AIRPORTS.get((iata or "").upper())
