---
name: singapore-lta
description: >
  Query Singapore's Land Transport Authority (LTA) DataMall API for transportation
  and traffic data. Use this skill whenever the user wants to access real-time or
  static transport data for Singapore — bus arrivals, bus routes and stops, taxi
  availability, car park availability, traffic incidents, traffic speed bands,
  estimated travel times, train service alerts, station crowd density, traffic
  images, road works, flood alerts, EV charging points, bicycle parking, or
  passenger volume data. Also trigger when the user mentions "LTA DataMall", "MyTransport",
  or asks about Singapore public transport API data in any context.
---

Singapore's LTA DataMall provides ~30 REST APIs covering public transport, traffic,
active mobility, geospatial data, and EV infrastructure. All endpoints share the
same base URL and authentication method.

## API Authentication

All API calls require an `AccountKey` header. The key is stored in the global
environment variable `api_key`. Use this pattern for every call:

```python
import os, requests, json

api_key = os.environ["api_key"]

def _send_query(url, key, skip=0):
    header = {"AccountKey": api_key, "accept": "application/json"}
    response = requests.get(
        f"{url}$skip={skip}" if skip > 0 else url, headers=header
    ).text
    res = json.loads(response)
    if key is not None:
        res = res[key]

    if len(res) == 500:
        res.extend(_send_query(url, key, skip + 500))
    return res
```

**Key points:**
- The base URL is: `https://datamall2.mytransport.sg/ltaodataservice/`
- Responses are limited to **500 records per call**. The `$skip` query parameter
  retrieves subsequent pages (e.g., `?skip=500`, `?skip=1000`). The helper above
  handles this recursion automatically.
- The API returns JSON wrapped in an OData envelope: `{"odata.metadata": "...", "value": [...]}`.
  When the response contains a list, the data array is typically under the `"value"` key.
  Pass `key="value"` to `_send_query` when the response contains a `value` key.
- **Exceptions:** Bus Arrival uses `"Services"` key, some endpoints return the
  response directly without wrapping, and batch/file-download endpoints return
  a single record with a `Link` field.

## API Categories

| Category | Count | Examples |
|----------|-------|----------|
| Public Transport | 15 | Bus Arrival, Bus Routes, Bus Stops, Taxi Availability, Train Service Alerts, Station Crowd Density |
| Traffic | 11 | Carpark Availability, Traffic Incidents, Traffic Speed Bands, Traffic Images, Faulty Traffic Lights, Flood Alerts |
| Active Mobility | 1 | Bicycle Parking |
| Geospatial | 1 | Geospatial Whole Island |
| Electric Vehicle | 2 | EV Charging Points, EV Charging Points Batch |

## Endpoint Details

See `${CLAUDE_PLUGIN_ROOT}/references/endpoints.md` for the full specification of all 30 endpoints,
including URLs, request parameters, response fields, and sample data.

Quick reference for the most commonly used endpoints:

### Bus Arrival (v3)
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/v3/BusArrival`
- **Query params:** `BusStopCode` (required, 5-digit code), `ServiceNo` (optional)
- **Response key:** `"Services"` — list of bus services with NextBus objects
- **NextBus fields:** `EstimatedArrival`, `Latitude`, `Longitude`, `Load` (SEA/SDA/LSD), `Feature` (WAB = wheelchair accessible), `Type` (SD/DD/BD)

```python
arrivals = _send_query(
    "https://datamall2.mytransport.sg/ltaodataservice/v3/BusArrival?BusStopCode=83139",
    key="Services"
)
```

### Bus Stops
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/BusStops`
- **Query params:** `BusStopCode` (optional, filter by 5-digit code)
- **Response key:** `"value"`
- **Fields:** `BusStopCode`, `RoadName`, `Description` (landmarks), `Latitude`, `Longitude`

```python
stops = _send_query(
    "https://datamall2.mytransport.sg/ltaodataservice/BusStops",
    key="value"
)
```

### Carpark Availability (v2)
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/CarParkAvailabilityv2`
- **No query params.** Returns all carparks.
- **Response key:** `"value"`
- **Fields:** `CarParkID`, `Area`, `Development`, `Location` (lat/long), `AvailableLots`, `LotType` (C=car, H=heavy, Y=motorcycle), `Agency` (HDB/LTA/URA)

```python
carparks = _send_query(
    "https://datamall2.mytransport.sg/ltaodataservice/CarParkAvailabilityv2",
    key="value"
)
```

### Taxi Availability
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/Taxi-Availability`
- **No query params.**
- **Response key:** `"value"`
- **Fields:** `Latitude`, `Longitude` (each item is one available taxi)

```python
taxis = _send_query(
    "https://datamall2.mytransport.sg/ltaodataservice/Taxi-Availability",
    key="value"
)
```

### Traffic Incidents
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/TrafficIncidents`
- **No query params.**
- **Response key:** `"value"`
- **Fields:** `Type` (Accident, Roadwork, Vehicle breakdown, Weather, Obstacle, Road Block, Heavy Traffic, Miscellaneous, Diversion, Unattended Vehicle, Fire, Plant Failure, Reverse Flow), `Latitude`, `Longitude`, `Message`

### Traffic Speed Bands (v4)
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/v4/TrafficSpeedBands`
- **No query params.**
- **Response key:** `"value"`
- **Fields:** `LinkID`, `RoadName`, `RoadCategory` (1-8), `SpeedBand` (1-8, 1=slowest 0-9km/h, 8=fastest 70+km/h), `MinimumSpeed`, `MaximumSpeed`, `StartLon`, `StartLat`, `EndLon`, `EndLat`

