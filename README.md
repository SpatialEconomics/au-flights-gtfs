# au-flights-gtfs

Build a valid **GTFS feed** of scheduled flights between **Victorian, NSW and ACT**
airports, using real timetable data from the
[AviationStack](https://aviationstack.com) `flightsFuture` endpoint.

Each flight becomes a GTFS trip; airports are stops (`stop_id` = ICAO code),
airlines are agencies, and a straight-line shape connects the airports. Flights
with an intermediate stop are modelled as a single trip with multiple stops,
exactly like a multi-stop public-transport route.

## Why the date is June 10, 2026

The AviationStack plan used here **cannot** read historical dates (they return
`403 function_access_restricted`), and the `flightsFuture` endpoint only serves
dates roughly a week or more ahead. Australian airline timetables are
weekday-based, so the feed is built for **Wednesday, June 10, 2026** — the
nearest queryable date — and the GTFS calendar is stamped with that same date so
data and calendar match exactly. Both VIC and NSW are UTC+10 in June (no daylight
saving), so no timezone conversion is required. Change `fetch_date` /
`service_date` in `Config` to target a different day.

## Install

```bash
pip install -e .            # core package
pip install -e ".[notebook]"  # + pandas/matplotlib/jupyter for the notebook
```

## Configure the API key

The key is read from an environment variable — **never commit it**:

```bash
# Windows PowerShell
$env:AVIATIONSTACK_KEY = "your_key_here"

# macOS/Linux
export AVIATIONSTACK_KEY="your_key_here"
```

## Usage

### Python

```python
from au_flights_gtfs import Config, build_gtfs

cfg  = Config()                 # reads AVIATIONSTACK_KEY from the environment
feed = build_gtfs(cfg)          # fetch -> build -> write folder + zip
print(feed.summary())
```

### Command line

```bash
au-flights-gtfs                         # uses env key + defaults
au-flights-gtfs --service-date 20260610 # custom GTFS date
au-flights-gtfs --no-api                # built-in fallback timetable only
python -m au_flights_gtfs               # equivalent module form
```

### Notebook

See [`notebooks/build_au_flights_gtfs.ipynb`](notebooks/build_au_flights_gtfs.ipynb)
for a step-by-step walk-through: configure, fetch, build, inspect the tables with
pandas, plot the route network, and export the GTFS zip.

## Output

```
gtfs_flights/
├── agency.txt          airlines
├── stops.txt           airports (stop_id = ICAO, stop_code = IATA)
├── routes.txt          one route per airline + city pair (route_type 1100, Air)
├── trips.txt           one trip per flight
├── stop_times.txt      departure/arrival times (HH:MM:SS, local AEST)
├── shapes.txt          straight-line geometry between airports
├── calendar_dates.txt  single service date
└── feed_info.txt       feed metadata
gtfs_flights.zip        the above, zipped for import
```

## How it works

| Concept        | GTFS mapping                                                        |
|----------------|---------------------------------------------------------------------|
| Airline        | `agency`                                                            |
| Airport        | `stop` (`stop_id` = ICAO, `stop_code` = IATA)                       |
| Flight         | `trip` (+ `stop_times` for departure/arrival)                       |
| Airline + pair | `route` (`route_type = 1100`, the GTFS Extended "Air Service" code) |
| Flight path    | `shape` (straight line; multi-segment if the flight has a stop)     |
| Service day    | single date in `calendar_dates.txt`                                 |

Codeshares are collapsed to a single physical flight (same route + departure
time), preferring the operating carrier. Connecting legs that share a flight
number become one multi-stop trip.

The package falls back to a built-in realistic timetable (Qantas, QantasLink,
Jetstar, Virgin Australia, Rex) if the API is disabled or returns nothing, so it
always produces a usable feed.

## Validate

Import `gtfs_flights.zip` into a GTFS validator such as the
[Canonical GTFS Validator](https://github.com/MobilityData/gtfs-validator) or a
trip planner like OpenTripPlanner.

## License

MIT — see [LICENSE](LICENSE).
