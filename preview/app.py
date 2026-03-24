"""Preview server to review competitor analysis output on mobile."""

from pathlib import Path

from flask import Flask, send_file

app = Flask(__name__)

PREVIEW_HTML = Path(__file__).parent / "index.html"


@app.route("/")
def dashboard():
    return send_file(PREVIEW_HTML)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
