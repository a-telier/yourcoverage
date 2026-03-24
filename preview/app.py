"""Preview server — serves the generated report on localhost for mobile preview."""

from pathlib import Path

from flask import Flask, send_file

app = Flask(__name__)

# Serve from docs/index.html (the generated report)
REPORT_HTML = Path(__file__).parent.parent / "docs" / "index.html"


@app.route("/")
def dashboard():
    if REPORT_HTML.exists():
        return send_file(REPORT_HTML)
    return "<h1>No report generated yet</h1><p>Run: yourcoverage report</p>", 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
