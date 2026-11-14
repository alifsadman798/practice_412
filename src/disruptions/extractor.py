import re
from typing import Literal

from src.shared.constants import BANGLADESH_64_DISTRICTS


# Regex & keyword maps for deterministic extraction
RAILWAY_KEYWORDS = {
    "train", "trains", "railway", "rail", "intercity", "mail train", "express train",
    "locomotive", "rail track", "railway track", "rail line", "railway line",
    "station", "junction", "derail", "derailed", "derailment", "bogey", "compartment",
}

ROAD_KEYWORDS = {
    "bus", "buses", "road", "highway", "expressway", "truck", "coach", "traffic",
    "toll plaza", "bypass", "intersection", "pavement", "culvert", "flyover", "bridge",
}

BOTH_INDICATORS = {
    "both road and rail", "both road and railway", "road and railway", "railway and road",
    "bus and train", "train and bus", "both bus and train", "both train and bus",
    "transport across", "all transport", "all vehicular",
}

# Incident Type / Cause detection patterns
CAUSE_PATTERNS = [
    (r"\b(derail|derailed|derailment|railway accident|train accident|rail accident|train crash|train collision)\b", "Railway Accident", "RAILWAY_ACCIDENT"),
    (r"\b(road accident|bus crash|bus accident|vehicle collision|truck accident|overturned|car crash)\b", "Road Accident", "ROAD_ACCIDENT"),
    (r"\b(accident|collision|crash|crashed|head-on)\b", "Accident", "ROAD_ACCIDENT"),
    (r"\b(protest|protesters|strike|hartal|blockade|blockaded|demonstration|rally|human chain)\b", "Protest / Road Blockage", "PROTEST"),
    (r"\b(flood|flooded|flooding|flash flood|inundated|submerged|waterlogging|waterlogged)\b", "Flooding / Natural Disaster", "FLOOD"),
    (r"\b(suspend|suspended|suspension|shutdown|halted|stopped|cancelled|interrupted)\b", "Service Suspension", "TRAIN_SUSPENSION"),
    (r"\b(road closure|closed|closure|traffic halted|highway blocked|road blocked)\b", "Road Closure", "ROAD_CLOSURE"),
    (r"\b(breakdown|mechanical failure|engine trouble|signal failure|track damage|obstruction)\b", "Technical Failure / Obstruction", "HEAVY_OBSTRUCTION"),
]

# Operational Impact patterns
IMPACT_PATTERNS = [
    (r"\b(suspend|suspended|suspension|stopped|halted|shut down|no movement)\b", "Service Suspended"),
    (r"\b(block|blocked|blockage|blockade|impassable|closed|shut)\b", "Movement Blocked"),
    (r"\b(severe delay|delayed|delays|disrupted|disruption|halt)\b", "Severe Delays Expected"),
    (r"\b(single line|slow|cautious|restricted|partial|diverted)\b", "Partially Disrupted"),
]

# Known highway corridor indicators in Bangladesh
CORRIDOR_INDICATORS = [
    (r"dhaka[–\-\s]+chittagong|dhaka[–\-\s]+chattogram", "Dhaka-Chittagong Highway", ("Dhaka", "Chattogram")),
    (r"dhaka[–\-\s]+cumilla|cumilla[–\-\s]+dhaka", "Dhaka-Cumilla Highway", ("Dhaka", "Cumilla")),
    (r"dhaka[–\-\s]+sylhet|sylhet[–\-\s]+dhaka", "Dhaka-Sylhet Highway", ("Dhaka", "Sylhet")),
    (r"dhaka[–\-\s]+mymensingh", "Dhaka-Mymensingh Highway", ("Dhaka", "Mymensingh")),
    (r"dhaka[–\-\s]+rajshahi", "Dhaka-Rajshahi Highway", ("Dhaka", "Rajshahi")),
    (r"dhaka[–\-\s]+khulna", "Dhaka-Khulna Highway", ("Dhaka", "Khulna")),
    (r"cumilla[–\-\s]+chittagong|cumilla[–\-\s]+chattogram", "Cumilla-Chittagong Highway", ("Cumilla", "Chattogram")),
]


