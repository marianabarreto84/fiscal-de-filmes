import json
import re
import time

import requests
from bs4 import BeautifulSoup

BASE = "https://letterboxd.com"
DELAY = 1.5  # seconds between requests

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def make_session():
    s = requests.Session()
    s.headers.update(_HEADERS)
    return s


def _fetch(session, url, retries=2):
    for attempt in range(retries + 1):
        try:
            r = session.get(url, timeout=15)
            r.raise_for_status()
            time.sleep(DELAY)
            return BeautifulSoup(r.text, "lxml")
        except requests.RequestException:
            if attempt == retries:
                raise
            time.sleep(2 ** attempt * 3)


def _parse_count(text):
    """Converts '1.2M', '500K', '1,234' to int."""
    if not text:
        return None
    text = text.strip().replace(",", "").replace("\xa0", "").replace(" ", "")
    for suffix, mult in [("B", 1_000_000_000), ("M", 1_000_000), ("K", 1_000)]:
        if text.upper().endswith(suffix):
            try:
                return int(float(text[:-1]) * mult)
            except ValueError:
                return None
    try:
        return int(text)
    except ValueError:
        return None


def scrape_list(session, list_url):
    """
    Returns (meta dict, list of film stubs).
    meta: {name, owner, description, film_count}
    stub: {slug, title, position, notes}
    """
    list_url = list_url.rstrip("/") + "/"
    films = []
    meta = {"name": None, "owner": None, "description": None, "film_count": 0}
    page = 1

    while True:
        url = list_url if page == 1 else f"{list_url}page/{page}/"
        soup = _fetch(session, url)

        if page == 1:
            el = soup.select_one("h1.title-1, h1.headline-1")
            meta["name"] = el.get_text(strip=True) if el else None

            el = soup.select_one(".list-title-meta .owner a, .list-attributes .owner a")
            meta["owner"] = el.get_text(strip=True) if el else None

            el = soup.select_one(".list-description p, .body-text p")
            meta["description"] = el.get_text(strip=True) if el else None

        items = soup.select("li.poster-container")
        if not items:
            break

        for item in items:
            poster = item.select_one("[data-film-slug]")
            if not poster:
                continue
            img = poster.select_one("img")
            note_el = item.select_one(".poster-viewingdata")
            films.append({
                "slug": poster.get("data-film-slug"),
                "title": img.get("alt") if img else None,
                "position": len(films) + 1,
                "notes": note_el.get_text(strip=True) if note_el else None,
            })

        if not soup.select_one("a.next"):
            break
        page += 1

    meta["film_count"] = len(films)
    return meta, films


def scrape_film(session, slug):
    """Returns a dict with all available metadata for a film."""
    url = f"{BASE}/film/{slug}/"
    soup = _fetch(session, url)

    film = {
        "letterboxd_slug": slug,
        "letterboxd_url": url,
        "title": None,
        "original_title": None,
        "year": None,
        "runtime": None,
        "synopsis": None,
        "tagline": None,
        "average_rating": None,
        "ratings_count": None,
        "watches_count": None,
        "likes_count": None,
        "cast": [],
        "crew": {},
        "genres": [],
        "themes": [],
        "countries": [],
        "languages": [],
        "studios": [],
    }

    # JSON-LD: title, synopsis, runtime, aggregate rating
    ld_tag = soup.find("script", type="application/ld+json")
    if ld_tag:
        try:
            ld = json.loads(ld_tag.string)
            film["title"] = ld.get("name")
            film["synopsis"] = ld.get("description")

            if m := re.match(r"PT(\d+)M", ld.get("duration", "")):
                film["runtime"] = int(m.group(1))

            agg = ld.get("aggregateRating", {})
            if agg.get("ratingValue"):
                film["average_rating"] = float(agg["ratingValue"])
            if agg.get("ratingCount"):
                film["ratings_count"] = int(agg["ratingCount"])
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    # Year
    el = soup.select_one(
        ".releaseyear a, small.number a[href*='/films/year/'], "
        "p.releasedate a[href*='/films/year/']"
    )
    if el:
        try:
            film["year"] = int(el.get_text(strip=True))
        except ValueError:
            pass

    # Tagline
    el = soup.select_one("h4.tagline")
    film["tagline"] = el.get_text(strip=True) if el else None

    # Original title (shown below main title when the film is not in English)
    el = soup.select_one("h2.originalTitle")
    film["original_title"] = el.get_text(strip=True) if el else None

    # Title fallback if JSON-LD didn't have it
    if not film["title"]:
        el = soup.select_one("h1.headline-1, h1[itemprop='name']")
        film["title"] = el.get_text(strip=True) if el else slug

    # Cast tab
    cast_tab = soup.select_one("#tab-cast")
    if cast_tab:
        for a in cast_tab.select("a[href*='/actor/'], a[href*='/name/']"):
            parts = a["href"].strip("/").split("/")
            film["cast"].append({
                "name": a.get_text(strip=True),
                "slug": parts[-1] if parts else None,
            })

    # Crew tab — sections have id="crew-{role}"
    for section in soup.select("[id^='crew-']"):
        role = section["id"][len("crew-"):]
        people = []
        for a in section.select("a[href]"):
            parts = a["href"].strip("/").split("/")
            name = a.get_text(strip=True)
            if name:
                people.append({
                    "name": name,
                    "slug": parts[-1] if len(parts) >= 2 else None,
                })
        if role and people:
            film["crew"][role] = people

    # Genres / Themes tab
    genres_tab = soup.select_one("#tab-genres")
    if genres_tab:
        film["genres"] = [
            a.get_text(strip=True)
            for a in genres_tab.select("a[href*='/films/genre/']")
        ]
        film["themes"] = [
            a.get_text(strip=True)
            for a in genres_tab.select(
                "a[href*='/films/theme/'], a[href*='/films/nano-genre/']"
            )
        ]

    # Details tab: countries, languages, studios
    details_tab = soup.select_one("#tab-details")
    if details_tab:
        film["countries"] = [
            a.get_text(strip=True)
            for a in details_tab.select("a[href*='/films/country/']")
        ]
        film["languages"] = [
            a.get_text(strip=True)
            for a in details_tab.select("a[href*='/films/language/']")
        ]
        film["studios"] = [
            a.get_text(strip=True)
            for a in details_tab.select("a[href*='/studio/']")
        ]

    # Stats: watches and likes from the sidebar links
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        val_el = a.select_one(".value")
        if not val_el:
            continue
        if f"/film/{slug}/members/" in href:
            film["watches_count"] = _parse_count(val_el.get_text())
        elif f"/film/{slug}/likes/" in href or f"/film/{slug}/fans/" in href:
            film["likes_count"] = _parse_count(val_el.get_text())

    return film
