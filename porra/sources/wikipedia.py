"""Fuente Wikipedia (backup).

Parsea las cajas de partido (``div.footballbox``) del HTML renderizado de los
artículos del Mundial 2026. Es *best-effort*: si la estructura cambia o no hay
datos, devuelve lo que pueda sin romper la sincronización (ESPN es la primaria).
"""

from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from ..models import TournamentData
from .base import ResultsSource, ScrapedGame

REST_HTML = "https://en.wikipedia.org/api/rest_v1/page/html/{title}"

# Artículos con los resultados (fase de grupos y eliminatorias).
DEFAULT_ARTICLES = [
    "2026_FIFA_World_Cup_group_stage",
    "2026_FIFA_World_Cup_knockout_stage",
    "2026_FIFA_World_Cup",
]

_SCORE_RE = re.compile(r"(\d+)\s*[–\-:]\s*(\d+)")


class WikipediaSource(ResultsSource):
    name = "Wikipedia"

    def __init__(self, articles: list[str] | None = None, timeout: int = 10):
        self.articles = articles or DEFAULT_ARTICLES
        self.timeout = timeout

    def _fetch_article(self, title: str) -> list[ScrapedGame]:
        resp = requests.get(REST_HTML.format(title=title), timeout=self.timeout,
                            headers={"User-Agent": "porra/1.0 (porra del Mundial)"})
        resp.raise_for_status()
        return parse_footballboxes(resp.text)

    def fetch(self, data: TournamentData) -> list[ScrapedGame]:
        games: list[ScrapedGame] = []
        seen: set[tuple[str, str]] = set()
        for title in self.articles:
            try:
                for g in self._fetch_article(title):
                    key = (g.home, g.away)
                    if key not in seen:
                        seen.add(key)
                        games.append(g)
            except Exception:  # noqa: BLE001
                continue
        return games


def parse_footballboxes(html: str) -> list[ScrapedGame]:
    soup = BeautifulSoup(html, "lxml")
    games: list[ScrapedGame] = []
    for box in soup.select("div.footballbox"):
        home_el = box.select_one(".fhome")
        score_el = box.select_one(".fscore")
        away_el = box.select_one(".faway")
        if not (home_el and away_el):
            continue
        home = _team_name(home_el)
        away = _team_name(away_el)
        hg = ag = None
        finished = False
        if score_el:
            m = _SCORE_RE.search(score_el.get_text(" ", strip=True))
            if m:
                hg, ag, finished = int(m.group(1)), int(m.group(2)), True
        if home and away:
            games.append(ScrapedGame(home=home, away=away, home_goals=hg, away_goals=ag,
                                    finished=finished))
    return games


def _team_name(el) -> str:
    """Extrae el nombre de la selección de una caja .fhome/.faway."""
    link = el.find("a", title=True)
    if link and link.get("title"):
        return link["title"].strip()
    return el.get_text(" ", strip=True)
