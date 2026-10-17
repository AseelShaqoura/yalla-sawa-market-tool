from typing import Any
from urllib.parse import urlparse


def search_apps(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search Google Play when the optional scraper dependency is available.

    The function is deliberately isolated so that rate limits, retries, and review
    pagination can be added without coupling them to the Streamlit UI.
    """
    try:
        from google_play_scraper import search
    except ImportError:
        return []

    try:
        results = search(query, lang="en", country="us", n_hits=limit)
    except Exception:
        return []

    normalized: list[dict[str, Any]] = []
    for item in results:
        app_id = item.get("appId") or item.get("app_id") or item.get("id")
        app_url = item.get("url") or ""
        if not app_id and app_url:
            path_parts = [part for part in urlparse(app_url).path.split("/") if part]
            if "details" in path_parts:
                details_index = path_parts.index("details")
                if details_index + 1 < len(path_parts):
                    app_id = path_parts[details_index + 1]
        if not app_id:
            continue
        normalized.append(
            {
                "app_id": app_id,
                "title": item.get("title", "غير معروف"),
                "developer": item.get("developer"),
                "score": item.get("score"),
                "ratings_count": item.get("ratings"),
                "installs": item.get("installs"),
                "category": item.get("genre"),
                "url": app_url,
                "icon_url": item.get("icon"),
                "source": "google_play",
            }
        )
    return normalized


def fetch_reviews(app_id: str, count: int = 150) -> list[dict[str, Any]]:
    """Fetch up to ``count`` reviews from Google Play for one app.

    The scraper returns a normalized shape so the UI and database do not depend
    on the third-party package's field names.
    """
    try:
        from google_play_scraper import reviews as play_reviews, Sort
    except ImportError:
        return []

    raw_reviews = []
    try:
        raw_reviews, _ = play_reviews(
            app_id,
            lang="ar",
            country="ps",
            sort=Sort.NEWEST,
            count=count,
        )
    except Exception:
        try:
            raw_reviews, _ = play_reviews(
                app_id,
                lang="en",
                country="us",
                sort=Sort.NEWEST,
                count=count,
            )
        except Exception:
            return []

    normalized: list[dict[str, Any]] = []
    for item in raw_reviews[:count]:
        review_date = item.get("at") or item.get("date")
        normalized.append(
            {
                "review_id": item.get("reviewId") or item.get("review_id"),
                "content": item.get("content", ""),
                "score": item.get("score"),
                "review_date": review_date.isoformat() if hasattr(review_date, "isoformat") else review_date,
            }
        )
    return normalized
