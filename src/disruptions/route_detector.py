from collections import defaultdict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.bus.dijkstra import shortest_path
from src.database.models import (
    BusSchedule,
    DistrictEdge,
    TrainService,
    TrainStop,
)
from src.disruptions.extractor import ExtractedIncident
from src.disruptions.schemas import AffectedRouteSummary, AffectedSegmentInput
from src.train.corridors import (
    get_corridors_crossing_district,
    get_train_corridor_name,
    train_traverses_district,
)


def detect_affected_segments_and_routes(
    session: Session,
    incident: ExtractedIncident,
) -> tuple[list[AffectedSegmentInput], list[AffectedRouteSummary]]:
    """
    Given an extracted incident, automatically identifies:
    1. The corresponding road or railway network segments in the database.
    2. All existing transport routes whose actual paths traverse those segments.
    """
    if not incident.location or not incident.transport_mode or not incident.is_confident:
        return [], []

    loc_name = incident.location.strip()
    loc_lower = loc_name.lower()
    mode = incident.transport_mode  # "BUS", "TRAIN", "BOTH"

    identified_segments: list[AffectedSegmentInput] = []
    affected_routes: list[AffectedRouteSummary] = []
    seen_routes: set[tuple[str, str, str, str]] = set()

    # -------------------------------------------------------------
    # 1. RAILWAY NETWORK DETECTION (For TRAIN or BOTH)
    # -------------------------------------------------------------
    if mode in ("TRAIN", "BOTH"):
        # Find all train stations located in or named after this location/district
        matching_stops = session.execute(
            select(TrainStop.station, TrainStop.district_name)
            .where(
                (func.lower(TrainStop.district_name) == loc_lower)
                | (func.lower(TrainStop.station) == loc_lower)
                | (func.lower(TrainStop.station).like(f"%{loc_lower}%"))
            )
            .distinct()
        ).all()

        target_stations = {st for st, _ in matching_stops}
        if not target_stations:
            target_stations.add(loc_name)

        # Build segment records for rail stations
        for st in sorted(target_stations):
            dist_label = loc_name
            identified_segments.append(
                AffectedSegmentInput(
                    transport_mode="TRAIN",
                    affected_segment_id=f"station:{st}",
                    segment_description=f"{st} Railway Station ({dist_label})",
                    from_point=st,
                    to_point=None,
                )
            )

        # Also add the physical railway corridor track section for this district
        crossing_corridors = get_corridors_crossing_district(loc_name)
        corridor_desc = crossing_corridors[0] if crossing_corridors else f"{loc_name} Railway Line"
        track_seg_id = f"corridor:{loc_name}-rail-track"
        if not any(s.affected_segment_id == track_seg_id for s in identified_segments):
            identified_segments.append(
                AffectedSegmentInput(
                    transport_mode="TRAIN",
                    affected_segment_id=track_seg_id,
                    segment_description=f"{loc_name} Railway Track & Section ({corridor_desc})",
                    from_point=loc_name,
                    to_point=None,
                )
            )

        # Inspect all train services and their stop sequences
        train_services = session.scalars(select(TrainService).order_by(TrainService.train_no)).all()
        all_train_stops = session.scalars(
            select(TrainStop).order_by(TrainStop.train_no, TrainStop.stop_order)
        ).all()

        stops_by_train = defaultdict(list)
        for ts in all_train_stops:
            stops_by_train[ts.train_no].append(ts)

        # Separate Group A (Scheduled Stops) and Group B (Non-Stop Transit)
        group_a_stopping: list[AffectedRouteSummary] = []
        group_b_transit: list[AffectedRouteSummary] = []

        for srv in train_services:
            stops = stops_by_train.get(srv.train_no, [])
            stop_districts = {s.district_name for s in stops}

            matched_station_name = None
            for s in stops:
                if (
                    s.station in target_stations
                    or s.district_name.lower() == loc_lower
                    or loc_lower in s.station.lower()
                ):
                    matched_station_name = f"{s.station} Station"
                    break

            traverses, match_type = train_traverses_district(
                train_no=srv.train_no,
                target_district=loc_name,
                from_district=srv.from_district,
                to_district=srv.to_district,
                scheduled_stop_districts=stop_districts,
            )

            key = ("TRAIN", srv.train_name, srv.from_district, srv.to_district)
            if key in seen_routes:
                continue

            if matched_station_name or match_type == "STOP":
                seen_routes.add(key)
                st_label = matched_station_name or f"{loc_name} Station"
                group_a_stopping.append(
                    AffectedRouteSummary(
                        mode="TRAIN",
                        service=f"{srv.train_name} ({srv.train_no})",
                        origin=srv.from_district,
                        destination=srv.to_district,
                        matched_section=f"{st_label} (Scheduled Stop)",
                    )
                )
            elif match_type == "TRANSIT":
                seen_routes.add(key)
                c_name = get_train_corridor_name(srv.train_no, srv.from_district, srv.to_district) or f"{loc_name} Section"
                group_b_transit.append(
                    AffectedRouteSummary(
                        mode="TRAIN",
                        service=f"{srv.train_name} ({srv.train_no})",
                        origin=srv.from_district,
                        destination=srv.to_district,
                        matched_section=f"{loc_name} Railway Section ({c_name} - Non-Stop Transit)",
                    )
                )

        # Combine both groups without duplicate train records (Group A stopping first, then Group B transit)
        affected_routes.extend(group_a_stopping)
        affected_routes.extend(group_b_transit)

    # -------------------------------------------------------------
    # 2. ROAD NETWORK DETECTION (For BUS or BOTH)
    # -------------------------------------------------------------
    if mode in ("BUS", "BOTH"):
        # Query road network edges
        edges = list(session.scalars(select(DistrictEdge)).all())

        matching_edges: list[DistrictEdge] = []

        # If a specific highway corridor pair was identified (e.g. Dhaka-Cumilla, Dhaka-Chittagong)
        if incident.corridor_endpoints:
            p1, p2 = incident.corridor_endpoints
            p1_l, p2_l = p1.lower(), p2.lower()
            for e in edges:
                f_l, t_l = e.from_district.lower(), e.to_district.lower()
                if (f_l == p1_l and t_l == p2_l) or (f_l == p2_l and t_l == p1_l):
                    matching_edges.append(e)

        # If no specific corridor endpoint matched or also include local edges connecting this district
        if not matching_edges:
            for e in edges:
                if e.from_district.lower() == loc_lower or e.to_district.lower() == loc_lower:
                    matching_edges.append(e)

        # Build segment records for road
        for e in matching_edges:
            seg_id = f"edge:{e.from_district}-{e.to_district}"
            desc = f"{e.from_district} ↔ {e.to_district} Highway"
            if not any(s.affected_segment_id == seg_id for s in identified_segments):
                identified_segments.append(
                    AffectedSegmentInput(
                        transport_mode="BUS",
                        affected_segment_id=seg_id,
                        segment_description=desc,
                        from_point=e.from_district,
                        to_point=e.to_district,
                    )
                )

        # Inspect all scheduled bus routes and their Dijkstra paths
        bus_pairs = session.execute(
            select(BusSchedule.from_district, BusSchedule.to_district, BusSchedule.transport_name)
            .distinct()
        ).all()

        # Cache paths by (orig, dest)
        path_cache = {}
        for from_d, to_d, oper in bus_pairs:
            pair = (from_d, to_d)
            if pair not in path_cache:
                path_data = shortest_path(edges, from_d, to_d)
                path_cache[pair] = path_data[0] if path_data else None

            path = path_cache[pair]
            if not path or len(path) < 2:
                continue

            # Check if this bus path traverses the affected road section
            path_lower = [p.lower() for p in path]
            matched_edge_desc = None

            # 1. Check matching edges
            for me in matching_edges:
                me_from, me_to = me.from_district.lower(), me.to_district.lower()
                for idx in range(len(path_lower) - 1):
                    p_a, p_b = path_lower[idx], path_lower[idx + 1]
                    if (p_a == me_from and p_b == me_to) or (p_a == me_to and p_b == me_from):
                        matched_edge_desc = f"{me.from_district}–{me.to_district} Section"
                        break
                if matched_edge_desc:
                    break

            # 2. Check if path enters the affected district
            if not matched_edge_desc and loc_lower in path_lower:
                matched_edge_desc = f"{loc_name} Road Corridor"

            if matched_edge_desc:
                key = ("BUS", f"Bus via {loc_name}", from_d, to_d)
                if key not in seen_routes:
                    seen_routes.add(key)
                    oper_label = oper if oper else "Inter-District Bus"
                    affected_routes.append(
                        AffectedRouteSummary(
                            mode="BUS",
                            service=f"{oper_label} ({from_d} ➔ {to_d})",
                            origin=from_d,
                            destination=to_d,
                            matched_section=matched_edge_desc,
                        )
                    )

    return identified_segments, affected_routes
