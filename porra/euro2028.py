"""Loader de la **Eurocopa 2028** (stub): calendario en vivo desde Wikipedia.

La Euro 2028 aún no tiene equipos sorteados ni participantes/predicciones, así que
este loader construye un :class:`TournamentData` con ``teams=[]`` y ``players=[]``
pero con el **calendario completo** (51 partidos: fecha, sede y placeholders del
cruce) y el :data:`EURO2028_FORMAT` (24 equipos, 6 grupos, R16→QF→SF→Final, sin
3.er puesto). La estructura de puntuación se copia de la del Mundial (única fuente
de valores en ``ADMIN.xlsx``); se confirmará con el tiempo.

**Calendario en vivo**: se scrapea el artículo ``UEFA_Euro_2028`` de Wikipedia
(las cajas ``div.footballbox`` traen nº de partido, fecha, sede y placeholders).
Si el scraping falla o cambia la estructura, se cae a un **esqueleto horneado**
(:data:`_SKELETON`, snapshot del mismo calendario) para que la web nunca quede
sin datos. Cuando se sortee y haya resultados, entrarán por las fuentes de
:mod:`porra.sources` igual que en el Mundial (liga ESPN ``uefa.euro``).
"""

from __future__ import annotations

import re
import warnings
from datetime import datetime
from typing import Optional

from .models import EURO2028_FORMAT, Match, Phase, ScoringRules, TournamentData

WIKI_URL = "https://en.wikipedia.org/api/rest_v1/page/html/UEFA_Euro_2028"

# Bonus por ronda (provisional, a confirmar): grupos 1; R16/QF 2; SF/Final 3.
_BONUS = {Phase.GROUPS: 1, Phase.R16: 2, Phase.QF: 2, Phase.SF: 3, Phase.FINAL: 3}

# Traducción al español de las ciudades sede (el estadio se deja tal cual).
_CITY_ES = {
    "London": "Londres", "Manchester": "Mánchester", "Liverpool": "Liverpool",
    "Newcastle upon Tyne": "Newcastle", "Birmingham": "Birmingham",
    "Glasgow": "Glasgow", "Cardiff": "Cardiff", "Dublin": "Dublín",
}

