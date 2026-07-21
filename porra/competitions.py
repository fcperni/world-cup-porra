"""Registro de competiciones de la porra (multi-torneo).

Cada :class:`Competition` describe un torneo concreto (Mundial 2026, Eurocopa
2028…): sus metadatos de presentación, su :class:`~porra.models.TournamentFormat`,
dónde persisten sus resultados y de qué fuentes se scrapean, y un ``loader`` que
devuelve su :class:`~porra.models.TournamentData`.

El paquete ``porra`` permanece libre de Streamlit; la selección de competición
activa vive en :mod:`ui_common` (estado de sesión).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .models import EURO2028_FORMAT, WC2026_FORMAT, TournamentData, TournamentFormat

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass(frozen=True)
class Competition:
    """Una competición que la porra sabe mostrar."""

    id: str
    name: str                       # nombre corto ("Mundial 2026")
    kind: str                       # "WORLD_CUP" | "EURO"
    year: int
    status: str                     # "FINISHED" | "UPCOMING" | "LIVE"
    hero_kicker: str                # línea superior del hero ("Copa Mundial · 2026 · …")
    host_label: str                 # sede(s) ("USA · México · Canadá")
    start_label: str                # texto de arranque ("11 de junio de 2026")
    emoji: str                      # icono de la tarjeta de portada
    fmt: TournamentFormat
    loader: Callable[[], TournamentData]
    results_path: Path
    github_path: str                # ruta del commit de resultados en el repo
    espn_league: str                # liga ESPN para el scraping
    wiki_articles: tuple[str, ...]  # artículos de Wikipedia con resultados

    @property
    def is_open(self) -> bool:
        """¿Hay ya porra jugable (participantes) para esta competición?"""
        return self.status in ("LIVE", "FINISHED")


def _load_wc2026() -> TournamentData:
    from .excel_loader import load_tournament
    return load_tournament()


def _load_euro2028() -> TournamentData:
    from .euro2028 import load_euro2028
    return load_euro2028()


COMPETITIONS: dict[str, Competition] = {
    "wc2026": Competition(
        id="wc2026",
        name="Mundial 2026",
        kind="WORLD_CUP",
        year=2026,
        status="FINISHED",
        hero_kicker="Copa Mundial · 2026 · USA · México · Canadá",
        host_label="USA · México · Canadá",
        start_label="11 de junio de 2026",
        emoji="🌎",
        fmt=WC2026_FORMAT,
        loader=_load_wc2026,
        results_path=_DATA_DIR / "results.json",
        github_path="data/results.json",
        espn_league="fifa.world",
        wiki_articles=(
            "2026_FIFA_World_Cup_group_stage",
            "2026_FIFA_World_Cup_knockout_stage",
            "2026_FIFA_World_Cup",
        ),
    ),
    "euro2028": Competition(
        id="euro2028",
        name="Eurocopa 2028",
        kind="EURO",
        year=2028,
        status="UPCOMING",
        hero_kicker="UEFA EURO · 2028 · Reino Unido · Irlanda",
        host_label="Reino Unido · Irlanda",
        start_label="9 de junio de 2028",
        emoji="🇪🇺",
        fmt=EURO2028_FORMAT,
        loader=_load_euro2028,
        results_path=_DATA_DIR / "results_euro2028.json",
        github_path="data/results_euro2028.json",
        espn_league="uefa.euro",
        wiki_articles=("UEFA_Euro_2028",),
    ),
}

# Orden de presentación en la portada (más reciente/activa primero).
COMPETITION_ORDER = ["wc2026", "euro2028"]
DEFAULT_ID = "wc2026"


def get_competition(comp_id: str | None) -> Competition:
    """Competición por id, con fallback al default si no se reconoce."""
    return COMPETITIONS.get(comp_id or DEFAULT_ID, COMPETITIONS[DEFAULT_ID])
