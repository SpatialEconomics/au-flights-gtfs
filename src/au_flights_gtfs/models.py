"""Lightweight data models shared across the package."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FlightSegment:
    """
    One physical point-to-point flight leg, normalised from any data source.

    Times are seconds since midnight on the service day, in local airport time
    (VIC/NSW/ACT are all UTC+10 in June, so no timezone conversion is needed).
    An arrival past midnight is represented with ``arr_sec >= 86400``.
    """

    dep_iata: str
    arr_iata: str
    dep_sec: int
    arr_sec: int
    airline_name: str = "Unknown Airline"
    airline_icao: str = ""
    airline_iata: str = ""
    flight_icao: str = ""
    flight_iata: str = ""
    flight_number: str = ""
    is_codeshare: bool = False

    @property
    def flight_code(self) -> str:
        """Best available flight identifier for grouping/trip naming."""
        return (
            self.flight_iata
            or self.flight_icao
            or f"{self.dep_iata}{self.arr_iata}{self.dep_sec}"
        )

    @property
    def agency_id(self) -> str:
        return self.airline_icao or self.airline_iata or "UNK"
