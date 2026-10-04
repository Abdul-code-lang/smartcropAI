"""Train/evaluate the global demo model on time ordered sample records and save metrics."""
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
data = pd.read_csv(ROOT / "data" / "historical_prices.csv", parse_dates=["date"])
data["price_per_kg"] = pd.to_numeric(data["price_per_kg"], errors="coerce")
data = data.dropna(subset=["date", "crop", "market", "price_per_kg"])
data = data[data.price_per_kg > 0].sort_values("date")
data["crop_code"] = data.crop.astype("category").cat.codes
data["market_code"] = data.market.astype("category").cat.codes
data["month"] = data.date.dt.month
data["trend"] = data.date.map(pd.Timestamp.toordinal)
data["lag1"] = data.groupby(["crop", "market"]).price_per_kg.shift()
data["lag2"] = data.groupby(["crop", "market"]).price_per_kg.shift(2)
data = data.dropna()
features = ["crop_code", "market_code", "month", "trend", "lag1", "lag2"]
dates = sorted(data.date.unique())
cutoff = dates[max(1, int(len(dates) * .8)) - 1]
train, test = data[data.date <= cutoff], data[data.date > cutoff]
model = RandomForestRegressor(n_estimators=200, max_depth=8, min_samples_leaf=2, random_state=42)
model.fit(train[features], train.price_per_kg)
pred = model.predict(test[features])
metrics = {"mae": float(mean_absolute_error(test.price_per_kg, pred)), "rmse": float(np.sqrt(mean_squared_error(test.price_per_kg, pred))), "r2": float(r2_score(test.price_per_kg, pred))}
artifact = {"model": model, "features": features, "crops": data.crop.astype("category").cat.categories.tolist(), "markets": data.market.astype("category").cat.categories.tolist(), "metrics": metrics, "version": "demo-1"}
joblib.dump(artifact, ROOT / "ml" / "model.pkl")
(ROOT / "ml" / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
print(f"Saved demo model. Time-ordered holdout metrics: {json.dumps(metrics)}")
