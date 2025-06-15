import os

ARXIV_CATEGORIES = [
    # Astrophysics
    "astro-ph", "astro-ph.CO", "astro-ph.EP", "astro-ph.GA",
    "astro-ph.HE", "astro-ph.IM", "astro-ph.SR",

    # General Physics
    "physics", "physics.acc-ph", "physics.ao-ph", "physics.app-ph", "physics.atom-ph",
    "physics.atm-clus", "physics.bio-ph", "physics.chem-ph", "physics.class-ph",
    "physics.comp-ph", "physics.data-an", "physics.ed-ph", "physics.flu-dyn",
    "physics.gen-ph", "physics.geo-ph", "physics.hist-ph", "physics.ins-det",
    "physics.med-ph", "physics.optics", "physics.plasm-ph", "physics.pop-ph",
    "physics.soc-ph", "physics.space-ph",

    # Condensed Matter Physics
    "cond-mat", "cond-mat.dis-nn", "cond-mat.mes-hall", "cond-mat.mtrl-sci",
    "cond-mat.other", "cond-mat.quant-gas", "cond-mat.soft", "cond-mat.stat-mech",
    "cond-mat.str-el", "cond-mat.supr-con",

    # High Energy Physics
    "hep-ex", "hep-lat", "hep-ph", "hep-th",

    # Nuclear Physics
    "nucl-ex", "nucl-th",

    # Quantum Physics
    "quant-ph",

    # General Relativity & Gravitation
    "gr-qc",

    # Mathematical Physics
    "math-ph"
]


SIMILARITY_THRESHOLDS = {
    "low": 0.5,
    "medium": 0.7,
    "high": 0.85
}

MAX_RESULTS = 10
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
DATA_DIR = "arxiv_pipeline_data"

os.makedirs(DATA_DIR, exist_ok=True)
