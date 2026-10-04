# SmartCrop AI — Crop Price Prediction & Market Recommendation

SmartCrop AI is a farmer-focused demonstration application for exploring crop price trends and comparing estimated market prices. A farmer selects a crop, enters a town, and chooses a forecast horizon; a Flask API analyzes the included weekly data and returns a forecast, market ranking, model check, and saved prediction history.

> **Data honesty:** The included records are synthetic sample data. The project has no live government market feed, weather integration, or production accuracy claim. Forecasts and market comparisons are for demonstrating the workflow and must not be treated as actual market quotes.

## Problem and objectives

Farmers often have to choose when and where to sell with incomplete price information. This mini-project demonstrates how historical price patterns can be turned into a simple, explainable decision-support view. Its objectives are to offer clear crop and location inputs, inspect recent prices, create a time-ordered ML forecast, compare sample market observations, and preserve prediction requests.

## Features

- Responsive landing page, prediction flow, and farmer dashboard.
- Flask JSON APIs for crops, markets, prediction, trends, comparisons, history, and health.
- Scikit-learn Random Forest regression, with a chronological holdout evaluation (MAE, RMSE, and R²).
- Market prices sorted by forecast estimate; distance appears for recognized market towns.
- SQLite prediction-history fallback for a no-configuration demo; optional MySQL-backed history.
- Clear sample-data labels and human-readable validation/errors.

## Technology and structure

Python, Flask, Pandas, NumPy, scikit-learn, MySQL Connector, SQLite (demo fallback), HTML, CSS, and vanilla JavaScript. Flask serves both the frontend and API from one local origin.

```text
backend/app.py                 Flask application and API routes
backend/services/history.py    MySQL/SQLite prediction history
frontend/                      HTML pages, CSS, and browser JavaScript
ml/predict.py                  Data cleanup, time features, evaluation, forecasts
ml/train_model.py              Standalone dataset training and model artifact script
data/historical_prices.csv     Synthetic sample observations (not live data)
database/schema.sql            MySQL tables and crop/market seed rows
requirements.txt
.env.example
```

## Run locally (Windows PowerShell)

From the project folder:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python -m backend.app
```

Open **http://127.0.0.1:5000**. The included data is ready immediately; no model artifact needs to be generated for the demo forecast. If `py -3` is unavailable, install Python 3.10 or later and substitute `python` for `py -3` when creating the virtual environment.

### Optional MySQL setup

1. Install and start MySQL Server.
2. Run `database/schema.sql` in a MySQL client (it creates the database and core relational tables).
3. Set `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME` in `.env`.
4. Restart Flask. Prediction history uses the configured MySQL database; with `DB_HOST` empty the app uses `data/prediction_history.sqlite`.

The app currently reads its demonstration historical prices from CSV. The MySQL schema includes normalized crop, market, historical-price, and prediction tables as a future integration path; it does not import the synthetic CSV automatically.

## ML workflow and interpretation

The request-time forecast cleans invalid observations, aggregates weekly values for the nearest matching market, creates lag/rolling/time features, evaluates a Random Forest on a chronological holdout, then fits the final model to available series and recursively predicts up to four weeks. Each selected series is fitted once per server process and reused for later requests; restarting Flask clears this small in-memory cache. The selected period chooses week one, two, or four. The UI reports holdout MAE/RMSE/R² instead of inventing a confidence probability. A low or negative R² can happen and signals weak fit; MAE is in the same price units as the data.

To run the standalone dataset training/evaluation script and save `ml/model.pkl` plus `ml/metrics.json`:

```powershell
python ml/train_model.py
```

This artifact is for the pooled training demonstration. The API uses a selected-series model cache rather than reloading this pooled artifact because it forecasts a crop and market weekly series directly. A production system should persist and version the series models (or train a validated globally encoded estimator) when real data becomes available.

## API

All responses are JSON. API errors use an explanatory `error` field and HTTP 4xx/5xx status.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Service/data/history backend status |
| GET | `/api/crops` | Crop choices |
| GET | `/api/markets` | Market list and sample coordinates |
| GET | `/api/historical-prices?crop=Tomato&location=Tirunelveli` | Recent weekly observations |
| GET | `/api/market-comparison?crop=Tomato&location=Tirunelveli&period=Next%20Week` | Sorted market estimates |
| POST | `/api/predict` | Forecast, charts, comparison, recommendation, reliability metrics; JSON `{ "crop": "Tomato", "location": "Tirunelveli", "period": "Next Week" }` |
| GET | `/api/prediction-history` | Latest 25 saved requests |

## Sample dataset

The CSV includes 2,120 synthetic weekly observations: eight crops × five markets × 53 weeks. It exists so the interface and model run immediately. Replace it with appropriately licensed, checked data and update the data notice before presenting results as factual.

## Future enhancements

Potential next steps include verified government market API integration, weather and demand signals, model monitoring and walk-forward evaluation, language selection, a voice interface, mobile clients, and SMS alerts. Each requires its own real data source and validation before affecting a farmer recommendation.
