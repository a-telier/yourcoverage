"""Tests for theme analysis."""

from yourcoverage.themes import analyze_post, analyze_week, generate_summary


class TestAnalyzePost:
    def test_detects_colors(self):
        result = analyze_post("New blue linen bedding collection now available")
        assert "blue" in result["colors"]

    def test_detects_materials(self):
        result = analyze_post("Our cotton sheets are back in stock")
        assert "cotton" in result["materials"]

    def test_detects_categories(self):
        result = analyze_post("Transform your bedroom with our new duvet covers")
        assert "bedding" in result["categories"]

    def test_detects_campaigns(self):
        result = analyze_post("Discover our new collection for spring")
        assert "new collection" in result["campaigns"]
        assert "seasonal" in result["campaigns"]

    def test_multilingual(self):
        result = analyze_post("Nouvelle collection de linge de lit en lin")
        assert "linen" in result["materials"]
        assert "bedding" in result["categories"]
        assert "new collection" in result["campaigns"]

    def test_empty_caption(self):
        result = analyze_post("")
        assert result == {"colors": [], "materials": [], "categories": [], "campaigns": []}


class TestAnalyzeWeek:
    def test_aggregates_themes(self):
        posts = [
            {"caption": "Blue cotton bedding for your bedroom"},
            {"caption": "White linen sheets, so fresh"},
            {"caption": "Blue velvet cushions for the living room"},
        ]
        result = analyze_week(posts)
        assert "blue" in result["top_colors"]
        assert "cotton" in result["top_materials"]
        assert "bedding" in result["top_categories"]

    def test_empty_posts(self):
        result = analyze_week([])
        assert result["top_colors"] == []


class TestGenerateSummary:
    def test_generates_readable_summary(self):
        theme_data = {
            "top_colors": ["blue", "white"],
            "top_materials": ["cotton", "linen"],
            "top_categories": ["bedding", "living room"],
            "campaigns": ["new collection"],
        }
        summary = generate_summary(theme_data)
        assert "bedding" in summary
        assert "blue" in summary
        assert "cotton" in summary
