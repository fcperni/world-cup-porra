"""Fuente ESPN (primaria) vía su API JSON pública de marcadores.

Endpoint: ``site.api.espn.com/.../soccer/{liga}/scoreboard?dates=YYYYMMDD``.
La liga del Mundial es ``fifa.world``.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import requests

from ..models import TournamentData
from .base import ResultsSource, ScrapedGame

ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard"


class ESPNSource(ResultsSource):
    name = "ESPN"

    def __init__(self, league: str = "fifa.world", timeout: int = 10):
        self.league = league
        self.timeout = timeout

    def _dates(self, data: TournamentData) -> list[date]:
        days = {m.date.date() for m in data.matches if m.date}
        if not days:
            return []
        # cubrir el rango (con un día de margen por zona horaria) pero solo hasta hoy:
        # los partidos futuros aún no tienen resultado, así que no merece la pena pedirlos.
        lo, hi = min(days), min(max(days), date.today() + timedelta(days=1))
        if hi < lo:
            return []
        return [lo + timedelta(days=i) for i in range((hi - lo).days + 1)]

    def _fetch_day(self, day: date) -> list[ScrapedGame]:
        url = ESPN_URL.format(league=self.league)
        resp = requests.get(url, params={"dates": day.strftime("%Y%m%d")},
                            timeout=self.timeout, headers={"User-Agent": "porra/1.0"})
        resp.raise_for_status()
        return _parse_scoreboard(resp.json())

    def fetch(self, data: TournamentData) -> list[ScrapedGame]:
        games: list[ScrapedGame] = []
        for day in self._dates(data):
            try:
                games.extend(self._fetch_day(day))
            except Exception:  # noqa: BLE001 — un día sin datos no aborta el resto
                continue
        return games


def _parse_scoreboard(payload: dict) -> list[ScrapedGame]:
    games: list[ScrapedGame] = []
    for event in payload.get("events", []):
        comps = event.get("competitions", [])
        if not comps:
            continue
        comp = comps[0]
        home = away = None
        hg = ag = None
        for c in comp.get("competitors", []):
            name = (c.get("team", {}) or {}).get("displayName") or (c.get("team", {}) or {}).get("name")
            score = _as_int(c.get("score"))
            if c.get("homeAway") == "home":
                home, hg = name, score
            elif c.get("homeAway") == "away":
                away, ag = name, score
        status = (event.get("status", {}) or {}).get("type", {}) or {}
        finished = bool(status.get("completed"))
        when = _parse_date(event.get("date"))
        winner = _winner_from(comp)
        if home and away:
            games.append(ScrapedGame(home=home, away=away, home_goals=hg, away_goals=ag,
                                    finished=finished, when=when, winner=winner))
    return games


def _winner_from(comp: dict) -> Optional[str]:
    for c in comp.get("competitors", []):
        if c.get("winner") and c.get("homeAway") in ("home", "away"):
            return c["homeAway"]
    return None


def _as_int(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_date(value) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None
