"""Prediction history persistence: MySQL when configured, local SQLite for an instant demo."""
import json
import os
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

class HistoryStore:
    def __init__(self, root):
        self.root = Path(root)
        self.mysql = bool(os.getenv("DB_HOST") and os.getenv("DB_NAME"))
        self.backend_name = "MySQL" if self.mysql else "SQLite demo fallback"
        # Vercel's deployed project directory is read-only; only /tmp is writable.
        # Its contents are ephemeral, so durable deployed history requires MySQL.
        self.sqlite_path = (Path(tempfile.gettempdir()) / "smartcrop_prediction_history.sqlite"
                            if os.getenv("VERCEL") else self.root / "data" / "prediction_history.sqlite")
        if self.mysql:
            self._mysql_init()
        else:
            self._sqlite_init()

    def _sqlite(self):
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _sqlite_init(self):
        with self._sqlite() as db:
            db.execute("CREATE TABLE IF NOT EXISTS prediction_history (id INTEGER PRIMARY KEY AUTOINCREMENT, crop TEXT NOT NULL, location TEXT NOT NULL, period TEXT NOT NULL, predicted_price REAL NOT NULL, best_market TEXT NOT NULL, created_at TEXT NOT NULL, result_json TEXT NOT NULL)")

    def _mysql_conn(self):
        import mysql.connector
        return mysql.connector.connect(host=os.getenv("DB_HOST"), port=int(os.getenv("DB_PORT", "3306")), user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"), database=os.getenv("DB_NAME"))

    def _mysql_init(self):
        with self._mysql_conn() as db:
            cur = db.cursor()
            cur.execute("""CREATE TABLE IF NOT EXISTS prediction_history (id BIGINT AUTO_INCREMENT PRIMARY KEY, crop VARCHAR(80) NOT NULL, location VARCHAR(120) NOT NULL, period VARCHAR(30) NOT NULL, predicted_price DECIMAL(10,2) NOT NULL, best_market VARCHAR(120) NOT NULL, created_at DATETIME NOT NULL, result_json JSON NOT NULL)""")
            db.commit()

    def save(self, crop, location, period, result):
        created = datetime.now().isoformat(timespec="seconds")
        if self.mysql:
            with self._mysql_conn() as db:
                cur = db.cursor()
                cur.execute("INSERT INTO prediction_history (crop,location,period,predicted_price,best_market,created_at,result_json) VALUES (%s,%s,%s,%s,%s,%s,%s)", (crop, location, period, result["predicted_price"], result["best_market"]["market"], created, json.dumps(result)))
                db.commit()
        else:
            with self._sqlite() as db:
                db.execute("INSERT INTO prediction_history (crop,location,period,predicted_price,best_market,created_at,result_json) VALUES (?,?,?,?,?,?,?)", (crop, location, period, result["predicted_price"], result["best_market"]["market"], created, json.dumps(result)))

    def list_recent(self):
        if self.mysql:
            with self._mysql_conn() as db:
                cur = db.cursor(dictionary=True)
                cur.execute("SELECT id,crop,location,period,predicted_price,best_market,created_at FROM prediction_history ORDER BY id DESC LIMIT 25")
                rows = cur.fetchall()
        else:
            with self._sqlite() as db:
                rows = [dict(r) for r in db.execute("SELECT id,crop,location,period,predicted_price,best_market,created_at FROM prediction_history ORDER BY id DESC LIMIT 25")]
        for row in rows:
            if hasattr(row.get("created_at"), "isoformat"):
                row["created_at"] = row["created_at"].isoformat(timespec="minutes")
            if isinstance(row.get("predicted_price"), str):
                row["predicted_price"] = float(row["predicted_price"])
        return rows