# Esqueleto horneado (fallback): (nº, fecha ISO, local, visitante, estadio, ciudad).
# Snapshot del calendario oficial (Wikipedia/UEFA); los placeholders son los mismos
# que publica Wikipedia. Se usa solo si el scraping en vivo no está disponible.
_SKELETON: list[tuple[int, str, str, str, str, str]] = [
    (1, "2028-06-09", "A1", "A2", "Millennium Stadium", "Cardiff"),
    (2, "2028-06-10", "A3", "A4", "Hampden Park", "Glasgow"),
    (3, "2028-06-10", "B1", "B2", "City of Manchester Stadium", "Manchester"),
    (4, "2028-06-10", "B3", "B4", "Aviva Stadium", "Dublin"),
    (5, "2028-06-11", "C1", "C2", "Wembley Stadium", "London"),
    (6, "2028-06-11", "C3", "C4", "Villa Park", "Birmingham"),
    (7, "2028-06-11", "D3", "D4", "Hill Dickinson Stadium", "Liverpool"),
    (8, "2028-06-12", "D1", "D2", "Tottenham Hotspur Stadium", "London"),
    (9, "2028-06-12", "E1", "E2", "Aviva Stadium", "Dublin"),
    (10, "2028-06-12", "E3", "E4", "St James' Park", "Newcastle upon Tyne"),
    (11, "2028-06-13", "F1", "F2", "Hampden Park", "Glasgow"),
    (12, "2028-06-13", "F3", "F4", "City of Manchester Stadium", "Manchester"),
    (13, "2028-06-14", "A1", "A3", "Millennium Stadium", "Cardiff"),
    (14, "2028-06-14", "A2", "A4", "Hill Dickinson Stadium", "Liverpool"),
    (15, "2028-06-14", "B1", "B3", "Wembley Stadium", "London"),
    (16, "2028-06-15", "B2", "B4", "Villa Park", "Birmingham"),
    (17, "2028-06-15", "C1", "C3", "Tottenham Hotspur Stadium", "London"),
    (18, "2028-06-15", "C2", "C4", "St James' Park", "Newcastle upon Tyne"),
    (19, "2028-06-16", "D1", "D3", "Wembley Stadium", "London"),
    (20, "2028-06-16", "D2", "D4", "City of Manchester Stadium", "Manchester"),
    (21, "2028-06-16", "E1", "E3", "Aviva Stadium", "Dublin"),
    (22, "2028-06-17", "E2", "E4", "Hill Dickinson Stadium", "Liverpool"),
    (23, "2028-06-17", "F1", "F3", "Hampden Park", "Glasgow"),
    (24, "2028-06-17", "F2", "F4", "St James' Park", "Newcastle upon Tyne"),
    (25, "2028-06-18", "A4", "A1", "Millennium Stadium", "Cardiff"),
    (26, "2028-06-18", "A2", "A3", "Tottenham Hotspur Stadium", "London"),
    (27, "2028-06-19", "B4", "B1", "Wembley Stadium", "London"),
    (28, "2028-06-19", "B2", "B3", "Aviva Stadium", "Dublin"),
    (29, "2028-06-20", "C4", "C1", "City of Manchester Stadium", "Manchester"),
    (30, "2028-06-20", "C2", "C3", "Hill Dickinson Stadium", "Liverpool"),
    (31, "2028-06-20", "D4", "D1", "Villa Park", "Birmingham"),
    (32, "2028-06-20", "D2", "D3", "St James' Park", "Newcastle upon Tyne"),
    (33, "2028-06-21", "E4", "E1", "Aviva Stadium", "Dublin"),
    (34, "2028-06-21", "E2", "E3", "Tottenham Hotspur Stadium", "London"),
    (35, "2028-06-21", "F4", "F1", "Hampden Park", "Glasgow"),
    (36, "2028-06-21", "F2", "F3", "Millennium Stadium", "Cardiff"),
    (37, "2028-06-24", "Winner Group A", "Runner-up Group C", "Millennium Stadium", "Cardiff"),
    (38, "2028-06-24", "Runner-up Group A", "Runner-up Group B", "Hill Dickinson Stadium", "Liverpool"),
    (39, "2028-06-25", "Winner Group B", "3rd Group A/D/E/F", "St James' Park", "Newcastle upon Tyne"),
    (40, "2028-06-25", "Winner Group C", "3rd Group D/E/F", "City of Manchester Stadium", "Manchester"),
    (41, "2028-06-26", "Winner Group F", "3rd Group A/B/C", "Hampden Park", "Glasgow"),
    (42, "2028-06-26", "Runner-up Group D", "Runner-up Group E", "Tottenham Hotspur Stadium", "London"),
    (43, "2028-06-27", "Winner Group D", "Runner-up Group F", "Villa Park", "Birmingham"),
    (44, "2028-06-27", "Winner Group E", "3rd Group A/B/C/D", "Aviva Stadium", "Dublin"),
    (45, "2028-06-30", "Winner Match 39", "Winner Match 37", "Wembley Stadium", "London"),
    (46, "2028-06-30", "Winner Match 41", "Winner Match 42", "Aviva Stadium", "Dublin"),
    (47, "2028-07-01", "Winner Match 44", "Winner Match 43", "Hampden Park", "Glasgow"),
    (48, "2028-07-01", "Winner Match 40", "Winner Match 38", "Millennium Stadium", "Cardiff"),
    (49, "2028-07-04", "Winner Match 45", "Winner Match 46", "Wembley Stadium", "London"),
    (50, "2028-07-05", "Winner Match 47", "Winner Match 48", "Wembley Stadium", "London"),
    (51, "2028-07-09", "Winner Match 49", "Winner Match 50", "Wembley Stadium", "London"),
]


# ---------------------------------------------------------------------------
# Presentación de placeholders
# ---------------------------------------------------------------------------

_KO_PATTERNS = [
    (re.compile(r"^Winner Group ([A-F])$"), lambda m: f"1.º Grupo {m.group(1)}"),
    (re.compile(r"^Runner-up Group ([A-F])$"), lambda m: f"2.º Grupo {m.group(1)}"),
    (re.compile(r"^3rd Group ([A-F/]+)$"), lambda m: f"3.º ({m.group(1)})"),
    (re.compile(r"^Winner Match (\d+)$"), lambda m: f"Ganador M{m.group(1)}"),
]


def prettify(placeholder: str) -> str:
    """Traduce un placeholder de Wikipedia a español para mostrar (``"A1"`` intacto)."""
    for pat, fn in _KO_PATTERNS:
        m = pat.match(placeholder)
        if m:
            return fn(m)
    return placeholder


# ---------------------------------------------------------------------------
# Construcción del TournamentData
# ---------------------------------------------------------------------------

def _matchday_for(number: int) -> Optional[str]:
    """Jornada de un partido de grupos (1-36) por su número; None en KO."""
    if number <= 12:
        return "J1"
    if number <= 24:
        return "J2"
    if number <= 36:
        return "J3"
    return None


