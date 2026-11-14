"""
Bangladesh Railway Network Corridor Definitions and Route Mapping.

Separates train stoppages (passenger boarding/alighting stations) from physical
railway corridors (the geographical districts and tracks a train actually traverses,
even when running non-stop).
"""

from typing import Iterable


# Canonical railway corridors in Bangladesh Railway and the sequence of districts traversed
RAILWAY_CORRIDORS: dict[str, list[str]] = {
    "Dhaka-Chattogram Main Line": [
        "Dhaka", "Gazipur", "Narsingdi", "Kishoreganj", "Brahmanbaria", "Cumilla", "Feni", "Chattogram"
    ],
    "Dhaka-Cox's Bazar Line": [
        "Dhaka", "Gazipur", "Narsingdi", "Kishoreganj", "Brahmanbaria", "Cumilla", "Feni", "Chattogram", "Cox's Bazar"
    ],
    "Dhaka-Sylhet Line": [
        "Dhaka", "Gazipur", "Narsingdi", "Kishoreganj", "Brahmanbaria", "Habiganj", "Moulvibazar", "Sylhet"
    ],
    "Chattogram-Sylhet Line": [
        "Chattogram", "Feni", "Cumilla", "Brahmanbaria", "Habiganj", "Moulvibazar", "Sylhet"
    ],
    "Dhaka-Noakhali Line": [
        "Dhaka", "Gazipur", "Narsingdi", "Kishoreganj", "Brahmanbaria", "Cumilla", "Noakhali"
    ],
    "Chattogram-Mymensingh-Jamalpur Line": [
        "Chattogram", "Feni", "Cumilla", "Brahmanbaria", "Kishoreganj", "Mymensingh", "Jamalpur"
    ],
    "Chattogram-Chandpur Line": [
        "Chattogram", "Feni", "Cumilla", "Chandpur"
    ],
    "Chattogram-Cox's Bazar Line": [
        "Chattogram", "Cox's Bazar"
    ],
    "Dhaka-Kishoreganj Line": [
        "Dhaka", "Gazipur", "Narsingdi", "Kishoreganj"
    ],
    "Dhaka-Mymensingh-Jamalpur Line": [
        "Dhaka", "Gazipur", "Mymensingh", "Jamalpur"
    ],
    "Dhaka-Netrokona Line": [
        "Dhaka", "Gazipur", "Mymensingh", "Netrokona"
    ],
    "Dhaka-North Bengal (Rajshahi Line)": [
        "Dhaka", "Gazipur", "Tangail", "Sirajganj", "Natore", "Rajshahi", "Chapainawabganj"
    ],
    "Dhaka-North Bengal (Rangpur-Lalmonirhat Line)": [
        "Dhaka", "Gazipur", "Tangail", "Sirajganj", "Natore", "Bogura", "Gaibandha", "Rangpur", "Kurigram", "Lalmonirhat", "Burimari"
    ],
    "Dhaka-North Bengal (Dinajpur-Panchagarh Line)": [
        "Dhaka", "Gazipur", "Tangail", "Sirajganj", "Natore", "Naogaon", "Joypurhat", "Dinajpur", "Nilphamari", "Thakurgaon", "Panchagarh"
    ],
    "Dhaka-Sirajganj Line": [
        "Dhaka", "Gazipur", "Tangail", "Sirajganj"
    ],
    "Dhaka-Pabna Line": [
        "Dhaka", "Gazipur", "Tangail", "Sirajganj", "Natore", "Pabna"
    ],
    "Dhaka-Southwest (Padma Bridge Line)": [
        "Dhaka", "Munshiganj", "Shariatpur", "Madaripur", "Faridpur", "Rajbari", "Gopalganj", "Narail", "Jashore", "Khulna", "Chuadanga", "Kushtia", "Benapole"
    ],
    "Western Zone (Khulna-Rajshahi)": [
        "Khulna", "Jashore", "Jhenaidah", "Chuadanga", "Kushtia", "Pabna", "Natore", "Rajshahi"
    ],
    "Western Zone (Khulna-Chilahati)": [
        "Khulna", "Jashore", "Jhenaidah", "Chuadanga", "Kushtia", "Pabna", "Natore", "Naogaon", "Joypurhat", "Dinajpur", "Nilphamari"
    ],
    "Western Zone (Rajshahi-Panchagarh/Chilahati)": [
        "Rajshahi", "Natore", "Naogaon", "Joypurhat", "Dinajpur", "Nilphamari", "Thakurgaon", "Panchagarh"
    ],
    "Western Zone (Santahar-Burimari/Panchagarh)": [
        "Bogura", "Gaibandha", "Rangpur", "Lalmonirhat", "Joypurhat", "Dinajpur", "Thakurgaon", "Panchagarh", "Burimari"
    ],
    "Western Zone (Rajshahi-Dhalarchar/Gobra)": [
        "Rajshahi", "Pabna", "Gopalganj"
    ],
}


