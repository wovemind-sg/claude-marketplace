# LTA DataMall API — Endpoint Reference

LTA DataMall API User Guide v6.8 (21 Apr 2026)

## Public Transport API

### 1. Bus Arrival
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/v3/BusArrival`
- **Description:** Real-time bus arrival info for a bus stop (ETA, location, load)
- **Update Freq:** 20 seconds
- **Parameters:** `BusStopCode` (required), `ServiceNo` (optional — filter by service)
- **Response key:** `Services` — array of services, each with `ServiceNo`, `Operator`, `NextBus`, `NextBus2`, `NextBus3`
- **NextBus fields:** `OriginCode`, `DestinationCode`, `EstimatedArrival`, `Monitored`, `Latitude`, `Longitude`, `VisitNumber`, `Load` (SEA/SDA/LSD), `Feature` (WAB for wheelchair), `Type` (SD/DD/BD)
- **Operators:** SBST (SBS Transit), SMRT (SMRT Corp), TTS (Tower Transit), GAS (Go Ahead Singapore)
- **Note:** When no data available, API may return nothing at all (not even empty fields). When a bus is at the stop, round down derived duration. If only one bus left for the night, NextBus2 and NextBus3 will be empty/blank.

### 2. Bus Services
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/BusServices`
- **Description:** Service info for all active bus services (first/last stop, dispatch frequency)
- **Parameters:** `ServiceNo` (optional — filter by bus number, e.g. `107M`)
- **Fields:** `ServiceNo`, `Operator`, `Direction` (1 or 2; loop services have 1), `Category` (EXPRESS/FEEDER/INDUSTRIAL/TOWNLINK/TRUNK/2 TIER FLAT FEE/FLAT FEE), `OriginCode`, `DestinationCode`, `AM_Peak_Freq`, `AM_Offpeak_Freq`, `PM_Peak_Freq`, `PM_Offpeak_Freq`, `LoopDesc`
- **Loop services note:** Some loop services append 'G' or 'W' for direction (e.g. 225G, 225W)

### 3. Bus Routes
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/BusRoutes`
- **Description:** Full route info — all stops per service, first/last bus timings per stop
- **Fields:** `ServiceNo`, `Operator`, `Direction`, `StopSequence`, `BusStopCode`, `Distance` (km from start), `WD_FirstBus`, `WD_LastBus`, `SAT_FirstBus`, `SAT_LastBus`, `SUN_FirstBus`, `SUN_LastBus`

### 4. Bus Stops
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/BusStops`
- **Description:** All bus stops with codes and coordinates
- **Parameters:** `BusStopCode` (optional — filter by 5-digit code)
- **Fields:** `BusStopCode`, `RoadName`, `Description` (landmarks), `Latitude`, `Longitude`

### 5. Passenger Volume by Bus Stops
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/PV/Bus`
- **Description:** Tap-in/out passenger volume by weekday/weekend per bus stop
- **Parameters:** `Date` (optional, format YYYMM, last 3 months; e.g. `201803`)
- **Response:** Single record with `Link` (CSV download URL, expires 5 min)
- **CSV format:** YEAR_MONTH, DAY_TYPE, TIME_PER_HOUR, PT_TYPE, PT_CODE, TOTAL_TAP_IN_VOLUME, TOTAL_TAP_OUT_VOLUME

### 6. Passenger Volume by OD Bus Stops
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/PV/ODBus`
- **Description:** Origin-destination trip counts between bus stops
- **Parameters:** `Date` (optional, format YYYMM)
- **Response:** Single `Link` to ZIP file (CSV inside)
- **CSV format:** YEAR_MONTH, DAY_TYPE, TIME_PER_HOUR, PT_TYPE, ORIGIN_PT_CODE, DESTINATION_PT_CODE, TOTAL_TRIPS

### 7. Passenger Volume by OD Train Stations
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/PV/ODTrain`
- **Description:** Origin-destination trip counts between train stations
- **Parameters:** `Date` (optional, format YYYMM)
- **Response:** Single `Link` to ZIP file

### 8. Passenger Volume by Train Stations
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/PV/Train`
- **Description:** Tap-in/out passenger volume per train station
- **Parameters:** `Date` (optional, format YYYMM)
- **Response:** Single `Link` to ZIP file

