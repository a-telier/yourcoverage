"""Seed demo data for testing the dashboard without live Instagram access.

Run: python -m yourcoverage.seed_demo
This creates realistic sample data for weeks 10-13 to preview the report.
"""

import json
import random
from datetime import datetime, date
from pathlib import Path

from .storage import save_snapshot, week_label


COMPETITORS = [
    {
        "name": "Zara Home",
        "username": "zarahome",
        "color": "#c4a35a",
        "instagram_url": "https://www.instagram.com/zarahome",
        "website_url": "https://www.zarahome.com/se/",
        "followers": 8_400_000,
        "bio": "Decoration, Bed & Bath Linen, Tableware. Share your #zarahome moments.",
        "post_themes": [
            ("New linen bedding collection in soft blue tones. #zarahome #linen #bedding", "bedding"),
            ("Cotton percale sheets — breathable comfort for warmer nights", "bedding"),
            ("Discover our spring collection: natural textures, earthy tones", "decor"),
            ("Hand-painted ceramic vase collection. Artisan-crafted beauty.", "decor"),
            ("Velvet cushions in deep green and terracotta for your living room", "living room"),
            ("White cotton towels — hotel quality for your bathroom", "bathroom"),
            ("Spring table setting: linen napkins, ceramic plates, glass tumblers", "tableware"),
            ("Rattan storage baskets — organize beautifully", "storage"),
            ("New arrivals: silk pillowcases for better sleep", "bedding"),
            ("Marble bathroom accessories — timeless elegance", "bathroom"),
            ("Outdoor dining collection: terracotta and natural wood", "outdoor"),
            ("Kids room refresh: cotton bedding in playful prints", "kids"),
            ("Scented candles: fig, cedar, amber. Set the mood.", "decor"),
            ("Linen curtains in soft grey — let the light in", "curtains"),
            ("Handwoven jute rug — natural texture underfoot", "rugs"),
        ],
        "website_heroes": [
            "New Collection",
            "The Linen Edit",
            "Spring Home",
            "Bed & Bath",
            "Join Life: Sustainable Choices",
        ],
        "website_campaigns": [
            {"text": "Linen Collection", "url": "/collection/linen/"},
            {"text": "Spring 2026", "url": "/collection/spring/"},
            {"text": "JOIN LIFE — Sustainable Home", "url": "/sustainability/"},
        ],
    },
    {
        "name": "IKEA",
        "username": "ikea",
        "color": "#0058a3",
        "instagram_url": "https://www.instagram.com/ikea",
        "website_url": "https://www.ikea.com/se/sv/",
        "followers": 35_200_000,
        "bio": "Making everyday life better for the many people. #IKEA",
        "post_themes": [
            ("KALLAX shelf unit — endless storage possibilities. Now in new colors!", "storage"),
            ("Spring bedroom makeover with ÄNGSLILJA duvet cover in white cotton", "bedding"),
            ("Small space, big style: SÖDERHAMN sofa for compact living rooms", "living room"),
            ("VARDAGEN kitchen series — everything you need for everyday cooking", "kitchen"),
            ("New SOLLERÖN outdoor furniture for your balcony garden", "outdoor"),
            ("BJÖRKUDDEN bathroom textiles in organic cotton", "bathroom"),
            ("HEMNES bed frame + LUKTJASMIN bedding — dreamy bedroom combo", "bedding"),
            ("Kids love SMÅGÖRA: furniture that grows with them", "kids"),
            ("SINNERLIG rattan pendant lamp — natural beauty overhead", "decor"),
            ("Organize your wardrobe with PAX system. Open plan, open mind.", "storage"),
            ("GLADOM tray table in blue — small but mighty", "living room"),
            ("Earth Day: discover our sustainable cotton bedding range", "bedding"),
            ("STOCKHOLM rug in handwoven wool — craft meets comfort", "rugs"),
            ("MÖJLIGHET curtains — blackout for better sleep", "curtains"),
            ("Cook together: METOD kitchen starting at 3495 kr", "kitchen"),
        ],
        "website_heroes": [
            "Inspiration för ditt hem",
            "Vårens nyheter",
            "KALLAX — Ny i färg",
            "Hållbart hemma",
            "Sovrumsdrömmar",
        ],
        "website_campaigns": [
            {"text": "Vårens nyheter", "url": "/kampanj/vaarens-nyheter/"},
            {"text": "IKEA Family erbjudanden", "url": "/offers/ikea-family/"},
            {"text": "Hållbarhet", "url": "/this-is-ikea/sustainable-everyday/"},
        ],
    },
    {
        "name": "Maisons du Monde",
        "username": "maisonsdumonde",
        "color": "#d4a574",
        "instagram_url": "https://www.instagram.com/maisonsdumonde",
        "website_url": "https://www.maisonsdumonde.com/FR/fr",
        "followers": 5_900_000,
        "bio": "Meubles & Décoration d'intérieur – Maisons du Monde 🏠",
        "post_themes": [
            ("Collection Printemps : mobilier en rotin et lin naturel", "decor"),
            ("Linge de lit en coton lavé — doux et décontracté", "bedding"),
            ("Nouvelle collection de canapés en velours vert sauge", "living room"),
            ("Vaisselle artisanale en céramique blanche et bleue", "tableware"),
            ("Tapis en jute tressé — esprit bord de mer", "rugs"),
            ("Bureau en bois de manguier — travaillez avec style", "decor"),
            ("Coussins en lin beige et terracotta pour votre salon", "living room"),
            ("Collection outdoor : salon de jardin en résine tressée", "outdoor"),
            ("Miroir en rotin — touche bohème pour votre entrée", "decor"),
            ("Parure de lit en percale de coton blanc", "bedding"),
            ("Bougie parfumée figue — ambiance méditerranéenne", "decor"),
            ("Rangement salle de bain en bambou naturel", "bathroom"),
            ("Lampe à poser en verre soufflé — pièce unique", "decor"),
            ("Collection enfant : lit cabane en pin", "kids"),
            ("Rideau en lin lavé naturel — légèreté et élégance", "curtains"),
        ],
        "website_heroes": [
            "Nouvelle Collection Printemps",
            "Styles et Tendances",
            "Le guide outdoor",
            "Inspirations méditerranéennes",
            "Soldes : jusqu'à -50%",
        ],
        "website_campaigns": [
            {"text": "Collection Printemps 2026", "url": "/collection/printemps/"},
            {"text": "Inspiration Méditerranée", "url": "/inspiration/mediterranee/"},
            {"text": "Soldes Maison", "url": "/soldes/"},
        ],
    },
]


