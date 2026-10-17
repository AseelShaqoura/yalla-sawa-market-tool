import sqlite3
from datetime import datetime, timezone
from typing import Any

from .config import settings


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(settings.db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS competitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                developer TEXT,
                score REAL,
                ratings_count INTEGER,
                installs TEXT,
                category TEXT,
                url TEXT,
                icon_url TEXT,
                source TEXT NOT NULL DEFAULT 'google_play',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competitor_id INTEGER NOT NULL,
                review_id TEXT,
                content TEXT NOT NULL,
                score INTEGER,
                review_date TEXT,
                sentiment TEXT,
                themes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (competitor_id) REFERENCES competitors(id) ON DELETE CASCADE,
                UNIQUE (competitor_id, review_id)
            );

            CREATE TABLE IF NOT EXISTS insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competitor_id INTEGER,
                insight_type TEXT NOT NULL,
                title TEXT NOT NULL,
                detail TEXT NOT NULL,
                confidence REAL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (competitor_id) REFERENCES competitors(id) ON DELETE CASCADE
            );
            """
        )


def save_competitor(app: dict[str, Any]) -> None:
    app_id = str(app.get("app_id") or "").strip()
    if not app_id:
        raise ValueError("لا يمكن حفظ المنافس لأن معرّف التطبيق غير موجود")
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO competitors
              (app_id, title, developer, score, ratings_count, installs, category,
               url, icon_url, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(app_id) DO UPDATE SET
              title=excluded.title, developer=excluded.developer,
              score=excluded.score, ratings_count=excluded.ratings_count,
              installs=excluded.installs, category=excluded.category,
              url=excluded.url, icon_url=excluded.icon_url,
              updated_at=excluded.updated_at
            """,
            (
                app_id, app.get("title", "غير معروف"),
                app.get("developer"), app.get("score"), app.get("ratings_count"),
                app.get("installs"), app.get("category"), app.get("url"),
                app.get("icon_url"), app.get("source", "google_play"), now, now,
            ),
        )


def list_competitors() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM competitors ORDER BY updated_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def save_reviews(competitor_id: int, reviews: list[dict[str, Any]]) -> int:
    """Insert reviews once and return the number of rows accepted."""
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    with get_connection() as connection:
        for review in reviews:
            review_id = review.get("review_id") or f"{competitor_id}-{review.get('review_date')}-{inserted}"
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO reviews
                  (competitor_id, review_id, content, score, review_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    competitor_id,
                    review_id,
                    review.get("content", ""),
                    review.get("score"),
                    review.get("review_date"),
                    now,
                ),
            )
            inserted += cursor.rowcount
    return inserted


def list_reviews(competitor_id: int | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM reviews"
    parameters: tuple[Any, ...] = ()
    if competitor_id is not None:
        query += " WHERE competitor_id = ?"
        parameters = (competitor_id,)
    query += " ORDER BY review_date DESC"
    with get_connection() as connection:
        rows = connection.execute(query, parameters).fetchall()
    return [dict(row) for row in rows]


def review_count(competitor_id: int | None = None) -> int:
    query = "SELECT COUNT(*) AS total FROM reviews"
    parameters: tuple[Any, ...] = ()
    if competitor_id is not None:
        query += " WHERE competitor_id = ?"
        parameters = (competitor_id,)
    with get_connection() as connection:
        row = connection.execute(query, parameters).fetchone()
    return int(row["total"])


def list_reviews_for_competitors(competitor_ids: list[int]) -> list[dict[str, Any]]:
    if not competitor_ids:
        return []
    placeholders = ",".join("?" for _ in competitor_ids)
    with get_connection() as connection:
        rows = connection.execute(
            f"SELECT * FROM reviews WHERE competitor_id IN ({placeholders}) ORDER BY review_date DESC",
            tuple(competitor_ids),
        ).fetchall()
    return [dict(row) for row in rows]