### 9. Taxi Availability
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/Taxi-Availability`
- **Description:** Live coordinates of taxis available for hire (excludes hired/busy taxis)
- **Update Freq:** 1 minute
- **Fields:** `Latitude`, `Longitude`
- **Note:** Returns 500 records per call; use _send_query to get all

### 10. Taxi Stands
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/TaxiStands`
- **Description:** Taxi stand locations and details
- **Update Freq:** Monthly
- **Fields:** `TaxiCode`, `Latitude`, `Longitude`, `Bfa` (barrier free: Yes/No), `Ownership` (LTA/CCS/Private), `Type` (Stand/Stop), `Name`
- **Note:** Dataset is small; no pagination needed

### 11. Train Service Alerts
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/TrainServiceAlerts`
- **Description:** Real-time train service unavailability/disruption info
- **Fields:** `Status` (1=normal/minor delays, 2=disrupted/major delays), `Line` (EWL/NSL/NEL/CCL/DTL/TEL/BPL/SLRT/PLRT/CGL/CEL), `Direction`, `Stations` (comma-separated codes), `FreePublicBus` (station codes with free bus), `FreeMRTShuttle` (station codes with free shuttle), `MRTShuttleDirection`, `Message` (Content + CreatedDate)
- **Response structure:**
  - Normal: `{"value": {"Status": 1, "AffectedSegments": [], "Message": []}}`
  - Disrupted: `{"value": {"Status": 2, "AffectedSegments": [...], "Message": [...]}}`
- **Train line codes:** EWL, NSL, NEL, CCL, DTL, TEL, BPL, SLRT, PLRT, CGL (Changi Extension), CEL (Circle Line Extension)

### 12. Facilities Maintenance
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/v2/FacilitiesMaintenance`
- **Description:** Adhoc lift maintenance at MRT stations
- **Fields:** `Line`, `StationCode`, `StationName`, `LiftID`, `LiftDesc`

### 13. Station Crowd Density Real-time
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/PCDRealTime`
- **Description:** Real-time MRT/LRT station crowd levels per train line
- **Update Freq:** 10 minutes
- **Parameters:** `TrainLine` (required — EWL/NSL/NEL/CCL/DTL/TEL/BPL/SLRT/PLRT/CGL/CEL)
- **Fields:** `Station`, `StartTime`, `EndTime`, `CrowdLevel` (l=low, h=high, m=moderate, NA)

### 14. Station Crowd Density Forecast
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/PCDForecast`
- **Description:** Forecasted crowd levels at 30-min intervals for the current day
- **Update Freq:** 24 hours (daily)
- **Parameters:** `TrainLine` (required)
- **Fields:** `Date`, `Station`, `Start`, `CrowdLevel` (l/h/m/NA)

### 15. Planned Bus Routes
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/PlannedBusRoutes`
- **Description:** New/updated bus routes (release only ON/AFTER Effective Date)
- **Fields:** Same structure as Bus Routes plus `EffectiveDate`

---

## Traffic API

### 16. Carpark Availability
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/CarParkAvailabilityv2`
- **Description:** Available parking lots for HDB, LTA, and URA carparks
- **Update Freq:** 1 minute
- **Fields:** `CarParkID`, `Area` (Orchard/Marina/Harbfront/JurongLakeDistrict or blank), `Development`, `Location` (lat+long combined string), `AvailableLots`, `LotType` (C=Cars, H=Heavy Vehicles, Y=Motorcycles), `Agency` (HDB/LTA/URA)

### 17. Estimated Travel Times
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/EstTravelTimes`
- **Description:** Expressway segment travel times in minutes
- **Update Freq:** 5 minutes
- **Fields:** `Name` (expressway), `Direction` (1=east-to-west/south-to-north, 2=west-to-east/north-to-south), `FarEndPoint`, `StartPoint`, `EndPoint`, `EstTime` (minutes)

### 18. Faulty Traffic Lights
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/FaultyTrafficLights`
- **Description:** Currently faulty or under-maintenance traffic lights
- **Update Freq:** 2 minutes
- **Fields:** `AlarmID`, `NodeID`, `Type` (4=Blackout, 13=Flashing Yellow), `StartDate`, `EndDate`, `Message`

### 19. Planned Road Openings
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/RoadOpenings`
- **Description:** New roads planned to be opened
- **Update Freq:** 24 hours
- **Fields:** `EventID`, `StartDate`, `EndDate`, `SvcDept`, `RoadName`, `Other`

### 20. Approved Road Works
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/RoadWorks`
- **Description:** Current/approved road works
- **Update Freq:** 24 hours
- **Fields:** `EventID`, `StartDate`, `EndDate`, `SvcDept`, `RoadName`, `Other`

