"""Content theme analysis: extract colors, materials, categories from captions."""

import re
from collections import Counter

# Theme vocabularies for home/décor industry
COLORS = {
    "white": ["white", "blanc", "vit", "bianco", "blanco"],
    "blue": ["blue", "bleu", "blå", "azul", "navy", "indigo", "cobalt", "cerulean"],
    "green": ["green", "vert", "grön", "verde", "sage", "olive", "emerald", "moss"],
    "beige": ["beige", "sand", "ecru", "cream", "crème", "creme", "ivory"],
    "grey": ["grey", "gray", "gris", "grå", "charcoal", "slate"],
    "brown": ["brown", "brun", "marron", "terracotta", "terra cotta", "rust", "camel"],
    "black": ["black", "noir", "svart", "negro"],
    "pink": ["pink", "rose", "rosa", "blush", "coral"],
    "yellow": ["yellow", "jaune", "gul", "mustard", "ochre"],
    "red": ["red", "rouge", "röd", "rojo", "burgundy", "crimson"],
    "orange": ["orange", "tangerine", "peach", "apricot"],
    "purple": ["purple", "violet", "lila", "lavender", "mauve", "plum"],
    "gold": ["gold", "doré", "guld", "brass", "golden"],
    "natural": ["natural", "naturel", "natur", "earthy", "earth tone"],
}

MATERIALS = {
    "cotton": ["cotton", "coton", "bomull", "algodón"],
    "linen": ["linen", "lin", "linne"],
    "silk": ["silk", "soie", "silke", "seda"],
    "wool": ["wool", "laine", "ull", "lana"],
    "velvet": ["velvet", "velours", "sammet", "terciopelo"],
    "ceramic": ["ceramic", "céramique", "keramik", "cerámica", "porcelain"],
    "wood": ["wood", "bois", "trä", "madera", "oak", "walnut", "teak", "pine", "birch"],
    "rattan": ["rattan", "rotin", "rotting", "wicker", "bamboo", "cane"],
    "metal": ["metal", "métal", "metall", "iron", "steel", "brass", "copper"],
    "glass": ["glass", "verre", "glas", "cristal", "crystal"],
    "stone": ["stone", "pierre", "sten", "marble", "travertine", "granite"],
    "leather": ["leather", "cuir", "läder", "cuero"],
    "jute": ["jute", "sisal", "hemp", "seagrass"],
}

CATEGORIES = {
    "bedding": ["bedding", "bed", "duvet", "pillow", "sheet", "comforter", "quilt",
                 "linge de lit", "sängkläder", "cushion", "pillowcase", "bedspread",
                 "bedroom", "chambre", "sovrum"],
    "bathroom": ["bathroom", "bath", "towel", "shower", "salle de bain", "badrum",
                  "baño", "serviette"],
    "living room": ["living", "sofa", "couch", "salon", "vardagsrum", "lounge",
                     "throw", "blanket", "cushion"],
    "kitchen": ["kitchen", "cuisine", "kök", "cocina", "dining", "tableware",
                 "plate", "mug", "cup", "bowl"],
    "outdoor": ["outdoor", "garden", "terrace", "balcony", "patio", "jardin",
                 "trädgård", "extérieur", "parasol"],
    "decor": ["decor", "décor", "decoration", "vase", "candle", "frame",
               "mirror", "lamp", "light", "bougie", "ljus"],
    "storage": ["storage", "basket", "box", "shelf", "rangement", "förvaring",
                 "organizer"],
    "kids": ["kids", "children", "baby", "enfant", "barn", "nursery"],
    "rugs": ["rug", "carpet", "tapis", "matta", "alfombra", "runner"],
    "curtains": ["curtain", "drape", "rideau", "gardin", "cortina", "blind"],
    "tableware": ["table", "plate", "glass", "cutlery", "napkin", "serviette",
                   "vaisselle"],
}

CAMPAIGNS = {
    "new collection": ["new collection", "nouvelle collection", "ny kollektion",
                        "nueva colección", "new arrivals", "nouveautés"],
    "sale": ["sale", "soldes", "rea", "rebajas", "discount", "promo", "offer"],
    "seasonal": ["spring", "summer", "autumn", "winter", "printemps", "été",
                  "automne", "hiver", "vår", "sommar", "höst", "vinter"],
    "collaboration": ["collab", "collaboration", "collection by", "designed by",
                       "x ", "feat."],
    "sustainability": ["sustainable", "organic", "recycled", "eco", "durable",
                         "responsable", "hållbar"],
    "christmas": ["christmas", "noël", "jul", "navidad", "holiday", "festive"],
    "valentine": ["valentine", "saint-valentin", "alla hjärtans"],
}


def _find_matches(text: str, vocabulary: dict[str, list[str]]) -> dict[str, int]:
    """Count how many keyword matches each theme has in the text."""
    text_lower = text.lower()
    matches = {}
    for theme, keywords in vocabulary.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > 0:
            matches[theme] = count
    return matches


def analyze_post(caption: str) -> dict:
    """Analyze a single post caption for themes."""
    if not caption:
        return {"colors": [], "materials": [], "categories": [], "campaigns": []}

    return {
        "colors": sorted(_find_matches(caption, COLORS).keys()),
        "materials": sorted(_find_matches(caption, MATERIALS).keys()),
        "categories": sorted(_find_matches(caption, CATEGORIES).keys()),
        "campaigns": sorted(_find_matches(caption, CAMPAIGNS).keys()),
    }


def analyze_week(posts: list[dict]) -> dict:
    """Analyze all posts in a week and return aggregated theme summary."""
    color_counts = Counter()
    material_counts = Counter()
    category_counts = Counter()
    campaign_counts = Counter()

    for post in posts:
        caption = post.get("caption", "") or ""
        themes = analyze_post(caption)
        color_counts.update(themes["colors"])
        material_counts.update(themes["materials"])
        category_counts.update(themes["categories"])
        campaign_counts.update(themes["campaigns"])

    return {
        "top_colors": [c for c, _ in color_counts.most_common(5)],
        "top_materials": [m for m, _ in material_counts.most_common(5)],
        "top_categories": [c for c, _ in category_counts.most_common(5)],
        "campaigns": [c for c, _ in campaign_counts.most_common(3)],
        "color_detail": dict(color_counts),
        "material_detail": dict(material_counts),
        "category_detail": dict(category_counts),
        "campaign_detail": dict(campaign_counts),
    }


def generate_summary(theme_data: dict) -> str:
    """Generate a human-readable content summary from theme analysis."""
    parts = []

    if theme_data["top_categories"]:
        cats = ", ".join(theme_data["top_categories"][:3])
        parts.append(f"Focus: {cats}")

    if theme_data["top_colors"]:
        colors = ", ".join(theme_data["top_colors"][:3])
        parts.append(f"Colors: {colors}")

    if theme_data["top_materials"]:
        mats = ", ".join(theme_data["top_materials"][:3])
        parts.append(f"Materials: {mats}")

    if theme_data["campaigns"]:
        camps = ", ".join(theme_data["campaigns"][:2])
        parts.append(f"Campaign: {camps}")

    return " · ".join(parts) if parts else "No clear theme detected"