# Mapping origin/destination district pairs to their primary railway corridor name
OD_TO_CORRIDOR: dict[tuple[str, str], str] = {
    # Dhaka <-> Chattogram
    ("Dhaka", "Chattogram"): "Dhaka-Chattogram Main Line",
    ("Chattogram", "Dhaka"): "Dhaka-Chattogram Main Line",

    # Dhaka <-> Cox's Bazar
    ("Dhaka", "Cox's Bazar"): "Dhaka-Cox's Bazar Line",
    ("Cox's Bazar", "Dhaka"): "Dhaka-Cox's Bazar Line",

    # Chattogram <-> Cox's Bazar
    ("Chattogram", "Cox's Bazar"): "Chattogram-Cox's Bazar Line",
    ("Cox's Bazar", "Chattogram"): "Chattogram-Cox's Bazar Line",

    # Dhaka <-> Sylhet
    ("Dhaka", "Sylhet"): "Dhaka-Sylhet Line",
    ("Sylhet", "Dhaka"): "Dhaka-Sylhet Line",

    # Chattogram <-> Sylhet
    ("Chattogram", "Sylhet"): "Chattogram-Sylhet Line",
    ("Sylhet", "Chattogram"): "Chattogram-Sylhet Line",

    # Dhaka <-> Noakhali
    ("Dhaka", "Noakhali"): "Dhaka-Noakhali Line",
    ("Noakhali", "Dhaka"): "Dhaka-Noakhali Line",

    # Chattogram <-> Jamalpur (Bijoy Express)
    ("Chattogram", "Jamalpur"): "Chattogram-Mymensingh-Jamalpur Line",
    ("Jamalpur", "Chattogram"): "Chattogram-Mymensingh-Jamalpur Line",

    # Chattogram <-> Chandpur (Meghna Express)
    ("Chattogram", "Chandpur"): "Chattogram-Chandpur Line",
    ("Chandpur", "Chattogram"): "Chattogram-Chandpur Line",

    # Dhaka <-> Kishoreganj
    ("Dhaka", "Kishoreganj"): "Dhaka-Kishoreganj Line",
    ("Kishoreganj", "Dhaka"): "Dhaka-Kishoreganj Line",

    # Dhaka <-> Jamalpur
    ("Dhaka", "Jamalpur"): "Dhaka-Mymensingh-Jamalpur Line",
    ("Jamalpur", "Dhaka"): "Dhaka-Mymensingh-Jamalpur Line",

    # Dhaka <-> Netrokona
    ("Dhaka", "Netrokona"): "Dhaka-Netrokona Line",
    ("Netrokona", "Dhaka"): "Dhaka-Netrokona Line",

    # Dhaka <-> Rajshahi / Chapainawabganj
    ("Dhaka", "Rajshahi"): "Dhaka-North Bengal (Rajshahi Line)",
    ("Rajshahi", "Dhaka"): "Dhaka-North Bengal (Rajshahi Line)",
    ("Dhaka", "Chapainawabganj"): "Dhaka-North Bengal (Rajshahi Line)",
    ("Chapainawabganj", "Dhaka"): "Dhaka-North Bengal (Rajshahi Line)",

    # Dhaka <-> Rangpur / Kurigram / Lalmonirhat / Burimari
    ("Dhaka", "Rangpur"): "Dhaka-North Bengal (Rangpur-Lalmonirhat Line)",
    ("Rangpur", "Dhaka"): "Dhaka-North Bengal (Rangpur-Lalmonirhat Line)",
    ("Dhaka", "Kurigram"): "Dhaka-North Bengal (Rangpur-Lalmonirhat Line)",
    ("Kurigram", "Dhaka"): "Dhaka-North Bengal (Rangpur-Lalmonirhat Line)",
    ("Dhaka", "Lalmonirhat"): "Dhaka-North Bengal (Rangpur-Lalmonirhat Line)",
    ("Lalmonirhat", "Dhaka"): "Dhaka-North Bengal (Rangpur-Lalmonirhat Line)",
    ("Dhaka", "Burimari"): "Dhaka-North Bengal (Rangpur-Lalmonirhat Line)",
    ("Burimari", "Dhaka"): "Dhaka-North Bengal (Rangpur-Lalmonirhat Line)",

    # Dhaka <-> Panchagarh / Dinajpur / Nilphamari / Chilahati
    ("Dhaka", "Panchagarh"): "Dhaka-North Bengal (Dinajpur-Panchagarh Line)",
    ("Panchagarh", "Dhaka"): "Dhaka-North Bengal (Dinajpur-Panchagarh Line)",
    ("Dhaka", "Chilahati"): "Dhaka-North Bengal (Dinajpur-Panchagarh Line)",
    ("Chilahati", "Dhaka"): "Dhaka-North Bengal (Dinajpur-Panchagarh Line)",

    # Dhaka <-> Sirajganj / Pabna
    ("Dhaka", "Sirajganj Bazar"): "Dhaka-Sirajganj Line",
    ("Sirajganj Bazar", "Dhaka"): "Dhaka-Sirajganj Line",
    ("Dhaka", "Pabna"): "Dhaka-Pabna Line",
    ("Pabna", "Dhaka"): "Dhaka-Pabna Line",

    # Dhaka <-> Khulna / Benapole
    ("Dhaka", "Khulna"): "Dhaka-Southwest (Padma Bridge Line)",
    ("Khulna", "Dhaka"): "Dhaka-Southwest (Padma Bridge Line)",
    ("Dhaka", "Benapole"): "Dhaka-Southwest (Padma Bridge Line)",
    ("Benapole", "Dhaka"): "Dhaka-Southwest (Padma Bridge Line)",

    # Western Zone Internal
    ("Khulna", "Rajshahi"): "Western Zone (Khulna-Rajshahi)",
    ("Rajshahi", "Khulna"): "Western Zone (Khulna-Rajshahi)",
    ("Khulna", "Chilahati"): "Western Zone (Khulna-Chilahati)",
    ("Chilahati", "Khulna"): "Western Zone (Khulna-Chilahati)",
    ("Rajshahi", "Chilahati"): "Western Zone (Rajshahi-Panchagarh/Chilahati)",
    ("Chilahati", "Rajshahi"): "Western Zone (Rajshahi-Panchagarh/Chilahati)",
    ("Rajshahi", "Panchagarh"): "Western Zone (Rajshahi-Panchagarh/Chilahati)",
    ("Panchagarh", "Rajshahi"): "Western Zone (Rajshahi-Panchagarh/Chilahati)",
    ("Santahar", "Burimari"): "Western Zone (Santahar-Burimari/Panchagarh)",
    ("Burimari", "Santahar"): "Western Zone (Santahar-Burimari/Panchagarh)",
    ("Santahar", "Panchagarh"): "Western Zone (Santahar-Burimari/Panchagarh)",
    ("Panchagarh", "Santahar"): "Western Zone (Santahar-Burimari/Panchagarh)",
    ("Rajshahi", "Dhalarchar"): "Western Zone (Rajshahi-Dhalarchar/Gobra)",
    ("Dhalarchar", "Rajshahi"): "Western Zone (Rajshahi-Dhalarchar/Gobra)",
    ("Rajshahi", "Gobra"): "Western Zone (Rajshahi-Dhalarchar/Gobra)",
    ("Gobra", "Rajshahi"): "Western Zone (Rajshahi-Dhalarchar/Gobra)",
}

