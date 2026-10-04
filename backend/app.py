"""SmartCrop AI Flask application; sample data is clearly identified in every response."""
from __future__ import annotations
import sys
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")
from ml.predict import CropForecaster, DataUnavailable  # noqa: E402
from backend.services.history import HistoryStore  # noqa: E402

app = Flask(__name__, static_folder=str(ROOT / "frontend"), static_url_path="")
forecaster = CropForecaster(ROOT / "data" / "historical_prices.csv", ROOT / "ml" / "model.pkl")
history = HistoryStore(ROOT)
MARKETS = [
    {"name": "Tirunelveli", "location": "Tirunelveli", "latitude": 8.7139, "longitude": 77.7567},
    {"name": "Palayamkottai", "location": "Palayamkottai", "latitude": 8.7274, "longitude": 77.7042},
    {"name": "Thoothukudi", "location": "Thoothukudi", "latitude": 8.7642, "longitude": 78.1348},
    {"name": "Madurai", "location": "Madurai", "latitude": 9.9252, "longitude": 78.1198},
    {"name": "Nagercoil", "location": "Nagercoil", "latitude": 8.1833, "longitude": 77.4119},
]

@app.get("/")
def home():
    return send_from_directory(ROOT / "frontend", "index.html")

@app.get("/<path:page>")
def pages(page):
    if page.startswith("api/"):
        return jsonify({"error": "The requested API endpoint was not found."}), 404
    candidate = ROOT / "frontend" / page
    if candidate.is_file():
        return send_from_directory(ROOT / "frontend", page)
    return send_from_directory(ROOT / "frontend", "index.html")

@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "data_source": "sample", "database": history.backend_name})

@app.get("/api/crops")
def crops():
    return jsonify({"crops": forecaster.crops, "data_source": "sample"})

@app.get("/api/markets")
def markets():
    return jsonify({"markets": MARKETS, "data_source": "sample"})

@app.get("/api/historical-prices")
def historical_prices():
    crop = request.args.get("crop", "").strip()
    location = request.args.get("location", "").strip()
    if not crop or not location:
        return jsonify({"error": "Crop and location are required."}), 400
    try:
        result = forecaster.history(crop, location)
    except DataUnavailable as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({"crop": crop.title(), "location": location, **result, "data_source": "sample"})

@app.get("/api/market-comparison")
def market_comparison():
    crop, location = request.args.get("crop", "").strip(), request.args.get("location", "").strip()
    if not crop or not location:
        return jsonify({"error": "Crop and location are required."}), 400
    try:
        result = forecaster.predict(crop, location, request.args.get("period", "Next Week"))
    except (DataUnavailable, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"markets": result["markets"], "best_market": result["best_market"], "data_source": "sample"})

@app.post("/api/predict")
def predict():
    payload = request.get_json(silent=True) or {}
    crop, location = str(payload.get("crop", "")).strip(), str(payload.get("location", "")).strip()
    period = str(payload.get("period", "Next Week"))
    if not crop:
        return jsonify({"error": "Please select a crop."}), 400
    if not location:
        return jsonify({"error": "Please select or enter your location."}), 400
    if period not in forecaster.periods:
        return jsonify({"error": "Choose a valid prediction period."}), 400
    try:
        result = forecaster.predict(crop, location, period)
        history.save(crop, location, period, result)
        return jsonify({**result, "data_source": "sample", "notice": "Demo forecast based on clearly labelled sample data; not live market information."})
    except DataUnavailable as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception:
        app.logger.exception("Prediction failed")
        return jsonify({"error": "Something went wrong while preparing your forecast. Please try again."}), 500

@app.get("/api/prediction-history")
def prediction_history():
    return jsonify({"history": history.list_recent(), "data_source": "sample"})

@app.errorhandler(404)
def not_found(_error):
    return jsonify({"error": "The requested resource was not found."}), 404

@app.errorhandler(500)
def server_error(_error):
    app.logger.error("Unhandled server error: %s", _error)
    return jsonify({"error": "Something went wrong. Please try again."}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
