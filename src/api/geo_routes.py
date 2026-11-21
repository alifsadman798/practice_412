import os
import csv
import json
import re
import logging
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/geo", tags=["Geographic & Map"])

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCAL_GEO_DIR = PROJECT_ROOT / "data" / "geographic"
OSM_GEO_DIR = LOCAL_GEO_DIR / "osm_outputs" / "csv_location_matching"
PHASE_4B1_DIR = LOCAL_GEO_DIR / "osm_outputs" / "phase_4B_1"
PHASE_4B2B_DIR = LOCAL_GEO_DIR / "osm_outputs" / "phase_4B_2B"


def _find_file(filename: str, preferred_dirs: list[Path]) -> Path | None:
    for d in preferred_dirs:
        p = d / filename
        if p.exists():
            return p
    return None


# Lazy in-memory cache for fast response times
_CACHE: dict[str, Any] = {}


def _load_geo_cache():
    if _CACHE.get("initialized"):
        return _CACHE

    # 1. Location Master
    master_path = _find_file("csv_location_master.csv", [OSM_GEO_DIR, LOCAL_GEO_DIR])
    districts = []
    stations = []
    local_places = []
    location_by_id = {}
    location_by_name_cat = {}

    if master_path:
        with open(master_path, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                eid = r["Location_Entity_ID"]
                cat = r["Transport_Category"]
                orig_name = r.get("Original_CSV_Location_Name", "")
                canon_name = r.get("Canonical_Matched_Name", orig_name)
                lat_str = r.get("Latitude", "").strip()
                lon_str = r.get("Longitude", "").strip()
                lat = float(lat_str) if lat_str else None
                lon = float(lon_str) if lon_str else None
                item = {
                    "entity_id": eid,
                    "name": orig_name or canon_name,
                    "canonical_name": canon_name,
                    "category": cat,
                    "district": r.get("District", ""),
                    "actual_district": r.get("Actual_District", r.get("District", "")),
                    "latitude": lat,
                    "longitude": lon,
                    "coordinate_type": r.get("Coordinate_Type", ""),
                    "verification_status": r.get("Verification_Status", ""),
                    "road_anchor_id": r.get("Road_Anchor_ID", ""),
                    "road_anchor_name": r.get("Road_Anchor_Name", ""),
                    "road_anchor_category": r.get("Road_Anchor_Category", ""),
                    "trip_count": int(r.get("Geometry_Reference_Count", 0) or 0),
                }
                location_by_id[eid] = item
                for n in [orig_name, canon_name]:
                    if n:
                        location_by_name_cat[(n.casefold(), cat)] = item
                        location_by_name_cat[(n.casefold(), cat, r.get("District", "").casefold())] = item

                if cat == "district":
                    districts.append(item)
                elif cat == "train_station":
                    stations.append(item)
                elif cat == "local_place":
                    local_places.append(item)

    # 2. Bus Corridor GeoJSON (11 corridors)
    bus_geojson_path = _find_file("bus_corridor_geometry.geojson", [PHASE_4B1_DIR, LOCAL_GEO_DIR])
    bus_corridors = []
    bus_corridor_by_edge = {}
    if bus_geojson_path:
        with open(bus_geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for feat in data.get("features", []):
                props = feat.get("properties", {})
                eid = props.get("Edge_ID", "")
                geom = feat.get("geometry", {})
                coords = geom.get("coordinates", [])
                item = {
                    "edge_id": eid,
                    "from_district": props.get("Origin_District", props.get("From_District", "")),
                    "to_district": props.get("Destination_District", props.get("To_District", "")),
                    "operational_distance_km": float(props.get("Operational_Distance_KM", 0)),
                    "extracted_length_km": float(props.get("Path_Length_KM", props.get("Extracted_Path_Length_KM", 0))),
                    "node_count": int(props.get("Node_Count", len(coords))),
                    "coordinates": coords,
                    "verification_status": "verified_osm_road_path",
                    "geometry_category": "estimated_highway_corridor",
                }
                bus_corridors.append(item)
                bus_corridor_by_edge[eid] = item

    # 3. Railway Link GeoJSON (190 generated mainline links)
    rail_geojson_path = _find_file("railway_link_geometry.geojson", [PHASE_4B2B_DIR, LOCAL_GEO_DIR])
    railway_links = []
    railway_link_by_id = {}
    if rail_geojson_path:
        with open(rail_geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for feat in data.get("features", []):
                props = feat.get("properties", {})
                rlink_id = props.get("RLINK_ID", "")
                geom = feat.get("geometry", {})
                coords = geom.get("coordinates", [])
                item = {
                    "rlink_id": rlink_id,
                    "origin_station": props.get("Origin_Station", ""),
                    "origin_district": props.get("Origin_District", ""),
                    "destination_station": props.get("Destination_Station", ""),
                    "destination_district": props.get("Destination_District", ""),
                    "operational_distance_km": float(props.get("Operational_Distance_KM", 0)),
                    "path_length_km": float(props.get("Path_Length_KM", 0)),
                    "node_count": int(props.get("Node_Count", len(coords))),
                    "coordinates": coords,
                    "verification_status": "verified_osm_mainline_track",
                    "geometry_category": "estimated_railway_track_link",
                }
                railway_links.append(item)
                railway_link_by_id[rlink_id] = item

    # 4. Bus Schedule Route Lookup
    bus_sched_path = _find_file("bus_schedule_route_lookup.csv", [OSM_GEO_DIR, LOCAL_GEO_DIR])
    bus_route_lookup = {}
    if bus_sched_path:
        with open(bus_sched_path, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                key = (r["From"].strip().casefold(), r["To"].strip().casefold())
                bus_route_lookup[key] = r

    # 5. Train Service Hop Lookup
    train_hop_path = _find_file("train_service_hop_lookup.csv", [OSM_GEO_DIR, LOCAL_GEO_DIR])
    train_hop_lookup = {}
    if train_hop_path:
        with open(train_hop_path, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                tno = r["Train_No"].strip()
                s1 = r["From_Station"].strip().casefold()
                s2 = r["To_Station"].strip().casefold()
                train_hop_lookup[(tno, s1, s2)] = r
                train_hop_lookup[(s1, s2)] = r

    # 6. Local Geometry Lookup
    local_path = _find_file("local_geometry_lookup.csv", [OSM_GEO_DIR, LOCAL_GEO_DIR])
    local_links = []
    local_link_lookup = {}
    if local_path:
        with open(local_path, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                u = r["From_Place"].strip()
                v = r["To_Place"].strip()
                pdist = r["Parent_District"].strip()
                o_lat = float(r["Origin_Latitude"]) if r.get("Origin_Latitude") else None
                o_lon = float(r["Origin_Longitude"]) if r.get("Origin_Longitude") else None
                d_lat = float(r["Destination_Latitude"]) if r.get("Destination_Latitude") else None
                d_lon = float(r["Destination_Longitude"]) if r.get("Destination_Longitude") else None
                item = {
                    "local_link_id": r["Local_Link_ID"],
                    "from_place": u,
                    "to_place": v,
                    "parent_district": pdist,
                    "distance_km": float(r["Operational_Distance_KM"]) if r.get("Operational_Distance_KM") else 0.0,
                    "origin_lat": o_lat,
                    "origin_lon": o_lon,
                    "destination_lat": d_lat,
                    "destination_lon": d_lon,
                    "classification": r.get("Classification_Category", ""),
                    "geometry_availability": r.get("Geometry_Availability", ""),
                    "readiness_status": r.get("Readiness_Status", ""),
                    "display_permission": r.get("Display_Permission", ""),
                    "safety_disclaimer": r.get("Safety_Disclaimer", ""),
                }
                local_links.append(item)
                local_link_lookup[(u.casefold(), v.casefold())] = item
                local_link_lookup[(v.casefold(), u.casefold())] = item

    # 8. District Boundaries (simplified SVG paths for Google Maps-style light basemap)
    boundaries_path = _find_file("district_boundaries_simplified.json", [LOCAL_GEO_DIR, OSM_GEO_DIR])
    district_boundaries = []
    if boundaries_path:
        with open(boundaries_path, "r", encoding="utf-8") as f:
            district_boundaries = json.load(f)

    # 9. Train stops reference index for timetable stop lookups
    train_stops_path = PROJECT_ROOT / "data" / "train_stops.csv"
    train_stops_by_train = {}
    if train_stops_path.exists():
        with open(train_stops_path, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                tno = r.get("Train_No") or r.get("\ufeffTrain_No") or ""
                if tno:
                    train_stops_by_train.setdefault(tno.strip(), []).append(r)

    _CACHE["districts"] = districts
    _CACHE["stations"] = stations
    _CACHE["local_places"] = local_places
    _CACHE["location_by_id"] = location_by_id
    _CACHE["location_by_name_cat"] = location_by_name_cat
    _CACHE["bus_corridors"] = bus_corridors
    _CACHE["bus_corridor_by_edge"] = bus_corridor_by_edge
    _CACHE["railway_links"] = railway_links
    _CACHE["railway_link_by_id"] = railway_link_by_id
    _CACHE["bus_route_lookup"] = bus_route_lookup
    _CACHE["train_hop_lookup"] = train_hop_lookup
    _CACHE["local_links"] = local_links
    _CACHE["local_link_lookup"] = local_link_lookup
    _CACHE["district_boundaries"] = district_boundaries
    _CACHE["train_stops_by_train"] = train_stops_by_train
    _CACHE["initialized"] = True
    return _CACHE


class LegInput(BaseModel):
    mode: str
    origin: str
    destination: str
    service: str = ""
    stops: list[dict[str, Any]] = Field(default_factory=list)
    path: list[str] = Field(default_factory=list)


class RouteGeometryRequest(BaseModel):
    legs: list[LegInput]


@router.get("/layers")
def get_map_layers():
    cache = _load_geo_cache()
    return {
        "status": "success",
        "counts": {
            "districts": len(cache["districts"]),
            "bus_corridors_verified": len(cache["bus_corridors"]),
            "stations_total": len(cache["stations"]),
            "stations_with_coords": sum(1 for s in cache["stations"] if s["latitude"] is not None),
            "railway_links_generated": len(cache["railway_links"]),
            "local_places_total": len(cache["local_places"]),
            "local_links_total": len(cache["local_links"]),
            "local_links_schematic": sum(1 for l in cache["local_links"] if l["display_permission"] == "render_schematic_only_if_labelled"),
        },
        "districts": cache["districts"],
        "district_boundaries": cache.get("district_boundaries", []),
        "bus_corridors": cache["bus_corridors"],
        "stations": cache["stations"],
        "railway_links": cache["railway_links"],
        "local_places": cache["local_places"],
        "local_links": cache["local_links"],
    }


@router.get("/bus-corridors")
def get_bus_corridors():
    cache = _load_geo_cache()
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": c["coordinates"]},
                "properties": {
                    "Edge_ID": c["edge_id"],
                    "From_District": c["from_district"],
                    "To_District": c["to_district"],
                    "Operational_Distance_KM": c["operational_distance_km"],
                    "Extracted_Path_Length_KM": c["extracted_length_km"],
                    "Verification_Status": c["verification_status"],
                    "Geometry_Category": c["geometry_category"],
                },
            }
            for c in cache["bus_corridors"]
        ],
    }


@router.get("/railway-links")
def get_railway_links():
    cache = _load_geo_cache()
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": r["coordinates"]},
                "properties": {
                    "RLINK_ID": r["rlink_id"],
                    "Origin_Station": r["origin_station"],
                    "Origin_District": r["origin_district"],
                    "Destination_Station": r["destination_station"],
                    "Destination_District": r["destination_district"],
                    "Operational_Distance_KM": r["operational_distance_km"],
                    "Path_Length_KM": r["path_length_km"],
                    "Verification_Status": r["verification_status"],
                    "Geometry_Category": r["geometry_category"],
                },
            }
            for r in cache["railway_links"]
        ],
    }


@router.post("/route-geometry")
def resolve_route_geometry(req: RouteGeometryRequest):
    cache = _load_geo_cache()
    dist_map = {d["name"].casefold(): d for d in cache["districts"]}
    stn_map = {}
    for s in cache["stations"]:
        stn_map[s["name"].casefold()] = s
        if s.get("canonical_name"):
            stn_map[s.get("canonical_name").casefold()] = s

    local_place_map = {}
    for lp in cache["local_places"]:
        local_place_map[lp["name"].casefold()] = lp
        if lp.get("canonical_name"):
            local_place_map[lp.get("canonical_name").casefold()] = lp

    bus_corridor_map = cache["bus_corridor_by_edge"]
    rail_link_map = cache["railway_link_by_id"]
    bus_route_lookup = cache["bus_route_lookup"]
    train_hop_lookup = cache["train_hop_lookup"]
    local_link_lookup = cache["local_link_lookup"]

    enriched_legs = []
    tot_verified_km = 0.0
    tot_provisional_km = 0.0
    tot_schematic_km = 0.0
    tot_missing_count = 0

    for idx, leg in enumerate(req.legs):
        mode = leg.mode.lower()
        orig = leg.origin.strip()
        dest = leg.destination.strip()
        segments = []

        resolved_stops = []

        if mode == "bus":
            lookup_key = (orig.casefold(), dest.casefold())
            route_info = bus_route_lookup.get(lookup_key)
            edge_ids = []
            if route_info and route_info.get("District_Edge_IDs"):
                edge_ids = [e.strip() for e in route_info["District_Edge_IDs"].split(";") if e.strip()]

            if edge_ids:
                for eid in edge_ids:
                    if eid in bus_corridor_map:
                        corr = bus_corridor_map[eid]
                        coords = corr["coordinates"]
                        # Check direction
                        if orig.casefold() == corr["to_district"].casefold():
                            coords = list(reversed(coords))
                        lkm = corr["extracted_length_km"]
                        tot_verified_km += lkm
                        segments.append({
                            "segment_id": eid,
                            "segment_type": "verified_bus_corridor",
                            "geometry_status": "verified_geometry",
                            "verification_status": "verified_osm_road_path",
                            "coordinates": coords,
                            "length_km": lkm,
                            "notes": f"High-fidelity OSM road path ({eid}: {corr['from_district']} <-> {corr['to_district']}).",
                        })
                    else:
                        # Provisional anchor line
                        u_d = dist_map.get(orig.casefold())
                        v_d = dist_map.get(dest.casefold())
                        if u_d and v_d and u_d["latitude"] and v_d["latitude"]:
                            coords = [[u_d["longitude"], u_d["latitude"]], [v_d["longitude"], v_d["latitude"]]]
                            tot_provisional_km += 50.0  # nominal
                            segments.append({
                                "segment_id": eid,
                                "segment_type": "provisional_anchor_corridor",
                                "geometry_status": "provisional_anchor",
                                "verification_status": "provisional_highway_reference",
                                "coordinates": coords,
                                "length_km": 0.0,
                                "notes": f"Provisional road anchor edge {eid}. Detailed OSM centerline pending.",
                            })
            else:
                # Direct centroid connection if no edge IDs found
                u_d = dist_map.get(orig.casefold())
                v_d = dist_map.get(dest.casefold())
                if u_d and v_d and u_d["latitude"] and v_d["latitude"]:
                    coords = [[u_d["longitude"], u_d["latitude"]], [v_d["longitude"], v_d["latitude"]]]
                    tot_provisional_km += 50.0
                    segments.append({
                        "segment_id": f"ANCH_{orig}_{dest}",
                        "segment_type": "provisional_district_anchor",
                        "geometry_status": "provisional_anchor",
                        "verification_status": "provisional_highway_reference",
                        "coordinates": coords,
                        "length_km": 0.0,
                        "notes": "District centroid reference connection.",
                    })

            # Resolve bus route stops
            bus_points = []
            if leg.path and len(leg.path) >= 2:
                bus_points = leg.path
            elif edge_ids:
                seq = [orig]
                for eid in edge_ids:
                    if eid in bus_corridor_map:
                        corr = bus_corridor_map[eid]
                        nxt = corr["to_district"] if corr["from_district"].casefold() == seq[-1].casefold() else corr["from_district"]
                        if nxt.casefold() != seq[-1].casefold():
                            seq.append(nxt)
                bus_points = seq if len(seq) >= 2 else [orig, dest]
            else:
                bus_points = [orig, dest]

            for i, p_name in enumerate(bus_points):
                clean_p = re.sub(r'\(.*?\)', '', p_name).strip() or p_name
                d_ent = dist_map.get(clean_p.casefold())
                lat = d_ent.get("latitude") if d_ent else None
                lon = d_ent.get("longitude") if d_ent else None
                resolved_stops.append({
                    "station": clean_p,
                    "name": clean_p,
                    "district": clean_p,
                    "stop_order": i + 1,
                    "stop_number": i + 1,
                    "arrival_time": "",
                    "departure_time": "",
                    "halt_minutes": 0,
                    "latitude": lat,
                    "longitude": lon,
                    "has_coordinates": bool(lat is not None and lon is not None),
                    "verification_status": d_ent.get("verification_status", "verified_district_centroid") if d_ent else "provisional",
                    "stop_type": "origin" if i == 0 else ("destination" if i == len(bus_points) - 1 else "intermediate"),
                })

        elif mode == "train":
            # Train stops resolution
            train_stops_data = leg.stops
            if len(train_stops_data) < 2 and leg.service:
                m_no = re.search(r'\b(\d{3,4})\b', leg.service)
                if m_no:
                    t_no = m_no.group(1)
                    raw_sched_stops = cache.get("train_stops_by_train", {}).get(t_no, [])
                    st_names = [s["Station"].strip().casefold() for s in raw_sched_stops]
                    o_c = orig.casefold()
                    d_c = dest.casefold()
                    if o_c in st_names and d_c in st_names:
                        i1 = st_names.index(o_c)
                        i2 = st_names.index(d_c)
                        if i1 < i2:
                            train_stops_data = [{
                                "station": s["Station"],
                                "district_name": s["District"],
                                "arrival_time": s["Arrival"],
                                "departure_time": s["Departure"],
                                "stop_order": int(s["Stop_Order"]),
                            } for s in raw_sched_stops[i1:i2+1]]

            for i, st in enumerate(train_stops_data):
                st_name = st.get("station", "").strip()
                dist_name = st.get("district_name") or st.get("district") or ""
                matched = stn_map.get(st_name.casefold())
                if not matched and dist_name:
                    matched = location_by_name_cat.get((st_name.casefold(), "train_station", dist_name.casefold()))
                if not matched:
                    matched = location_by_name_cat.get((st_name.casefold(), "train_station"))

                lat = matched.get("latitude") if matched else None
                lon = matched.get("longitude") if matched else None
                actual_dist = (matched.get("district") if matched else dist_name) or dist_name

                arr = str(st.get("arrival_time") or "").strip()
                dep = str(st.get("departure_time") or "").strip()

                resolved_stops.append({
                    "station": st_name,
                    "name": st_name,
                    "district": actual_dist,
                    "stop_order": st.get("stop_order", i + 1),
                    "stop_number": i + 1,
                    "arrival_time": arr,
                    "departure_time": dep,
                    "halt_minutes": st.get("halt_minutes", 0),
                    "latitude": lat,
                    "longitude": lon,
                    "has_coordinates": bool(lat is not None and lon is not None),
                    "verification_status": matched.get("verification_status", "missing_coordinates") if matched else "missing_coordinates",
                    "stop_type": "origin" if i == 0 else ("destination" if i == len(train_stops_data) - 1 else "intermediate"),
                })

            # Train consecutive stops geometry
            stops = train_stops_data
            if len(stops) >= 2:
                for i in range(len(stops) - 1):
                    s1 = stops[i].get("station", "").strip()
                    s2 = stops[i+1].get("station", "").strip()
                    hop_key = (s1.casefold(), s2.casefold())
                    hop_info = train_hop_lookup.get(hop_key)
                    rlink_id = hop_info.get("Railway_Link_IDs", "") if hop_info else ""
                    
                    if rlink_id and rlink_id in rail_link_map:
                        rlink = rail_link_map[rlink_id]
                        coords = rlink["coordinates"]
                        if s1.casefold() == rlink["destination_station"].casefold():
                            coords = list(reversed(coords))
                        lkm = rlink["path_length_km"]
                        tot_verified_km += lkm
                        segments.append({
                            "segment_id": rlink_id,
                            "segment_type": "verified_railway_track",
                            "geometry_status": "verified_geometry",
                            "verification_status": "verified_osm_mainline_track",
                            "coordinates": coords,
                            "length_km": lkm,
                            "notes": f"Mainline physical railway track ({rlink_id}: {s1} <-> {s2}).",
                        })
                    else:
                        stn1 = stn_map.get(s1.casefold())
                        stn2 = stn_map.get(s2.casefold())
                        if stn1 and stn2 and stn1["latitude"] and stn2["latitude"]:
                            coords = [[stn1["longitude"], stn1["latitude"]], [stn2["longitude"], stn2["latitude"]]]
                            tot_provisional_km += 10.0
                            segments.append({
                                "segment_id": f"CHORD_{s1}_{s2}",
                                "segment_type": "railway_junction_chord",
                                "geometry_status": "manual_review_required",
                                "verification_status": "pending_manual_verification",
                                "coordinates": coords,
                                "length_km": 0.0,
                                "notes": f"Track connection {s1} <-> {s2} traverses complex yard; manual chord review required.",
                            })
                        else:
                            tot_missing_count += 1
                            segments.append({
                                "segment_id": f"MISSING_{s1}_{s2}",
                                "segment_type": "missing_railway_geometry",
                                "geometry_status": "missing_geometry",
                                "verification_status": "missing_coordinates",
                                "coordinates": [],
                                "length_km": 0.0,
                                "notes": f"One or both stations lack coordinates in current OSM extract ({s1} <-> {s2}).",
                            })
            else:
                # Fallback to origin/dest stations
                stn1 = stn_map.get(orig.casefold())
                stn2 = stn_map.get(dest.casefold())
                if stn1 and stn2 and stn1["latitude"] and stn2["latitude"]:
                    coords = [[stn1["longitude"], stn1["latitude"]], [stn2["longitude"], stn2["latitude"]]]
                    segments.append({
                        "segment_id": f"TRAIN_{orig}_{dest}",
                        "segment_type": "train_corridor_overview",
                        "geometry_status": "manual_review_required",
                        "verification_status": "pending_manual_verification",
                        "coordinates": coords,
                        "length_km": 0.0,
                        "notes": f"Direct station reference {orig} <-> {dest}.",
                    })

        elif mode == "local":
            p1 = local_place_map.get(orig.casefold())
            p2 = local_place_map.get(dest.casefold())
            for i, (name, ent, st_type) in enumerate([(orig, p1, "origin"), (dest, p2, "destination")]):
                lat = ent.get("latitude") if ent else None
                lon = ent.get("longitude") if ent else None
                resolved_stops.append({
                    "station": name,
                    "name": name,
                    "district": ent.get("district", "") if ent else "",
                    "stop_order": i + 1,
                    "stop_number": i + 1,
                    "arrival_time": "",
                    "departure_time": "",
                    "halt_minutes": 0,
                    "latitude": lat,
                    "longitude": lon,
                    "has_coordinates": bool(lat is not None and lon is not None),
                    "verification_status": ent.get("verification_status", "matched_local_place") if ent else "missing_coordinates",
                    "stop_type": st_type,
                })

            link_key = (orig.casefold(), dest.casefold())
            llink = local_link_lookup.get(link_key)
            if llink and llink["origin_lat"] and llink["destination_lat"]:
                coords = [
                    [llink["origin_lon"], llink["origin_lat"]],
                    [llink["destination_lon"], llink["destination_lat"]],
                ]
                tot_schematic_km += llink["distance_km"]
                segments.append({
                    "segment_id": llink["local_link_id"],
                    "segment_type": "local_schematic_connector",
                    "geometry_status": "schematic_connector",
                    "verification_status": "schematic_connector_only",
                    "coordinates": coords,
                    "length_km": llink["distance_km"],
                    "notes": llink["safety_disclaimer"],
                })
            else:
                if p1 and p2 and p1["latitude"] and p2["latitude"]:
                    coords = [
                        [p1["longitude"], p1["latitude"]],
                        [p2["longitude"], p2["latitude"]],
                    ]
                    segments.append({
                        "segment_id": f"LOCAL_{orig}_{dest}",
                        "segment_type": "local_schematic_connector",
                        "geometry_status": "schematic_connector",
                        "verification_status": "schematic_connector_only",
                        "coordinates": coords,
                        "length_km": 0.0,
                        "notes": "SCHEMATIC CONNECTOR ONLY: Straight-line between local places. NOT A VERIFIED ROAD ROUTE.",
                    })
                else:
                    tot_missing_count += 1
                    segments.append({
                        "segment_id": f"LOCAL_{orig}_{dest}",
                        "segment_type": "missing_local_geometry",
                        "geometry_status": "missing_geometry",
                        "verification_status": "missing_coordinates",
                        "coordinates": [],
                        "length_km": 0.0,
                        "notes": "Local feeder endpoint coordinates absent.",
                    })

        elif mode in ["walk", "transfer"]:
            u_ent = stn_map.get(orig.casefold()) or dist_map.get(orig.casefold())
            v_ent = stn_map.get(dest.casefold()) or dist_map.get(dest.casefold())
            for i, (name, ent, st_type) in enumerate([(orig, u_ent, "origin"), (dest, v_ent, "destination")]):
                lat = ent.get("latitude") if ent else None
                lon = ent.get("longitude") if ent else None
                resolved_stops.append({
                    "station": name,
                    "name": name,
                    "district": ent.get("district", "") if ent else "",
                    "stop_order": i + 1,
                    "stop_number": i + 1,
                    "arrival_time": "",
                    "departure_time": "",
                    "halt_minutes": 0,
                    "latitude": lat,
                    "longitude": lon,
                    "has_coordinates": bool(lat is not None and lon is not None),
                    "verification_status": ent.get("verification_status", "verified_hub") if ent else "missing_coordinates",
                    "stop_type": st_type,
                })

            if u_ent and v_ent and u_ent["latitude"] and v_ent["latitude"]:
                coords = [[u_ent["longitude"], u_ent["latitude"]], [v_ent["longitude"], v_ent["latitude"]]]
                segments.append({
                    "segment_id": f"TRANSFER_{orig}_{dest}",
                    "segment_type": "transfer_connector",
                    "geometry_status": "schematic_connector",
                    "verification_status": "transfer_connection",
                    "coordinates": coords,
                    "length_km": 0.0,
                    "notes": f"Intermodal transfer walk between {orig} and {dest}.",
                })

        enriched_legs.append({
            "leg_index": idx,
            "mode": mode,
            "origin": orig,
            "destination": dest,
            "service": leg.service,
            "stops": resolved_stops,
            "geometry_segments": segments,
        })

    all_stops = []
    for l in enriched_legs:
        for s in l.get("stops", []):
            s_copy = dict(s)
            s_copy["leg_index"] = l["leg_index"]
            s_copy["mode"] = l["mode"]
            s_copy["service"] = l.get("service", "")
            all_stops.append(s_copy)

    return {
        "status": "success",
        "summary": {
            "verified_geometry_km": round(tot_verified_km, 2),
            "provisional_anchor_km": round(tot_provisional_km, 2),
            "schematic_connector_km": round(tot_schematic_km, 2),
            "missing_geometry_segments_count": tot_missing_count,
            "total_stops_count": len(all_stops),
            "intermediate_stops_count": sum(1 for s in all_stops if s.get("stop_type") == "intermediate"),
            "missing_coordinates_stops_count": sum(1 for s in all_stops if not s.get("has_coordinates")),
        },
        "legs": enriched_legs,
        "all_stops": all_stops,
        "legs": enriched_legs,
        "summary": {
            "verified_geometry_km": round(tot_verified_km, 2),
            "provisional_anchor_km": round(tot_provisional_km, 2),
            "schematic_connector_km": round(tot_schematic_km, 2),
            "missing_geometry_segments_count": tot_missing_count,
        },
    }
