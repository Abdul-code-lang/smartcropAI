"""Small, explainable time-series regression forecast using lag and calendar features."""
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

class DataUnavailable(Exception):
    pass

class CropForecaster:
    periods = {"Next Week": 1, "Next 2 Weeks": 2, "Next 4 Weeks": 4}

    def __init__(self, csv_path: Path, model_path: Path):
        self.csv_path, self.model_path = Path(csv_path), Path(model_path)
        self.data = pd.read_csv(self.csv_path, parse_dates=["date"])
        self.data["price_per_kg"] = pd.to_numeric(self.data["price_per_kg"], errors="coerce")
        self.data = self.data.dropna(subset=["date", "crop", "market", "price_per_kg"])
        self.data = self.data[self.data.price_per_kg > 0].sort_values("date")
        self.crops = sorted(self.data.crop.unique().tolist())
        self.model = None
        self.metrics = None
        # Fit each selected series once per process and reuse it for later requests.
        self._fitted_series = {}

    @staticmethod
    def _features(series):
        df = pd.DataFrame({"price": series}).reset_index(names="date")
        df["t"] = np.arange(len(df))
        df["month"] = df.date.dt.month
        df["lag1"] = df.price.shift(1)
        df["lag2"] = df.price.shift(2)
        df["rolling3"] = df.price.shift(1).rolling(3, min_periods=1).mean()
        return df.dropna().reset_index(drop=True)

    def _series(self, crop, location):
        crop_match = self.data.crop.str.casefold() == crop.casefold()
        if not crop_match.any():
            raise DataUnavailable("No historical data is available for this crop.")
        market_names = self.data.loc[crop_match, "market"].unique()
        exact = [name for name in market_names if name.casefold() == location.casefold()]
        market = exact[0] if exact else min(market_names, key=lambda n: (n.casefold() not in location.casefold(), abs(len(n)-len(location))))
        rows = self.data[crop_match & (self.data.market == market)].sort_values("date")
        series = rows.set_index("date").price_per_kg.resample("W").mean().interpolate(limit_direction="both").dropna()
        if len(series) < 8:
            raise DataUnavailable("Prediction cannot be generated because sufficient historical data is unavailable.")
        series.name = f"{crop.casefold()}|{market.casefold()}"
        return market, series

    def _fit(self, series):
        frame = self._features(series)
        if len(frame) < 7:
            raise DataUnavailable("Prediction cannot be generated because sufficient historical data is unavailable.")
        cols = ["t", "month", "lag1", "lag2", "rolling3"]
        split = max(5, int(len(frame) * .8))
        if split < len(frame):
            eval_model = RandomForestRegressor(n_estimators=120, max_depth=4, min_samples_leaf=2, random_state=42)
            eval_model.fit(frame[cols].iloc[:split], frame.price.iloc[:split])
            pred = eval_model.predict(frame[cols].iloc[split:])
            actual = frame.price.iloc[split:]
            mae = float(mean_absolute_error(actual, pred))
            rmse = float(np.sqrt(mean_squared_error(actual, pred)))
            r2 = float(r2_score(actual, pred)) if len(actual) > 1 else None
        else:
            mae, rmse, r2 = None, None, None
        model = RandomForestRegressor(n_estimators=160, max_depth=5, min_samples_leaf=2, random_state=42)
        model.fit(frame[cols], frame.price)
        return model, (mae, rmse, r2)

    def _forecast(self, series, weeks):
        key = (str(series.name), str(series.index[0]), str(series.index[-1]), len(series))
        if key not in self._fitted_series:
            self._fitted_series[key] = self._fit(series)
        model, metrics = self._fitted_series[key]
        prices = list(map(float, series.values))
        start = series.index[-1]
        outputs = []
        for step in range(1, weeks + 1):
            future_date = start + pd.Timedelta(weeks=step)
            features = pd.DataFrame([[len(prices), future_date.month, prices[-1], prices[-2], float(np.mean(prices[-3:]))]],
                                    columns=["t", "month", "lag1", "lag2", "rolling3"])
            value = max(.01, float(model.predict(features)[0]))
            outputs.append({"week": step, "date": future_date.strftime("%b %d"), "price": round(value, 2)})
            prices.append(value)
        return outputs, metrics

    def history(self, crop, location):
        market, series = self._series(crop, location)
        tail = series.tail(8)
        return {"market": market, "historical_prices": [{"date": d.strftime("%b %d"), "price": round(float(v), 2)} for d, v in tail.items()]}

    def predict(self, crop, location, period):
        if period not in self.periods:
            raise ValueError("Choose a valid prediction period.")
        market, series = self._series(crop, location)
        forecast, metrics = self._forecast(series, 4)
        weeks = self.periods[period]
        target = forecast[weeks - 1]["price"]
        # Market premiums/discounts are learned from latest observed market prices relative to crop average.
        latest = self.data[(self.data.crop.str.casefold() == crop.casefold())].sort_values("date").groupby("market").tail(1)
        avg = float(latest.price_per_kg.mean())
        market_rows = []
        for row in latest.itertuples():
            m = row.market
            info = next((item for item in MARKET_INFO if item["name"].casefold() == m.casefold()), None)
            distance = _distance(location, info) if info else 0
            predicted = max(.01, target * float(row.price_per_kg) / max(avg, .01))
            market_rows.append({"market": m, "distance_km": distance, "current_price": round(float(row.price_per_kg), 2), "predicted_price": round(predicted, 2)})
        market_rows.sort(key=lambda item: item["predicted_price"], reverse=True)
        best = market_rows[0]
        hist = series.tail(8)
        return {"crop": crop.title(), "location": location.title(), "prediction_period": period,
                "predicted_price": round(target, 2), "historical_prices": [{"date": d.strftime("%b %d"), "price": round(float(v), 2)} for d,v in hist.items()],
                "forecast": forecast, "markets": market_rows, "best_market": best,
                "reliability": {"label": "Historical back-test", "mae": round(metrics[0], 2) if metrics[0] is not None else None,
                                "rmse": round(metrics[1], 2) if metrics[1] is not None else None, "r2": round(metrics[2], 3) if metrics[2] is not None else None,
                                "note": "Past holdout error; not a probability that this forecast is correct."},
                "recommendation": f"For your {period.lower()} outlook, {best['market']} has the highest estimated price at ₹{best['predicted_price']:.2f}/kg in the sample comparison. Check a current local quote before deciding when or where to sell."}

MARKET_INFO = [
    {"name":"Tirunelveli","latitude":8.7139,"longitude":77.7567}, {"name":"Palayamkottai","latitude":8.7274,"longitude":77.7042},
    {"name":"Thoothukudi","latitude":8.7642,"longitude":78.1348}, {"name":"Madurai","latitude":9.9252,"longitude":78.1198}, {"name":"Nagercoil","latitude":8.1833,"longitude":77.4119}]
def _distance(location, market):
    source = next((m for m in MARKET_INFO if m["name"].casefold() == location.casefold()), None)
    if not source: return None
    from math import radians, sin, cos, asin, sqrt
    lat1, lon1, lat2, lon2 = map(radians, [source["latitude"], source["longitude"], market["latitude"], market["longitude"]])
    a = sin((lat2-lat1)/2)**2 + cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
    return round(6371 * 2 * asin(sqrt(a)))