### 21. Traffic Images
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/Traffic-Imagesv2`
- **Description:** Links to live traffic camera images on expressways and checkpoints
- **Update Freq:** 1-5 minutes
- **Fields:** `CameraID`, `Latitude`, `Longitude`, `ImageLink` (expires 5 min)
- **Note:** Use ANNEX G for CameraID-to-location descriptions

### 22. Traffic Incidents
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/TrafficIncidents`
- **Description:** Active road incidents (accidents, breakdowns, road blocks, diversions)
- **Update Freq:** 2 minutes
- **Fields:** `Type` (Accident/Roadwork/Vehicle breakdown/Weather/Obstacle/Road Block/Heavy Traffic/Miscellaneous/Diversion/Unattended Vehicle/Fire/Plant Failure/Reverse Flow), `Latitude`, `Longitude`, `Message`

### 23. Traffic Speed Bands
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/v4/TrafficSpeedBands`
- **Description:** Current road speeds on expressways/arterial roads in speed bands
- **Update Freq:** 5 minutes
- **Fields:** `LinkID`, `RoadName`, `RoadCategory` (1=Expressways, 2=Major Arterial, 3=Arterial, 4=Minor Arterial, 5=Small Roads, 6=Slip Roads, 8=Short Tunnels), `SpeedBand` (1–8, higher=faster), `MinimumSpeed`, `MaximumSpeed` (km/h), `StartLon`, `StartLat`, `EndLon`, `EndLat`
- **Speed bands:** 1=0–9 km/h, 2=10–19, 3=20–29, 4=30–39, 5=40–49, 6=50–59, 7=60–69, 8=70+

### 24. VMS / EMAS
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/VMS`
- **Description:** Electronic signboard traffic advisories
- **Update Freq:** 2 minutes
- **Fields:** `EquipmentID`, `Latitude`, `Longitude`, `Message`

### 25. Traffic Flow
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/TrafficFlow`
- **Description:** Hourly average traffic flow (quarterly data)
- **Update Freq:** Quarterly
- **Response:** Single `Link` to JSON download (expires 5 min)

### 26. Flood Alerts
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/PubFloodAlerts`
- **Description:** Flood alert information across Singapore (from PUB)
- **Update Freq:** 3 minutes
- **Fields:** `alertId`, `dateTime`, `msgType` (Alert/Cancel), `event`, `responseType`, `urgency`, `severity` (Extreme/Severe/Moderate/Minor), `expires`, `senderName` (PUB), `headline`, `description`, `instruction`, `areaDesc`, `circle` (lat,long,radius), `status` (Actual)

---

## Active Mobility

### 27. Bicycle Parking
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/BicycleParkingv2`
- **Description:** Bicycle parking locations within a radius
- **Update Freq:** Monthly
- **Parameters:** `Lat` (required), `Long` (required), `Dist` (optional, default 0.5 km)
- **Fields:** `Description`, `Latitude`, `Longitude`, `RackType` (Racks/Yellow Box), `RackCount`, `ShelterIndicator`

---

## Geospatial

### 28. Geospatial Whole Island
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/GeospatialWholeIsland`
- **Description:** SHP files for geospatial layers
- **Parameters:** `ID` (required — layer name, case-sensitive, no spaces, e.g. `ArrowMarking`)
- **Response:** Single `Link` to ZIP download (expires 5 min)

---

## Electric Vehicle

### 29. EV Charging Points
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/EVChargingPoints`
- **Description:** EV charging points and availability by postal code
- **Update Freq:** 5 minutes
- **Parameters:** `PostalCode` (required)
- **Response:** Array of station objects with `address`, `name`, `longitude`, `latitude`, `locationId`, `status` (0=occupied, 1=available, 100=not available), `operationHours`, `operator`, `position`, `chargingPoints` (array: `status`, `plugType`, `powerRating`, `chargingSpeed` kW), `plugTypes`, `evlds` (individual connector statuses), `price`, `priceType` ($/h or $/kWh)
- **EV status codes:** 0=Occupied (CHARGING/RESERVED/BLOCKED), 1=Available, ""=Not Available (OUTOFORDER/INOPERATIVE/UNKNOWN/PLANNED/REMOVED)

### 30. EV Charging Points Batch
- **URL:** `https://datamall2.mytransport.sg/ltaodataservice/EVCBatch`
- **Description:** All EV charging points in a single file
- **Update Freq:** 5 minutes
- **Response:** Single `Link` to JSON download (expires 5 min)