def seed():
    """Generate 4 weeks of demo data (W10-W13 of 2026)."""
    random.seed(42)
    weeks = ["2026-W10", "2026-W11", "2026-W12", "2026-W13"]

    for comp in COMPETITORS:
        for week_idx, week in enumerate(weeks):
            posts = []
            # Each week gets 3-5 posts from the theme pool
            n_posts = random.randint(3, 5)
            start_idx = (week_idx * 4) % len(comp["post_themes"])
            for j in range(n_posts):
                caption, _ = comp["post_themes"][(start_idx + j) % len(comp["post_themes"])]
                likes = random.randint(5000, 80000)
                comments = random.randint(50, 1200)

                posts.append({
                    "shortcode": f"demo_{comp['username']}_{week}_{j}",
                    "url": f"https://www.instagram.com/p/demo_{comp['username']}_{j}/",
                    "timestamp": f"2026-03-{10 + week_idx * 7 + j:02d}T12:00:00",
                    "likes": likes,
                    "comments": comments,
                    "caption": caption,
                    "is_video": random.random() < 0.2,
                    "image_url": "",
                    "thumbnail_path": None,
                    "themes": _analyze_caption(caption),
                })

            # Theme analysis
            from .themes import analyze_week, generate_summary
            theme_summary = analyze_week(posts)
            content_summary = generate_summary(theme_summary)

            snapshot = {
                "competitor": {
                    "name": comp["name"],
                    "instagram_username": comp["username"],
                    "instagram_url": comp["instagram_url"],
                    "website_url": comp["website_url"],
                    "color": comp["color"],
                },
                "week": week,
                "collected_at": datetime.utcnow().isoformat(),
                "instagram": {
                    "username": comp["username"],
                    "name": comp["name"],
                    "collected_at": datetime.utcnow().isoformat(),
                    "week": week,
                    "source": "instagram",
                    "profile": {
                        "followers": comp["followers"] + random.randint(-50000, 50000),
                        "following": random.randint(100, 500),
                        "posts_count": random.randint(3000, 8000),
                        "biography": comp["bio"],
                        "is_private": False,
                    },
                    "posts": posts,
                    "theme_summary": theme_summary,
                    "content_summary": content_summary,
                    "error": None,
                },
                "website": {
                    "url": comp["website_url"],
                    "collected_at": datetime.utcnow().isoformat(),
                    "week": week,
                    "source": "website",
                    "title": comp["name"],
                    "hero_texts": comp["website_heroes"],
                    "campaign_banners": comp["website_campaigns"],
                    "navigation_categories": [],
                    "promo_texts": [],
                    "error": None,
                },
            }

            save_snapshot(comp["username"], snapshot, week)

    print(f"Seeded demo data for {len(weeks)} weeks × {len(COMPETITORS)} competitors")
    print("Weeks:", ", ".join(weeks))


def _analyze_caption(caption):
    from .themes import analyze_post
    return analyze_post(caption)


if __name__ == "__main__":
    seed()
