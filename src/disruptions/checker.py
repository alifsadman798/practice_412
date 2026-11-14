import logging
import re
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import DisruptionAffectedSegment, TransportDisruption
from src.disruptions.schemas import DisruptionAlertPayload
from src.shared.models import Mode, RouteKind, RouteOption
from src.train.corridors import train_traverses_district

logger = logging.getLogger(__name__)


def _normalize_name(val: str | None) -> str:
    if not val:
        return ""
    v = val.strip().casefold()
    for drop in ("railway station", "station", "junction", "halt", "bus terminal", "terminal", "stand"):
        v = v.replace(drop, "").strip()
    return v


def _leg_matches_bus_segment(leg, path_districts: list[str], seg: DisruptionAffectedSegment, loc_name: str) -> bool:
    """Checks whether a BUS leg traverses the affected road segment."""
    f_seg = _normalize_name(seg.from_point)
    t_seg = _normalize_name(seg.to_point)
    seg_id = (seg.affected_segment_id or "").strip().casefold()
    seg_desc = (seg.segment_description or "").strip().casefold()
    loc = _normalize_name(loc_name)

    path_norm = [_normalize_name(p) for p in path_districts]

    # 1. If segment specifies an explicit district edge pair: A <-> B
    if f_seg and t_seg and f_seg != t_seg:
        for idx in range(len(path_norm) - 1):
            p1, p2 = path_norm[idx], path_norm[idx + 1]
            if (p1 == f_seg and p2 == t_seg) or (p1 == t_seg and p2 == f_seg):
                return True
        # Also check leg origin/destination
        leg_o = _normalize_name(leg.origin)
        leg_d = _normalize_name(leg.destination)
        if (leg_o == f_seg and leg_d == t_seg) or (leg_o == t_seg and leg_d == f_seg):
            return True

    # 2. Check affected_segment_id (e.g. edge:Dhaka-Cumilla or edge:12)
    if "edge:" in seg_id:
        pair_part = seg_id.replace("edge:", "").strip()
        parts = [p.strip() for p in pair_part.split("-")]
        if len(parts) == 2:
            p_a, p_b = _normalize_name(parts[0]), _normalize_name(parts[1])
            for idx in range(len(path_norm) - 1):
                p1, p2 = path_norm[idx], path_norm[idx + 1]
                if (p1 == p_a and p2 == p_b) or (p1 == p_b and p2 == p_a):
                    return True

    # 3. If segment is a road section within a specific district (e.g. "Cumilla Bypass" or "Cumilla Highway")
    # Must check that the bus route actually enters/traverses that district
    if loc and loc in path_norm:
        if not f_seg and not t_seg:
            return True
        if (f_seg and f_seg in path_norm) or (t_seg and t_seg in path_norm):
            return True

    return False


def _leg_matches_train_segment(leg, seg: DisruptionAffectedSegment, loc_name: str) -> bool:
    """Checks whether a TRAIN leg traverses the affected railway station or rail corridor."""
    f_seg = _normalize_name(seg.from_point)
    t_seg = _normalize_name(seg.to_point)
    seg_id = (seg.affected_segment_id or "").strip().casefold()
    seg_desc = (seg.segment_description or "").strip().casefold()
    loc = _normalize_name(loc_name)

    # Collect all stations and districts along this train leg
    leg_stations: list[str] = []
    leg_districts: list[str] = []

    if getattr(leg, "stops", None):
        for s in leg.stops:
            if getattr(s, "station", None):
                leg_stations.append(_normalize_name(s.station))
            if getattr(s, "district_name", None):
                leg_districts.append(_normalize_name(s.district_name))

    leg_stations.append(_normalize_name(leg.origin))
    leg_stations.append(_normalize_name(leg.destination))

    all_stations_set = set(leg_stations)
    all_districts_set = set(leg_districts)

    # 1. Segment specifies station pair or rail corridor
    if f_seg and t_seg and f_seg != t_seg:
        if (f_seg in all_stations_set or f_seg in all_districts_set) and (t_seg in all_stations_set or t_seg in all_districts_set):
            return True

    # 2. Segment specifies single station (e.g. "station:Cumilla" or from_point="Cumilla Station")
    target_station = f_seg or t_seg
    if "station:" in seg_id:
        target_station = _normalize_name(seg_id.replace("station:", ""))

    if target_station and target_station in all_stations_set:
        return True

    # 3. Check location district for scheduled stoppage
    if loc and (loc in all_districts_set or loc in all_stations_set):
        return True

    # 4. Check physical railway corridor transit (even if train runs non-stop through the district)
    train_service_str = getattr(leg, "service", "") or ""
    train_no_match = re.search(r"\((\d+[a-zA-Z]?)\)", train_service_str)
    train_no = train_no_match.group(1) if train_no_match else ""

    leg_origin = getattr(leg, "origin", "") or ""
    leg_dest = getattr(leg, "destination", "") or ""

    target_district = loc_name
    if not target_district and "corridor:" in seg_id:
        target_district = seg_id.replace("corridor:", "").split("-")[0]

    if target_district:
        traverses, _ = train_traverses_district(
            train_no=train_no,
            target_district=target_district,
            from_district=leg_origin,
            to_district=leg_dest,
            scheduled_stop_districts=all_districts_set,
        )
        if traverses:
            return True

    return False


