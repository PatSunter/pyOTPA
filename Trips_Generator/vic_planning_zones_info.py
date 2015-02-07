
# These are for constraining trip start and end locations based on planning
# zone info.

RESIDENTIAL_ZONES = [\
    # General residential zones
    "GRZ", "GRZ1", "GRZ2", "GRZ3", "GRZ4", "GRZ5", "GRZ6", "GRZ7", "GRZ8", "GRZ9",
    "GRZ10", "GRZ11", "GRZ12", "GRZ13",
    "R1Z", "R2Z", "R3Z",
    # Neighbourhood residential zones
    "NRZ", "NRZ1", "NRZ2", "NRZ3", "NRZ4", "NRZ7",
    # Residential growth zones
    "RGZ1", "RGZ2", "RGZ3",
    # Mixed use zones
    "MUZ", "MUZ1", "MUZ2",
    # Low-density residential zones.
    "LDRZ",
    # Township zones
    "TZ",
    # Commercial mixued use zones.
    "B1Z", "B2Z", "B5Z", "C1Z",
    # Capital city zones
    "CCZ1", "CCZ2", "CCZ3", "CCZ4",
    # Docklands zones - 37.05
    "DZ1", "DZ2", "DZ3", "DZ4", "DZ5", "DZ6", "DZ7",
    # Rural living zones.
    "RLZ", "RLZ1", "RLZ2", "RLZ3", "RLZ4", "RLZ5",
    # Priority Development Zones - maybe these can be residential??
    "PDZ", "PDZ1", "PDZ2",
    # DON't add UGZ - Urban Growth Zone - as mostly not devp'd yet (Up to
    # UGZ13)
    # Activity center zone - 37.08
    "ACZ", "ACZ1",
    ]

RESIDENTIAL_AND_EMPLOYMENT_ZONES = RESIDENTIAL_ZONES + \
    [
    #Commercial, non-residential
    "B3Z", "B4Z", "C2Z",
    #Industrial zones
    "IN1Z", "IN2Z", "IN3Z",
    # Adding public use, since it includes schools etc.
    "PUZ1", "PUZ2", "PUZ3", "PUZ4", "PUZ5", "PUZ6", "PUZ7",
    # Parks and rec - people might work at sports centres etc
    "PPRZ",
    # Comprehensive devt zones - includes shopping ctrs etc
    "CDZ1", "CDZ2", "CDZ3", "CDZ4", "CDZ5", "CDZ6",
    # Rural activity zone - caravan parks etc
    "RAZ",
    # Public Conservation and Resource Zone
    "PCRZ",
    # Port zone
    "PZ",
    # Special use zone - e.g. could be refineries, ...
    "SUZ", "SUZ1", "SUZ2", "SUZ3", "SUZ4", "SUZ5", "SUZ6", "SUZ7", "SUZ8",
    "SUZ9", "SUZ10", "SUZ11", "SUZ12", "SUZ13",
    ]

