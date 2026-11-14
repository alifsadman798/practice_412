# SmartRoute BD — Plain-Language Project Overview

## What this project is

SmartRoute BD is a website that helps people explore ways to travel between places in Bangladesh. A visitor can enter where a journey starts and ends, then compare possible bus, train, and combined journeys. The site also lets people look up bus and train timetables across 64 districts.

The project is a planning and information tool. It estimates routes, fares, and journey times from the transport information and rules stored in the project. It does not book tickets, track a traveller's live location, or receive live traffic information.

## Who uses it

- **A visitor** can search journeys, explore timetables, and view the district map.
- **A registered traveller** can also save favourite routes or services, and set travel preferences.
- **An administrator** maintains transport information, bus schedules, train services, and checks administrative audit activity logs.

## What happens when someone plans a journey

1. The traveller enters an origin, a destination, a travel date, and other available search choices.
2. The website sends that request to the application's service.
3. The service checks that the places are supported and reads the relevant transport information from the database.
4. The routing components work out possible bus, train, local, or combined journeys. They account for things such as train stop order and operating days, journey distance, transfer time, and local connections.
5. The service compares the options by fare, estimated duration, and distance.
6. The website displays the route details, estimated costs and times, transfers, and any route advisories.

### Journey-search flowchart

```text
Traveller chooses places, date, and search options
                         |
                         v
               Public website (static/)
                         |
                         v
             Application service (src/api/)
                         |
                         v
             Transport information (database/)
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
    Bus routing     Train routing   Local connections
    (src/bus/)   (src/train/) (src/multimodal/)
          +--------------+--------------+
                         |
                         v
       Combine and compare possible journeys
                         |
                         v
       Results, route comparisons, and estimates
                         |
                         v
               Traveller chooses an option
```

The diagram describes the general flow. The bus route finder uses the district-distance network to find a path; bus departure information can also be explored separately in the timetable search.

## Main things the website can do

### Plan and compare journeys

- Find bus-only and train-only journey options, as well as supported combinations involving local transport.
- Show the places visited, journey legs, transfers, and available schedule details.
- Highlight options that are cheapest, fastest by estimated duration, or shortest by distance.
- Show estimated fares and time ranges rather than presenting them as guaranteed quotes.

### Explore timetables and transit map

- Search bus timetable information independently from a full journey search.
- Look up train services and their stops, including operating-day and off-day information where available.
- Interactive 64 districts transit map viewer.

### Use an account (optional)

Registered travellers can manage a profile and preferences, and save favourite routes and services. An account is not needed for the public journey planner or timetable searches.

### Maintain the service (administrator)

The protected admin portal supports:

- Adding, changing, or removing districts, locations, distance connections, bus schedules, train services, and train stops.
- Updating routing settings used by the estimates.
- Reviewing administrative activity and database mutation logs.



## How route information is estimated

The estimates come from the project's stored transport datasets and configured rules:

- **Bus distances and paths** are based on connections between districts. The estimated bus fare uses a base amount, distance, and a factor for core cities along the route.
- **Bus travel time** uses configured time-of-day and major-city factors. These are rule-based estimates, not readings from live traffic.
- **Train options** use recorded services, their ordered stops, timetable information, and off-days. Train fare estimates are based mainly on distance, with an additional rule involving intermediate stops.
- **Local connections** help connect places such as a district and a nearby station. Their estimates use configured distances, a fixed local-leg fare, and an assumed average speed.
- **Combined trips** include time to change transport. The system limits the number of main bus/train transfers and may show guidance when local travel is needed between two legs.
- **Comparison labels** are based on the calculated options: lowest estimated fare, shortest estimated journey duration, or least total distance.

These are planning estimates, not guarantees. Dataset coverage, schedules, fares, traffic, and actual service availability can change. Travellers should confirm current details with the transport provider before travelling.

## Project folders, explained

```text
Smart_route_BD_VS - Anti/
|
+-- data/                 Source transport tables: districts, distances,
|                         local links, bus schedules, train routes and stops
|
+-- src/                  The application's working parts
|   |
|   +-- auth/             Sign-in and account security helpers
|   +-- database/         Database setup, records, queries and data import
|   +-- data/              Reads, cleans and organizes source transport data
|   +-- bus/                Bus-network routing, fares and time estimates
|   +-- train/            Train routes, stops, timetables and fares
|   +-- multimodal/    Local travel and journeys combining transport types
|   +-- api/                 Connects the website to routing, accounts and admin
|   +-- shared/           Common definitions and settings used across modules
|   +-- utils/            Shared location and time helpers
|
+-- static/               The pages, styling, images and browser behavior
|   +-- index.html        Public journey planner and timetable pages
|   +-- app.js            Makes the public page search and display information
|   +-- admin.html        Administrator portal page
|   +-- admin.js          Makes the administrator portal work
|   +-- app.css           Shared visual design
|
+-- alembic/              Database change history and migration support
+-- tests/                Automated checks for routing, pages and workflows
+-- docs/                 Project explanations and technical diagrams
+-- README.md             Setup instructions and quick project reference
+-- requirements.txt      Python packages needed to run the application
+-- .env.example          Example settings to configure before running
```

## In one sentence

SmartRoute BD takes maintained Bangladesh transport data, works out and compares estimated journeys, and presents the results through a public website, while giving registered travellers and administrators additional reporting and management tools.