def check_and_attach_disruptions(routes: list[RouteOption], session: Session) -> list[RouteOption]:
    """
    Inspects generated routes against currently ACTIVE transport disruptions in PostgreSQL.
    Attaches alert metadata directly to matching legs and routes WITHOUT modifying
    underlying route paths, fares, journey durations, schedules, or comparisons.
    """
    if not routes:
        return routes

    try:
        active_disruptions = list(
            session.scalars(
                select(TransportDisruption)
                .where(
                    TransportDisruption.status == "ACTIVE",
                    TransportDisruption.deleted_at == None,
                )
                .order_by(TransportDisruption.created_at.desc())
            )
        )
    except Exception as err:
        logger.warning(f"Could not query active disruptions: {err}")
        return routes

    if not active_disruptions:
        for route in routes:
            route.is_affected = False
            route.disruption_alerts = []
            for leg in route.legs:
                leg.is_affected = False
                leg.disruption_alerts = []
        return routes

    for route in routes:
        route_alerts: list[dict] = []
        route_is_affected = False

        for leg in route.legs:
            leg_alerts: list[dict] = []
            leg_is_affected = False
            leg_mode = leg.mode

            for disruption in active_disruptions:
                disp_mode = disruption.transport_mode.upper()
                # Check transport mode compatibility
                is_bus_eligible = (disp_mode in ("BUS", "BOTH")) and (leg_mode == Mode.BUS)
                is_train_eligible = (disp_mode in ("TRAIN", "BOTH")) and (leg_mode == Mode.TRAIN)

                if not is_bus_eligible and not is_train_eligible:
                    continue

                matched = False
                matched_seg_desc = disruption.location_name

                # Check affected segments attached to this disruption
                segments = disruption.affected_segments or []
                if segments:
                    for seg in segments:
                        seg_mode = seg.transport_mode.upper()
                        if is_bus_eligible and seg_mode in ("BUS", "BOTH"):
                            if _leg_matches_bus_segment(leg, route.path, seg, disruption.location_name):
                                matched = True
                                matched_seg_desc = seg.segment_description or seg.affected_segment_id
                                break
                        elif is_train_eligible and seg_mode in ("TRAIN", "BOTH"):
                            if _leg_matches_train_segment(leg, seg, disruption.location_name):
                                matched = True
                                matched_seg_desc = seg.segment_description or seg.affected_segment_id
                                break
                else:
                    # Fallback: check location name if no fine-grained segments configured
                    if is_bus_eligible and _leg_matches_bus_segment(leg, route.path, DisruptionAffectedSegment(transport_mode="BUS", affected_segment_id=disruption.location_name, segment_description=disruption.location_name), disruption.location_name):
                        matched = True
                    elif is_train_eligible and _leg_matches_train_segment(leg, DisruptionAffectedSegment(transport_mode="TRAIN", affected_segment_id=disruption.location_name, segment_description=disruption.location_name), disruption.location_name):
                        matched = True

                if matched:
                    leg_is_affected = True
                    route_is_affected = True

                    alert_payload = DisruptionAlertPayload(
                        disruption_id=disruption.disruption_id,
                        location=disruption.location_name,
                        transport_mode=disp_mode,
                        cause=disruption.cause,
                        severity=disruption.severity,
                        status=disruption.status,
                        title=disruption.title,
                        message=disruption.alert_message,
                        affected_segment=matched_seg_desc,
                        estimated_end_time=disruption.estimated_end_time,
                        source_name=disruption.source_name,
                        source_url=disruption.source_url,
                    ).model_dump(mode="json")

                    if not any(a["disruption_id"] == disruption.disruption_id for a in leg_alerts):
                        leg_alerts.append(alert_payload)
                    if not any(a["disruption_id"] == disruption.disruption_id for a in route_alerts):
                        route_alerts.append(alert_payload)

            leg.is_affected = leg_is_affected
            leg.disruption_alerts = leg_alerts

        route.is_affected = route_is_affected
        route.disruption_alerts = route_alerts

        # If a critical or full suspension disruption matches, append an advisory warning to route.warnings
        for a in route_alerts:
            cause_code = a.get("cause", "").upper()
            sev = a.get("severity", "").upper()
            if sev == "CRITICAL" or cause_code in ("TRAIN_SUSPENSION", "BUS_SUSPENSION", "ROAD_CLOSURE"):
                warning_msg = f"DISRUPTION NOTICE: {a.get('title')}. {a.get('message')}"
                if warning_msg not in route.warnings:
                    route.warnings.append(warning_msg)

    return routes