### Train Service Alerts
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/TrainServiceAlerts`
- **No query params.**
- **Response wraps differently:** `{"value": {...}}` (single object, not a list — pass `key="value"`)
- **Fields:** `Status` (1=normal/minor delays, 2=disrupted/major), `AffectedSegments` (list), `Message` (list)
- **Train line codes:** EWL, NSL, NEL, CCL, DTL, TEL, BPL, SLRT, PLRT, CGL, CEL

### Station Crowd Density (Real-time)
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/PCDRealTime`
- **Query params:** `TrainLine` (required — EWL, NSL, NEL, CCL, DTL, TEL, BPL, SLRT, PLRT, CGL, CEL)
- **Response key:** `"value"`
- **Fields:** `Station`, `StartTime`, `EndTime`, `CrowdLevel` (l=low, h=high, m=moderate, NA)

### Faulty Traffic Lights
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/FaultyTrafficLights`
- **Fields:** `AlarmID`, `NodeID`, `Type` (4=Blackout, 13=Flashing Yellow), `StartDate`, `EndDate`, `Message`

### Flood Alerts
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/PubFloodAlerts`
- **Fields:** `alertId`, `dateTime`, `msgType` (Alert/Cancel), `event`, `responseType` (Avoid), `urgency`, `severity` (Extreme/Severe/Moderate/Minor), `expires`, `headline`, `description`, `instruction`, `areaDesc`, `circle` (lat,lon,radius), `status`

### EV Charging Points
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/EVChargingPoints`
- **Query params:** `PostalCode` (required, 6-digit)
- **Response key:** `"value"`
- **Fields:** `address`, `name`, `latitude`, `longitude`, `locationId`, `status` (0=occupied, 1=available, 100=fail, ""=n/a), `chargingPoints` (nested: `evCpld`, `plugType`, `powerRating`, `chargingSpeed` kW, `status`), `evlds`, `price`, `priceType`

### Bicycle Parking
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/BicycleParkingv2`
- **Query params:** `Lat` (required), `Long` (required), `Dist` (optional, default 0.5km radius)
- **Response key:** `"value"`
- **Fields:** `Description`, `Latitude`, `Longitude`, `RackType` (Racks/Yellow Box), `RackCount`, `ShelterIndicator`

## Batch/Download Endpoints

These endpoints return a `Link` to a downloadable file (CSV, ZIP, SHP, or JSON) instead
of inline data. The links expire after 5 minutes:

| Endpoint | Format |
|----------|--------|
| Passenger Volume by Bus Stops | CSV (ZIP) |
| Passenger Volume by OD Bus Stops | CSV (ZIP) |
| Passenger Volume by OD Train Stations | CSV (ZIP) |
| Passenger Volume by Train Stations | CSV (ZIP) |
| Traffic Flow | JSON |
| Geospatial Whole Island | SHP (ZIP) |
| EV Charging Points Batch | JSON |

For these, call the API normally to get the `Link`, then download and parse the file:

```python
import requests, json, io, zipfile, csv

# Get the download link
resp = _send_query(
    "https://datamall2.mytransport.sg/ltaodataservice/PV/Bus?Date=202604",
    key="value"
)  # resp is a list with one item containing {"Link": "..."}
link = resp[0]["Link"]

# Download and parse CSV inside ZIP
raw = requests.get(link).content
with zipfile.ZipFile(io.BytesIO(raw)) as zf:
    with zf.open(zf.namelist()[0]) as f:
        reader = csv.DictReader(io.TextIOWrapper(f))
        for row in reader:
            print(row)
```

## Common Query Patterns

### Find a bus stop by name
Search the Bus Stops dataset for a road name or landmark:
```python
stops = _send_query(
    "https://datamall2.mytransport.sg/ltaodataservice/BusStops",
    key="value"
)
matches = [s for s in stops if "Orchard" in s["RoadName"]]
```

### Get bus arrival at a stop
```python
arrivals = _send_query(
    "https://datamall2.mytransport.sg/ltaodataservice/v3/BusArrival?BusStopCode=YOUR_CODE",
    key="Services"
)
```

### Check for traffic incidents
```python
incidents = _send_query(
    "https://datamall2.mytransport.sg/ltaodataservice/TrafficIncidents",
    key="value"
)
```

### Check car park availability in an area
```python
carparks = _send_query(
    "https://datamall2.mytransport.sg/ltaodataservice/CarParkAvailabilityv2",
    key="value"
)
matches = [c for c in carparks if c.get("Area") == "Orchard"]
```

### Check train line disruptions
```python
alerts = _send_query(
    "https://datamall2.mytransport.sg/ltaodataservice/TrainServiceAlerts",
    key="value"
)
```

## Important Notes

- **Bus Arrival** response structure: `{"BusStopCode": "...", "Services": [...]}`.
  Use `key="Services"` to extract the service list.
- When bus arrival data is unavailable (outside operating hours), the `NextBus`,
  `NextBus2`, `NextBus3` fields are all `null`.
- **Bus load** values: SEA (Seats Available), SDA (Standing Available), LSD (Limited Standing).
- **Bus type** values: SD (Single Deck), DD (Double Deck), BD (Bendy).
- **Speed Band** 1-8 maps to 0-9, 10-19, 20-29, ..., 50-59, 60-69, 70+ km/h.
- **Crowd Level**: l = low, m = moderate, h = high, NA = not available.
- The API may change response sizes or field names over time; always check the
  returned data structure rather than assuming fixed schemas.
