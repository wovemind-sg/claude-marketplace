# singapore-lta

**This plugin is specific to Singapore.** It covers the LTA DataMall API run by Singapore's Land Transport Authority, which only has data about transport in Singapore.

Teaches Claude how to query [LTA DataMall](https://datamall.lta.gov.sg/): its authentication, the 500-records-per-call paging, the response shapes, and about 30 endpoints for buses, trains, taxis, car parks, traffic, flood alerts, bicycle parking and EV charging points. The full endpoint list with parameters and response fields is in `references/endpoints.md`.

## Install

```
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install singapore-lta@wovemind
```

## Requirements

- An LTA DataMall account key. Request one on the DataMall website.
- Python with the `requests` package, which the code the skill writes uses.

## Environment variables

| Variable | Meaning |
|---|---|
| `api_key` | Your LTA DataMall account key. The code sends it in the `AccountKey` header of every request. |

The name is lowercase `api_key`, exactly as written. Set it in the shell you start Claude Code from, for example `export api_key=...`.

## Usage

The skill triggers automatically when you ask about Singapore transport data, LTA DataMall or MyTransport. You can also invoke it directly with `/singapore-lta:singapore-lta`.

Example prompts:

> "When is the next bus at stop 83139?"
> "Are there any MRT disruptions right now?"
> "How many car park lots are free around Orchard?"

## Example

Ask Claude:

> "When is the next bus at stop 83139?"

Claude calls the Bus Arrival endpoint with your key and reads the `Services` list from the response:

```python
import os, requests

resp = requests.get(
    "https://datamall2.mytransport.sg/ltaodataservice/v3/BusArrival?BusStopCode=83139",
    headers={"AccountKey": os.environ["api_key"], "accept": "application/json"},
)
for service in resp.json()["Services"]:
    next_bus = service["NextBus"] or {}  # null outside operating hours
    print(service["ServiceNo"], next_bus.get("EstimatedArrival"))
```

It then answers with each bus service and its estimated arrival time. Outside operating hours the arrival fields are empty, and Claude says so instead of reporting a time.