def _build_match(number: int, iso_date: str, home: str, away: str,
                 stadium: str, city: str) -> Match:
    phase = EURO2028_FORMAT.phase_for_number(number)
    group = home[0] if phase is Phase.GROUPS and home[:1].isalpha() else None
    try:
        date = datetime.strptime(iso_date, "%Y-%m-%d") if iso_date else None
    except ValueError:
        date = None
    return Match(
        number=number, phase=phase, matchday=_matchday_for(number), group=group,
        home=home, away=away, date=date, bonus=_BONUS.get(phase, 1),
        city=_CITY_ES.get(city, city), stadium=stadium,
    )


def _rows_to_matches(rows: list[tuple[int, str, str, str, str, str]]) -> list[Match]:
    matches = [_build_match(*row) for row in rows]
    matches.sort(key=lambda m: m.number)
    return matches


def _scrape_wikipedia(timeout: int = 10) -> list[tuple[int, str, str, str, str, str]]:
    """Extrae el calendario del artículo de Wikipedia (cajas ``div.footballbox``)."""
    import requests
    from bs4 import BeautifulSoup

    resp = requests.get(WIKI_URL, timeout=timeout, headers={"User-Agent": "porra/1.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    rows: list[tuple[int, str, str, str, str, str]] = []
    num_re = re.compile(r"Match\s+(\d+)")
    for box in soup.select("div.footballbox"):
        home_el = box.select_one(".fhome")
        away_el = box.select_one(".faway")
        score_el = box.select_one(".fscore")
        right_el = box.select_one(".fright")
        bday_el = box.select_one(".bday")
        if not (home_el and away_el and score_el):
            continue
        m = num_re.search(score_el.get_text(" ", strip=True))
        if not m:
            m = num_re.search(box.select_one(".fevent").get_text(" ", strip=True)
                              if box.select_one(".fevent") else "")
        if not m:
            continue
        number = int(m.group(1))
        home = home_el.get_text(" ", strip=True)
        away = away_el.get_text(" ", strip=True)
        iso_date = bday_el.get_text(strip=True) if bday_el else ""
        stadium = city = ""
        if right_el:
            parts = [p.strip() for p in right_el.get_text(" ", strip=True).split(",")]
            stadium = parts[0] if parts else ""
            city = parts[-1] if len(parts) > 1 else ""
        rows.append((number, iso_date, home, away, stadium, city))
    return rows


def load_calendar() -> list[Match]:
    """Calendario de la Euro 2028: scraping en vivo con fallback al esqueleto."""
    try:
        rows = _scrape_wikipedia()
        if len(rows) >= 40:  # comprobación de cordura (deberían ser 51)
            return _rows_to_matches(rows)
    except Exception:  # noqa: BLE001 — best-effort; el fallback garantiza datos
        pass
    return _rows_to_matches(_SKELETON)


def _euro_rules() -> ScoringRules:
    """Reglas de puntuación: copia de las del Mundial (única fuente en ADMIN.xlsx)."""
    try:
        from .excel_loader import load_scoring_rules
        return load_scoring_rules()
    except Exception:  # noqa: BLE001 — sin Excel, reglas mínimas inertes
        return ScoringRules(points={}, diff_adjust=0.1)


def load_euro2028() -> TournamentData:
    """Construye el :class:`TournamentData` (stub) de la Eurocopa 2028."""
    matches = load_calendar()
    bracket = {m.number: (m.home, m.away) for m in matches if m.phase.is_knockout}
    return TournamentData(
        teams=[], matches=matches, players=[], rules=_euro_rules(),
        bracket=bracket, thirds_table={},
        format=EURO2028_FORMAT, competition_id="euro2028",
    )


if __name__ == "__main__":  # verificación rápida
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        data = load_euro2028()
    print(f"Partidos: {len(data.matches)} (esperado 51)")
    by_phase: dict[str, int] = {}
    for m in data.matches:
        by_phase[m.phase.value] = by_phase.get(m.phase.value, 0) + 1
    print(f"Por fase: {by_phase}")
    print(f"Grupos: {sorted({m.group for m in data.matches if m.group})}")
    print(f"ko_order: {[p.value for p in data.format.ko_order]}")
    print(f"3.er puesto: {data.format.has_third_place} (nº {data.format.third_place_match_number})")
    m1 = data.matches[0]
    print(f"M1: {m1.date} {m1.home}-{m1.away} @ {m1.stadium}, {m1.city} (bonus {m1.bonus}, {m1.matchday})")
    fin = data.matches[-1]
    print(f"Final (M{fin.number}): {prettify(fin.home)} vs {prettify(fin.away)} @ {fin.stadium}, {fin.city}")