# Individual train exceptions / special routings by train number
TRAIN_CORRIDOR_OVERRIDE: dict[str, str] = {
    # Suborna Express (Dhaka <-> Chattogram)
    "701": "Dhaka-Chattogram Main Line",
    "702": "Dhaka-Chattogram Main Line",
    # Sonar Bangla Express (Dhaka <-> Chattogram)
    "787": "Dhaka-Chattogram Main Line",
    "788": "Dhaka-Chattogram Main Line",
    # Coxs Bazar Express (Dhaka <-> Cox's Bazar)
    "813": "Dhaka-Cox's Bazar Line",
    "814": "Dhaka-Cox's Bazar Line",
    # Poryotok Express (Dhaka <-> Cox's Bazar)
    "815": "Dhaka-Cox's Bazar Line",
    "816": "Dhaka-Cox's Bazar Line",
    # Bijoy Express (Chattogram <-> Jamalpur via Akhaura in Brahmanbaria)
    "785": "Chattogram-Mymensingh-Jamalpur Line",
    "786": "Chattogram-Mymensingh-Jamalpur Line",
}


def get_train_corridor_name(train_no: str, from_district: str = "", to_district: str = "") -> str | None:
    """Returns the canonical railway corridor name for a train."""
    clean_no = str(train_no).strip()
    if clean_no in TRAIN_CORRIDOR_OVERRIDE:
        return TRAIN_CORRIDOR_OVERRIDE[clean_no]
    pair = (from_district.strip(), to_district.strip())
    if pair in OD_TO_CORRIDOR:
        return OD_TO_CORRIDOR[pair]
    # Check reversed pair
    rev = (to_district.strip(), from_district.strip())
    if rev in OD_TO_CORRIDOR:
        return OD_TO_CORRIDOR[rev]
    return None


