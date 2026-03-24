"""Tests for theme analysis."""

from yourcoverage.themes import analyze_text, summarize_themes, generate_summary


class TestAnalyzeText:
    def test_detects_colors(self):
        result = analyze_text("New blue linen bedding collection now available")
        labels = {t["label"] for t in result if t["kind"] == "color"}
        assert "blue" in labels

    def test_detects_materials(self):
        result = analyze_text("Our cotton sheets are back in stock")
        labels = {t["label"] for t in result if t["kind"] == "material"}
        assert "cotton" in labels

    def test_detects_categories(self):
        result = analyze_text("Transform your bedroom with our new duvet covers")
        labels = {t["label"] for t in result if t["kind"] == "category"}
        assert "bedding" in labels

    def test_detects_campaigns(self):
        result = analyze_text("Discover our new collection for spring")
        labels = {t["label"] for t in result if t["kind"] == "campaign"}
        assert "new collection" in labels
        assert "seasonal" in labels

    def test_multilingual(self):
        result = analyze_text("Nouvelle collection de linge de lit en lin")
        labels = {t["label"] for t in result}
        assert "linen" in labels
        assert "bedding" in labels
        assert "new collection" in labels

    def test_empty_text(self):
        assert analyze_text("") == []


class TestSummarizeThemes:
    def test_aggregates(self):
        tags = [
            {"kind": "color", "label": "blue", "match_count": 3},
            {"kind": "color", "label": "white", "match_count": 1},
            {"kind": "material", "label": "cotton", "match_count": 2},
            {"kind": "category", "label": "bedding", "match_count": 5},
        ]
        result = summarize_themes(tags)
        assert result["top_colors"][0] == "blue"
        assert "cotton" in result["top_materials"]
        assert "bedding" in result["top_categories"]


class TestGenerateSummary:
    def test_readable_output(self):
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
