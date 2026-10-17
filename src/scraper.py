from typing import Any
from urllib.parse import urlparse


ARAB_COUNTRIES = {
    "فلسطين": "ps",
    "الأردن": "jo",
    "مصر": "eg",
    "السعودية": "sa",
    "الإمارات": "ae",
    "قطر": "qa",
    "الكويت": "kw",
    "عُمان": "om",
    "المغرب": "ma",
    "تونس": "tn",
    "الجزائر": "dz",
    "البحرين": "bh",
    "العراق": "iq",
    "لبنان": "lb",
}

CURATED_ARAB_RIDE_APPS = [
    "Careem",
    "Uber",
    "inDrive",
    "Jeeny",
    "Kaiian",
    "Bolt",
    "Yango",
    "DiDi",
    "TaxiF",
    "KDDAD",
]


def search_apps(
    query: str,
    limit: int = 10,
    countries: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Search Google Play when the optional scraper dependency is available.

    The function is deliberately isolated so that rate limits, retries, and review
    pagination can be added without coupling them to the Streamlit UI.
    """
    try:
        from google_play_scraper import search
    except ImportError:
        return []

    country_codes = countries or list(ARAB_COUNTRIES.values())
    all_results: dict[str, dict[str, Any]] = {}
    for country in country_codes:
        try:
            results = search(query, lang="ar", country=country, n_hits=limit)
        except Exception:
            try:
                results = search(query, lang="en", country=country, n_hits=limit)
            except Exception:
                continue
        for item in results:
            app_id = item.get("appId") or item.get("app_id") or item.get("id")
            if not app_id or app_id in all_results:
                continue
            all_results[app_id] = {**item, "_country": country}

    normalized: list[dict[str, Any]] = []
    for item in all_results.values():
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
                "country": item.get("_country"),
            }
        )
    normalized.sort(key=lambda item: (item.get("score") or 0, item.get("ratings_count") or 0), reverse=True)
    return normalized[:limit]


def search_curated_arab_apps(limit: int = 10) -> list[dict[str, Any]]:
    """Return one verified Google Play result for each curated Arabic ride app."""
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for app_name in CURATED_ARAB_RIDE_APPS:
        results = search_apps(app_name, limit=3, countries=["sa", "ae", "eg", "jo"])
        match = next((item for item in results if item.get("app_id") not in seen), None)
        if match:
            match["curated_name"] = app_name
            found.append(match)
            seen.add(match["app_id"])
        if len(found) >= limit:
            break
    return found[:limit]


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
