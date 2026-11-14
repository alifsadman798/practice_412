DISTRICT_CANONICAL_MAP = {
    "chapai": "Chapainawabganj",
    "chapai nawabganj": "Chapainawabganj",
    "chapainawabganj": "Chapainawabganj",
    "nawabganj": "Chapainawabganj",
    "coxs bazar": "Cox's Bazar",
    "cox's bazar": "Cox's Bazar",
    "cox bazar": "Cox's Bazar",
    "chittagong": "Chattogram",
    "comilla": "Cumilla",
    "jessore": "Jashore",
    "barisal": "Barishal",
    "bogra": "Bogura",
}


def normalize_name(value: str) -> str:
    cleaned = value.strip()
    return DISTRICT_CANONICAL_MAP.get(cleaned.casefold(), cleaned)


def normalize_location_lookup(value: str) -> str:
    canonical = normalize_name(value)
    return canonical.casefold()