class ExtractedIncident:
    def __init__(
        self,
        is_confident: bool,
        location: str | None,
        transport_mode: Literal["BUS", "TRAIN", "BOTH"] | None,
        incident_type: str,
        cause_code: str,
        operational_impact: str,
        severity: Literal["LOW", "MODERATE", "HIGH", "CRITICAL"],
        title: str,
        alert_message: str,
        matching_confidence: str = "HIGH",
        matching_status: str = "CONFIDENT MATCH",
        corridor_name: str | None = None,
        corridor_endpoints: tuple[str, str] | None = None,
        clarification_prompt: str | None = None,
    ):
        self.is_confident = is_confident
        self.location = location
        self.transport_mode = transport_mode
        self.incident_type = incident_type
        self.cause_code = cause_code
        self.operational_impact = operational_impact
        self.severity = severity
        self.title = title
        self.alert_message = alert_message
        self.matching_confidence = matching_confidence
        self.matching_status = matching_status
        self.corridor_name = corridor_name
        self.corridor_endpoints = corridor_endpoints
        self.clarification_prompt = clarification_prompt


def extract_incident_details(text: str, corrected_location: str | None = None) -> ExtractedIncident:
    """
    Deterministically parses free-text incident descriptions to extract:
    - Incident Location (city, district, station, highway)
    - Transport Mode (BUS, TRAIN, BOTH)
    - Incident Type & Code
    - Operational Impact & Severity
    - Dynamic Public Alert Message
    Identifies ambiguity and requests clarification when needed.
    Allows optional corrected_location override.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return ExtractedIncident(
            is_confident=False,
            location=corrected_location.strip() if corrected_location else None,
            transport_mode=None,
            incident_type="Unknown",
            cause_code="OTHER",
            operational_impact="Unknown",
            severity="MODERATE",
            title="Transport Disruption",
            alert_message="A transport disruption has been reported.",
            matching_confidence="LOW",
            matching_status="NEEDS CLARIFICATION",
            clarification_prompt="Incident description is empty. Please describe what happened, the location, and affected transport mode.",
        )

    lower_text = cleaned.lower()

    # 1. Location Detection
    detected_location: str | None = None
    districts_lower_map = {d.lower(): d for d in BANGLADESH_64_DISTRICTS}
    # Add common alternative spellings (English variations)
    districts_lower_map["comilla"] = "Cumilla"
    districts_lower_map["cumilla"] = "Cumilla"
    districts_lower_map["chittagong"] = "Chattogram"
    districts_lower_map["chattogram"] = "Chattogram"
    districts_lower_map["brahmanbaria"] = "Brahmanbaria"
    districts_lower_map["brahman baria"] = "Brahmanbaria"
    districts_lower_map["b.baria"] = "Brahmanbaria"
    districts_lower_map["bbaria"] = "Brahmanbaria"
    districts_lower_map["cox's bazar"] = "Cox's Bazar"
    districts_lower_map["coxs bazar"] = "Cox's Bazar"
    districts_lower_map["coxsbazar"] = "Cox's Bazar"
    districts_lower_map["barisal"] = "Barishal"
    districts_lower_map["barishal"] = "Barishal"
    districts_lower_map["jessore"] = "Jashore"
    districts_lower_map["jashore"] = "Jashore"
    districts_lower_map["bogra"] = "Bogura"
    districts_lower_map["bogura"] = "Bogura"
    districts_lower_map["dacca"] = "Dhaka"
    districts_lower_map["dhaka"] = "Dhaka"
    districts_lower_map["netrakona"] = "Netrokona"
    districts_lower_map["kishorganj"] = "Kishoreganj"
    districts_lower_map["maulvibazar"] = "Moulvibazar"
    districts_lower_map["nawabganj"] = "Chapainawabganj"

    # Add common Bengali district names
    bengali_districts = {
        "ব্রাহ্মণবাড়িয়া": "Brahmanbaria", "ব্রাহ্মণবাড়িয়া": "Brahmanbaria",
        "কুমিল্লা": "Cumilla", "চট্টগ্রাম": "Chattogram",
        "বরিশাল": "Barishal", "বগুড়া": "Bogura", "বগুড়া": "Bogura",
        "যশোর": "Jashore", "কক্সবাজার": "Cox's Bazar", "কক্স বাজার": "Cox's Bazar",
        "ঢাকা": "Dhaka", "সিলেট": "Sylhet", "রাজশাহী": "Rajshahi", "খুলনা": "Khulna",
        "ময়মনসিংহ": "Mymensingh", "ময়মনসিংহ": "Mymensingh", "রংপুর": "Rangpur",
        "ফেনী": "Feni", "নোয়াখালী": "Noakhali", "নোয়াখালী": "Noakhali",
        "চাঁদপুর": "Chandpur", "গাজীপুর": "Gazipur", "নারায়ণগঞ্জ": "Narayanganj",
        "নারায়ণগঞ্জ": "Narayanganj", "নরসিংদী": "Narsingdi", "টাঙ্গাইল": "Tangail",
        "সিরাজগঞ্জ": "Sirajganj", "নাটোর": "Natore", "পাবনা": "Pabna",
        "হবিগঞ্জ": "Habiganj", "মৌলভীবাজার": "Moulvibazar", "সুনামগঞ্জ": "Sunamganj",
        "জামালপুর": "Jamalpur", "নেত্রকোনা": "Netrokona", "নেত্রকোণা": "Netrokona",
        "কিশোরগঞ্জ": "Kishoreganj", "কুষ্টিয়া": "Kushtia", "কুষ্টিয়া": "Kushtia",
        "ঝিনাইদহ": "Jhenaidah", "চুয়াডাঙ্গা": "Chuadanga", "চুয়াডাঙ্গা": "Chuadanga",
        "দিনাজপুর": "Dinajpur", "পঞ্চগড়": "Panchagarh", "পঞ্চগড়": "Panchagarh",
        "ঠাকুরগাঁও": "Thakurgaon", "নীলফামারী": "Nilphamari", "কুড়িগ্রাম": "Kurigram",
        "কুড়িগ্রাম": "Kurigram", "লালমনিরহাট": "Lalmonirhat", "গাইবান্ধা": "Gaibandha",
        "জয়পুরহাট": "Joypurhat", "জয়পুরহাট": "Joypurhat", "নওগাঁ": "Naogaon",
        "চাঁপাইনবাবগঞ্জ": "Chapainawabganj", "ফরিদপুর": "Faridpur", "মাদারীপুর": "Madaripur",
        "শরীয়তপুর": "Shariatpur", "শরীয়তপুর": "Shariatpur", "গোপালগঞ্জ": "Gopalganj",
        "রাজবাড়ী": "Rajbari", "রাজবাড়ী": "Rajbari", "নড়াইল": "Narail", "নড়াইল": "Narail",
        "মাগুরা": "Magura", "বাগেরহাট": "Bagerhat", "সাতক্ষীরা": "Satkhira",
        "ঝালকাঠি": "Jhalokati", "পিরোজপুর": "Pirojpur", "পটুয়াখালী": "Patuakhali",
        "পটুয়াখালী": "Patuakhali", "বরগুনা": "Barguna", "ভোলা": "Bhola",
        "মানিকগঞ্জ": "Manikganj", "মুন্সিগঞ্জ": "Munshiganj", "মুন্সীগঞ্জ": "Munshiganj",
        "শেরপুর": "Sherpur", "মেহেরপুর": "Meherpur", "লক্ষ্মীপুর": "Lakshmipur",
        "খাগড়াছড়ি": "Khagrachhari", "খাগড়াছড়ি": "Khagrachhari", "রাঙ্গামাটি": "Rangamati",
        "বান্দরবান": "Bandarban",
    }
    districts_lower_map.update(bengali_districts)

    # If an optional corrected location is explicitly provided, use it
    if corrected_location and corrected_location.strip():
        norm_key = corrected_location.strip().lower()
        detected_location = districts_lower_map.get(norm_key, corrected_location.strip())
    else:
        # Priority A: Check prepositional proximity first: "near <district>", "in <district>", "at <district>", "around <district>"
        for prep_match in re.finditer(r"(?:\b|^)(near|at|in|around|outside|close to)\s+([^\n\r,.;!]+)", cleaned, re.IGNORECASE):
            following_phrase = prep_match.group(2).strip().lower()
            for dist_key in sorted(districts_lower_map.keys(), key=len, reverse=True):
                if dist_key.isascii():
                    if re.search(rf"^{re.escape(dist_key)}\b", following_phrase):
                        detected_location = districts_lower_map[dist_key]
                        break
                else:
                    if following_phrase.startswith(dist_key) or dist_key in following_phrase:
                        detected_location = districts_lower_map[dist_key]
                        break
            if detected_location:
                break

        # Priority B: Search for district mentions in general text if no preposition match
        if not detected_location:
            for dist_key in sorted(districts_lower_map.keys(), key=len, reverse=True):
                if dist_key.isascii():
                    pattern = rf"\b{re.escape(dist_key)}\b"
                    if re.search(pattern, lower_text):
                        detected_location = districts_lower_map[dist_key]
                        break
                else:
                    if dist_key in lower_text:
                        detected_location = districts_lower_map[dist_key]
                        break

    # Check for highway corridors
    detected_corridor: str | None = None
    corridor_endpoints: tuple[str, str] | None = None
    for pattern, name, endpoints in CORRIDOR_INDICATORS:
        if re.search(pattern, lower_text):
            detected_corridor = name
            corridor_endpoints = endpoints
            if not detected_location:
                detected_location = endpoints[1]  # default to destination or midway
            break

    # 2. Transport Mode Detection
    has_both_indicator = any(re.search(rf"\b{re.escape(term)}\b", lower_text) for term in BOTH_INDICATORS)

    railway_hits = sum(1 for kw in RAILWAY_KEYWORDS if re.search(rf"\b{re.escape(kw)}\b", lower_text))
    road_hits = sum(1 for kw in ROAD_KEYWORDS if re.search(rf"\b{re.escape(kw)}\b", lower_text))

    transport_mode: Literal["BUS", "TRAIN", "BOTH"] | None = None
    if has_both_indicator or (railway_hits > 0 and road_hits > 0 and ("both" in lower_text or "and" in lower_text)):
        transport_mode = "BOTH"
    elif railway_hits > 0 and road_hits == 0:
        transport_mode = "TRAIN"
    elif road_hits > 0 and railway_hits == 0:
        transport_mode = "BUS"
    elif railway_hits > 0 and road_hits > 0:
        # Check context dominance
        if railway_hits > road_hits * 2:
            transport_mode = "TRAIN"
        elif road_hits > railway_hits * 2:
            transport_mode = "BUS"
        else:
            transport_mode = "BOTH"

    # 3. Incident Type / Cause
    incident_type = "Transport Disruption"
    cause_code = "OTHER"
    for pat, inc_name, inc_code in CAUSE_PATTERNS:
        if re.search(pat, lower_text):
            incident_type = inc_name
            cause_code = inc_code
            break

    # Adjust cause_code to match transport mode if generic
    if incident_type == "Accident" or (cause_code in ("ROAD_ACCIDENT", "RAILWAY_ACCIDENT") and "accident" in lower_text):
        if transport_mode == "TRAIN":
            cause_code = "RAILWAY_ACCIDENT"
            incident_type = "Railway Accident"
        elif transport_mode == "BUS":
            cause_code = "ROAD_ACCIDENT"
            incident_type = "Road Accident"

    if cause_code == "TRAIN_SUSPENSION" and transport_mode == "BUS":
        cause_code = "BUS_SUSPENSION"
        incident_type = "Bus Service Suspension"
    elif cause_code == "ROAD_ACCIDENT" and transport_mode == "TRAIN":
        cause_code = "RAILWAY_ACCIDENT"
        incident_type = "Railway Accident"

    # 4. Operational Impact
    operational_impact = "Service Disrupted"
    for pat, impact_desc in IMPACT_PATTERNS:
        if re.search(pat, lower_text):
            operational_impact = impact_desc
            break

    if "suspended" in operational_impact.lower():
        if transport_mode == "TRAIN":
            operational_impact = "Train Service Suspended"
        elif transport_mode == "BUS":
            operational_impact = "Bus Service Suspended"

    # 5. Severity Determination
    severity: Literal["LOW", "MODERATE", "HIGH", "CRITICAL"] = "MODERATE"
    if "suspended" in lower_text or "suspension" in lower_text or "derail" in lower_text or "fatal" in lower_text:
        severity = "CRITICAL"
    elif "blocked" in lower_text or "closure" in lower_text or "closed" in lower_text or "flood" in lower_text:
        severity = "HIGH"
    elif "delay" in lower_text or "slow" in lower_text or "protest" in lower_text:
        severity = "MODERATE"
    else:
        severity = "MODERATE"

    # 6. Ambiguity & Clarification Evaluation
    clarification_reasons = []
    if not detected_location:
        clarification_reasons.append("Location is ambiguous or unidentifiable. Please specify the district or city (e.g. Cumilla, Dhaka).")
    if not transport_mode:
        clarification_reasons.append("Transport mode is ambiguous. Please clarify if this affects bus, train, or both.")

    # Guard: A bare generic mention like "An incident has occurred near Cumilla." lacks mode and impact
    if detected_location and not transport_mode and incident_type == "Transport Disruption":
        clarification_reasons.append("Incident details are too vague. Please specify the affected transport mode and incident type (e.g., road blockage, train accident).")

    is_confident = (len(clarification_reasons) == 0)
    clarification_prompt = " ".join(clarification_reasons) if clarification_reasons else None

    # 7. Dynamic Alert Message & Title Synthesis
    mode_label = transport_mode if transport_mode else "Transport"
    loc_display = detected_location or "the affected area"

    if transport_mode == "TRAIN":
        title = f"Train Disruption near {loc_display}"
        if "suspended" in operational_impact.lower():
            alert_message = f"Train movement is currently suspended near {loc_display} due to {incident_type.lower()}. This route may be unavailable or facing severe disruption."
        else:
            alert_message = f"Train services passing near {loc_display} are experiencing disruptions due to {incident_type.lower()}. Expect delays."
    elif transport_mode == "BUS":
        title = f"Bus & Highway Disruption near {loc_display}"
        if detected_corridor:
            alert_message = f"Bus movement on {detected_corridor} near {loc_display} is disrupted due to {incident_type.lower()} ({operational_impact.lower()}). Expect delays."
        elif "blocked" in operational_impact.lower() or "closed" in operational_impact.lower():
            alert_message = f"Road movement is currently blocked near {loc_display} due to {incident_type.lower()}. Bus trips through this corridor may be delayed or rerouted."
        else:
            alert_message = f"Bus movement near {loc_display} is experiencing disruptions due to {incident_type.lower()}. Expect delays."
    elif transport_mode == "BOTH":
        title = f"Road & Railway Disruption near {loc_display}"
        alert_message = f"Both road and railway movement near {loc_display} are heavily disrupted due to {incident_type.lower()} ({operational_impact.lower()}). Travelers should check trip status."
    else:
        title = f"Transport Disruption near {loc_display}"
        alert_message = f"Transport movement near {loc_display} is disrupted due to {incident_type.lower()}."

    # Check for railway corridor if train mode and not already matched
    if transport_mode in ("TRAIN", "BOTH") and detected_location and not detected_corridor:
        from src.train.corridors import get_corridors_crossing_district
        crossing = get_corridors_crossing_district(detected_location)
        if crossing:
            detected_corridor = crossing[0]

    matching_confidence = "HIGH" if is_confident else "AMBIGUOUS"
    matching_status = "CONFIDENT MATCH" if is_confident else "NEEDS CLARIFICATION"

    return ExtractedIncident(
        is_confident=is_confident,
        location=detected_location,
        transport_mode=transport_mode,
        incident_type=incident_type,
        cause_code=cause_code,
        operational_impact=operational_impact,
        severity=severity,
        title=title,
        alert_message=alert_message,
        matching_confidence=matching_confidence,
        matching_status=matching_status,
        corridor_name=detected_corridor,
        corridor_endpoints=corridor_endpoints,
        clarification_prompt=clarification_prompt,
    )
