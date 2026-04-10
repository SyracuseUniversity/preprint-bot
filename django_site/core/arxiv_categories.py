"""
arXiv category taxonomy – flat list and nested tree structure.

Used by the profile form's category-picker widget.
"""

from typing import Dict, List

# Nested tree used by the JavaScript category picker
ARXIV_CATEGORY_TREE: List[Dict] = [
    {
        "label": "Computer Science",
        "value": "cs",
        "children": [
            {"label": "Artificial Intelligence (cs.AI)", "value": "cs.AI"},
            {"label": "Computation and Language (cs.CL)", "value": "cs.CL"},
            {"label": "Computational Complexity (cs.CC)", "value": "cs.CC"},
            {"label": "Computer Vision and Pattern Recognition (cs.CV)", "value": "cs.CV"},
            {"label": "Cryptography and Security (cs.CR)", "value": "cs.CR"},
            {"label": "Databases (cs.DB)", "value": "cs.DB"},
            {"label": "Data Structures and Algorithms (cs.DS)", "value": "cs.DS"},
            {"label": "Distributed, Parallel, and Cluster Computing (cs.DC)", "value": "cs.DC"},
            {"label": "Human-Computer Interaction (cs.HC)", "value": "cs.HC"},
            {"label": "Information Retrieval (cs.IR)", "value": "cs.IR"},
            {"label": "Information Theory (cs.IT)", "value": "cs.IT"},
            {"label": "Machine Learning (cs.LG)", "value": "cs.LG"},
            {"label": "Multiagent Systems (cs.MA)", "value": "cs.MA"},
            {"label": "Neural and Evolutionary Computing (cs.NE)", "value": "cs.NE"},
            {"label": "Networking and Internet Architecture (cs.NI)", "value": "cs.NI"},
            {"label": "Programming Languages (cs.PL)", "value": "cs.PL"},
            {"label": "Robotics (cs.RO)", "value": "cs.RO"},
            {"label": "Software Engineering (cs.SE)", "value": "cs.SE"},
            {"label": "Social and Information Networks (cs.SI)", "value": "cs.SI"},
            {"label": "Systems and Control (cs.SY)", "value": "cs.SY"},
        ],
    },
    {
        "label": "Economics",
        "value": "econ",
        "children": [
            {"label": "Econometrics (econ.EM)", "value": "econ.EM"},
            {"label": "General Economics (econ.GN)", "value": "econ.GN"},
            {"label": "Theoretical Economics (econ.TH)", "value": "econ.TH"},
        ],
    },
    {
        "label": "Electrical Engineering and Systems Science",
        "value": "eess",
        "children": [
            {"label": "Audio and Speech Processing (eess.AS)", "value": "eess.AS"},
            {"label": "Image and Video Processing (eess.IV)", "value": "eess.IV"},
            {"label": "Signal Processing (eess.SP)", "value": "eess.SP"},
            {"label": "Systems and Control (eess.SY)", "value": "eess.SY"},
        ],
    },
    {
        "label": "Mathematics",
        "value": "math",
        "children": [
            {"label": "Combinatorics (math.CO)", "value": "math.CO"},
            {"label": "Dynamical Systems (math.DS)", "value": "math.DS"},
            {"label": "Information Theory (math.IT)", "value": "math.IT"},
            {"label": "Numerical Analysis (math.NA)", "value": "math.NA"},
            {"label": "Optimization and Control (math.OC)", "value": "math.OC"},
            {"label": "Probability (math.PR)", "value": "math.PR"},
            {"label": "Statistics Theory (math.ST)", "value": "math.ST"},
        ],
    },
    {
        "label": "Physics",
        "value": "physics_group",
        "children": [
            {"label": "Cosmology and Nongalactic Astrophysics (astro-ph.CO)", "value": "astro-ph.CO"},
            {"label": "Astrophysics of Galaxies (astro-ph.GA)", "value": "astro-ph.GA"},
            {"label": "Condensed Matter (cond-mat.stat-mech)", "value": "cond-mat.stat-mech"},
            {"label": "General Relativity and Quantum Cosmology (gr-qc)", "value": "gr-qc"},
            {"label": "High Energy Physics – Theory (hep-th)", "value": "hep-th"},
            {"label": "Quantum Physics (quant-ph)", "value": "quant-ph"},
        ],
    },
    {
        "label": "Quantitative Biology",
        "value": "q-bio",
        "children": [
            {"label": "Genomics (q-bio.GN)", "value": "q-bio.GN"},
            {"label": "Neurons and Cognition (q-bio.NC)", "value": "q-bio.NC"},
            {"label": "Populations and Evolution (q-bio.PE)", "value": "q-bio.PE"},
            {"label": "Quantitative Methods (q-bio.QM)", "value": "q-bio.QM"},
        ],
    },
    {
        "label": "Statistics",
        "value": "stat",
        "children": [
            {"label": "Applications (stat.AP)", "value": "stat.AP"},
            {"label": "Machine Learning (stat.ML)", "value": "stat.ML"},
            {"label": "Methodology (stat.ME)", "value": "stat.ME"},
        ],
    },
]


def _build_code_to_label() -> Dict[str, str]:
    """Build a flat code → human-readable label mapping."""
    out: Dict[str, str] = {}

    def walk(nodes):
        for node in nodes:
            v = node.get("value", "")
            lbl = node.get("label", v)
            if v:
                out[v] = lbl
            for ch in node.get("children", []):
                walk([ch])

    walk(ARXIV_CATEGORY_TREE)
    return out


ARXIV_CODE_TO_LABEL: Dict[str, str] = _build_code_to_label()


def label_for(code: str) -> str:
    """Return the human-readable label for an arXiv category code."""
    return ARXIV_CODE_TO_LABEL.get(code, code)
