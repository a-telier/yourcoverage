"""Content theme analysis: extract colors, materials, categories from scraped text."""

from collections import Counter

# Theme vocabularies for home/décor industry (multilingual)
COLORS = {
    "white": ["white", "blanc", "vit", "bianco", "blanco"],
    "blue": ["blue", "bleu", "blå", "azul", "navy", "indigo", "cobalt"],
    "green": ["green", "vert", "grön", "verde", "sage", "olive", "emerald"],
    "beige": ["beige", "sand", "ecru", "cream", "crème", "ivory"],
    "grey": ["grey", "gray", "gris", "grå", "charcoal", "slate"],
    "brown": ["brown", "brun", "marron", "terracotta", "rust", "camel"],
    "black": ["black", "noir", "svart", "negro"],
    "pink": ["pink", "rose", "rosa", "blush", "coral"],
    "yellow": ["yellow", "jaune", "gul", "mustard", "ochre"],
    "red": ["red", "rouge", "röd", "rojo", "burgundy"],
    "orange": ["orange", "tangerine", "peach", "apricot"],
    "purple": ["purple", "violet", "lila", "lavender", "mauve"],
    "gold": ["gold", "doré", "guld", "brass", "golden"],
    "natural": ["natural", "naturel", "natur", "earthy"],
}

MATERIALS = {
    "cotton": ["cotton", "coton", "bomull", "algodón"],
    "linen": ["linen", "lin", "linne"],
    "silk": ["silk", "soie", "silke", "seda"],
    "wool": ["wool", "laine", "ull", "lana"],
    "velvet": ["velvet", "velours", "sammet"],
    "ceramic": ["ceramic", "céramique", "keramik", "porcelain"],
    "wood": ["wood", "bois", "trä", "madera", "oak", "walnut", "teak", "pine"],
    "rattan": ["rattan", "rotin", "rotting", "wicker", "bamboo"],
    "metal": ["metal", "métal", "metall", "iron", "steel", "brass", "copper"],
    "glass": ["glass", "verre", "glas", "cristal", "crystal"],
    "stone": ["stone", "pierre", "sten", "marble", "travertine"],
    "leather": ["leather", "cuir", "läder", "cuero"],
    "jute": ["jute", "sisal", "hemp", "seagrass"],
}

CATEGORIES = {
    "bedding": ["bedding", "bed", "duvet", "pillow", "sheet", "quilt",
                 "linge de lit", "sängkläder", "pillowcase", "bedroom",
                 "chambre", "sovrum"],
    "bathroom": ["bathroom", "bath", "towel", "shower", "salle de bain",
                  "badrum", "serviette"],
    "living room": ["living", "sofa", "couch", "salon", "vardagsrum",
                     "throw", "blanket", "cushion"],
    "kitchen": ["kitchen", "cuisine", "kök", "dining", "tableware",
                 "plate", "mug", "cup", "bowl"],
    "outdoor": ["outdoor", "garden", "terrace", "balcony", "patio",
                 "jardin", "trädgård", "extérieur"],
    "decor": ["decor", "décor", "decoration", "vase", "candle", "frame",
               "mirror", "lamp", "light", "bougie", "ljus"],
    "storage": ["storage", "basket", "shelf", "rangement", "förvaring"],
    "kids": ["kids", "children", "baby", "enfant", "barn", "nursery"],
    "rugs": ["rug", "carpet", "tapis", "matta", "runner"],
    "curtains": ["curtain", "drape", "rideau", "gardin", "blind"],
}

CAMPAIGNS = {
    "new collection": ["new collection", "nouvelle collection", "ny kollektion",
                        "new arrivals", "nouveautés", "nyheter"],
    "sale": ["sale", "soldes", "rea", "rebajas", "discount", "promo", "offer",
             "erbjudande"],
    "seasonal": ["spring", "summer", "autumn", "winter", "printemps", "été",
                  "automne", "hiver", "vår", "sommar", "höst", "vinter"],
    "collaboration": ["collab", "collaboration", "collection by", "designed by"],
    "sustainability": ["sustainable", "organic", "recycled", "eco", "durable",
                         "responsable", "hållbar"],
}


def _find_matches(text: str, vocabulary: dict[str, list[str]]) -> dict[str, int]:
    """Count keyword matches per theme in text."""
    text_lower = text.lower()
    matches = {}
    for theme, keywords in vocabulary.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > 0:
            matches[theme] = count
    return matches


def analyze_text(text: str) -> list[dict]:
    """Analyze any text and return theme tags for database storage.

    Returns list of dicts: [{"kind": "color", "label": "blue", "match_count": 3}, ...]
    """
    if not text:
        return []

    tags = []
    for kind, vocab in [
        ("color", COLORS),
        ("material", MATERIALS),
        ("category", CATEGORIES),
        ("campaign", CAMPAIGNS),
    ]:
        matches = _find_matches(text, vocab)
        for label, count in matches.items():
            tags.append({"kind": kind, "label": label, "match_count": count})

    return tags


def summarize_themes(theme_tags: list[dict]) -> dict:
    """Aggregate theme tags into a summary structure.

    Input: list of {"kind", "label", "match_count"} dicts.
    Output: {
        "top_colors": [...], "top_materials": [...],
        "top_categories": [...], "campaigns": [...],
    }
    """
    counters = {
        "color": Counter(),
        "material": Counter(),
        "category": Counter(),
        "campaign": Counter(),
    }
    for tag in theme_tags:
        kind = tag["kind"]
        if kind in counters:
            counters[kind][tag["label"]] += tag.get("match_count", 1)

    return {
        "top_colors": [c for c, _ in counters["color"].most_common(5)],
        "top_materials": [m for m, _ in counters["material"].most_common(5)],
        "top_categories": [c for c, _ in counters["category"].most_common(5)],
        "campaigns": [c for c, _ in counters["campaign"].most_common(3)],
    }


def generate_summary(theme_data: dict) -> str:
    """Generate a human-readable content summary from theme data."""
    parts = []
    if theme_data.get("top_categories"):
        parts.append("Focus: " + ", ".join(theme_data["top_categories"][:3]))
    if theme_data.get("top_colors"):
        parts.append("Colors: " + ", ".join(theme_data["top_colors"][:3]))
    if theme_data.get("top_materials"):
        parts.append("Materials: " + ", ".join(theme_data["top_materials"][:3]))
    if theme_data.get("campaigns"):
        parts.append("Campaign: " + ", ".join(theme_data["campaigns"][:2]))
    return " · ".join(parts) if parts else "No clear theme detected"
