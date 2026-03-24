"""Preview server to review competitor analysis output on mobile."""

import json
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template

app = Flask(__name__)

# Sample data simulating real output
SAMPLE_DATA = {
    "nike": [
        {"year": 2025, "month": 10, "post_count": 22, "total_likes": 1_450_000, "total_comments": 32_000, "avg_likes": 65909.09, "avg_comments": 1454.55, "engagement_rate": 0.0273, "follower_count": 306_000_000},
        {"year": 2025, "month": 11, "post_count": 18, "total_likes": 1_230_000, "total_comments": 28_500, "avg_likes": 68333.33, "avg_comments": 1583.33, "engagement_rate": 0.0288, "follower_count": 306_000_000},
        {"year": 2025, "month": 12, "post_count": 25, "total_likes": 1_890_000, "total_comments": 41_000, "avg_likes": 75600.00, "avg_comments": 1640.00, "engagement_rate": 0.0309, "follower_count": 306_000_000},
        {"year": 2026, "month": 1, "post_count": 20, "total_likes": 1_560_000, "total_comments": 35_200, "avg_likes": 78000.00, "avg_comments": 1760.00, "engagement_rate": 0.0296, "follower_count": 307_000_000},
        {"year": 2026, "month": 2, "post_count": 16, "total_likes": 1_180_000, "total_comments": 27_800, "avg_likes": 73750.00, "avg_comments": 1737.50, "engagement_rate": 0.0311, "follower_count": 307_000_000},
        {"year": 2026, "month": 3, "post_count": 12, "total_likes": 920_000, "total_comments": 21_500, "avg_likes": 76666.67, "avg_comments": 1791.67, "engagement_rate": 0.0321, "follower_count": 307_000_000},
    ],
    "adidas": [
        {"year": 2025, "month": 10, "post_count": 30, "total_likes": 980_000, "total_comments": 18_500, "avg_likes": 32666.67, "avg_comments": 616.67, "engagement_rate": 0.0142, "follower_count": 70_000_000},
        {"year": 2025, "month": 11, "post_count": 26, "total_likes": 870_000, "total_comments": 16_200, "avg_likes": 33461.54, "avg_comments": 623.08, "engagement_rate": 0.0148, "follower_count": 70_000_000},
        {"year": 2025, "month": 12, "post_count": 28, "total_likes": 1_050_000, "total_comments": 20_100, "avg_likes": 37500.00, "avg_comments": 717.86, "engagement_rate": 0.0153, "follower_count": 70_000_000},
        {"year": 2026, "month": 1, "post_count": 24, "total_likes": 810_000, "total_comments": 15_800, "avg_likes": 33750.00, "avg_comments": 658.33, "engagement_rate": 0.0147, "follower_count": 71_000_000},
        {"year": 2026, "month": 2, "post_count": 20, "total_likes": 720_000, "total_comments": 14_100, "avg_likes": 36000.00, "avg_comments": 705.00, "engagement_rate": 0.0155, "follower_count": 71_000_000},
        {"year": 2026, "month": 3, "post_count": 15, "total_likes": 580_000, "total_comments": 11_200, "avg_likes": 38666.67, "avg_comments": 746.67, "engagement_rate": 0.0166, "follower_count": 71_000_000},
    ],
    "puma": [
        {"year": 2025, "month": 10, "post_count": 18, "total_likes": 320_000, "total_comments": 8_500, "avg_likes": 17777.78, "avg_comments": 472.22, "engagement_rate": 0.0101, "follower_count": 36_000_000},
        {"year": 2025, "month": 11, "post_count": 15, "total_likes": 275_000, "total_comments": 7_200, "avg_likes": 18333.33, "avg_comments": 480.00, "engagement_rate": 0.0105, "follower_count": 36_000_000},
        {"year": 2025, "month": 12, "post_count": 20, "total_likes": 410_000, "total_comments": 10_800, "avg_likes": 20500.00, "avg_comments": 540.00, "engagement_rate": 0.0117, "follower_count": 36_000_000},
        {"year": 2026, "month": 1, "post_count": 16, "total_likes": 295_000, "total_comments": 7_900, "avg_likes": 18437.50, "avg_comments": 493.75, "engagement_rate": 0.0106, "follower_count": 36_500_000},
        {"year": 2026, "month": 2, "post_count": 14, "total_likes": 260_000, "total_comments": 6_800, "avg_likes": 18571.43, "avg_comments": 485.71, "engagement_rate": 0.0110, "follower_count": 36_500_000},
        {"year": 2026, "month": 3, "post_count": 10, "total_likes": 195_000, "total_comments": 5_100, "avg_likes": 19500.00, "avg_comments": 510.00, "engagement_rate": 0.0116, "follower_count": 36_500_000},
    ],
}


def format_number(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


app.jinja_env.filters["fmtnum"] = format_number


@app.route("/")
def dashboard():
    return render_template("dashboard.html", data=SAMPLE_DATA)


@app.route("/api/data")
def api_data():
    return json.dumps(SAMPLE_DATA)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