def get_train_corridor_districts(train_no: str, from_district: str = "", to_district: str = "") -> list[str]:
    """Returns the list of districts physically traversed by the train's railway corridor."""
    corridor_name = get_train_corridor_name(train_no, from_district, to_district)
    if corridor_name and corridor_name in RAILWAY_CORRIDORS:
        return RAILWAY_CORRIDORS[corridor_name]
    return []


def train_traverses_district(
    train_no: str,
    target_district: str,
    from_district: str = "",
    to_district: str = "",
    scheduled_stop_districts: Iterable[str] | None = None,
) -> tuple[bool, str]:
    """
    Determines whether a train traverses the specified district:
    Returns (traverses: bool, match_category: 'STOP' | 'TRANSIT' | 'NONE').
    - 'STOP': Train has a scheduled passenger halt in the district.
    - 'TRANSIT': Train has no passenger stop, but its physical railway corridor runs through the district.
    - 'NONE': Train does not traverse this district section.
    """
    clean_target = target_district.strip().casefold()
    if not clean_target:
        return False, "NONE"

    # 1. Check Group A: Scheduled Stoppages
    if scheduled_stop_districts:
        for d in scheduled_stop_districts:
            if d and d.strip().casefold() == clean_target:
                return True, "STOP"

    # 2. Check Group B: Physical Corridor Transit (Without Stoppage)
    corridor_districts = get_train_corridor_districts(train_no, from_district, to_district)
    for cd in corridor_districts:
        if cd.strip().casefold() == clean_target:
            return True, "TRANSIT"

    # Also check direct origin / destination
    if from_district.strip().casefold() == clean_target or to_district.strip().casefold() == clean_target:
        return True, "STOP"

    return False, "NONE"


def get_corridors_crossing_district(district_name: str) -> list[str]:
    """Returns all railway corridor names that traverse the given district."""
    clean_dist = district_name.strip().casefold()
    res = []
    for c_name, dists in RAILWAY_CORRIDORS.items():
        if any(d.strip().casefold() == clean_dist for d in dists):
            res.append(c_name)
    return res
