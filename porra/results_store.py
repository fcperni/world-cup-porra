"""Almacén de resultados introducidos (manual o por scraping).

Persiste en ``data/results.json``. La fuente de predicciones sigue siendo
``ADMIN.xlsx`` (solo lectura); aquí solo guardamos lo que va ocurriendo en el
Mundial: goles de cada partido y el cuadro de honor real.

El commit al repositorio (Streamlit Cloud) se añade en :mod:`porra.github_sync`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

DEFAULT_RESULTS = Path(__file__).resolve().parent.parent / "data" / "results.json"

HONOR_KEYS = [
    "campeon", "subcampeon", "tercero",
    "bota_oro", "bota_plata", "bota_bronce",
    "balon_oro", "balon_plata", "balon_bronce",
]


@dataclass
class Results:
    """Resultados conocidos del torneo."""

    # nº de partido -> (goles_local, goles_visitante)
    matches: dict[int, tuple[int, int]] = field(default_factory=dict)
    # cuadro de honor real (entrada manual): clave -> nombre
    honor: dict[str, Optional[str]] = field(default_factory=dict)
    # ganador en eliminatorias cuando hay empate (penaltis): nº -> "home"/"away"
    ko_winners: dict[int, str] = field(default_factory=dict)

    def has(self, number: int) -> bool:
        return number in self.matches

    def winner_side(self, number: int) -> Optional[str]:
        """"home"/"away" del que avanza en KO, o None si no decidido."""
        g = self.matches.get(number)
        if g is None:
            return None
        h, a = g
        if h > a:
            return "home"
        if h < a:
            return "away"
        return self.ko_winners.get(number)  # empate -> ganador por penaltis

    def goals(self, number: int) -> Optional[tuple[int, int]]:
        return self.matches.get(number)

    def sign(self, number: int) -> Optional[str]:
        """Signo 1X2 del resultado real, o None si no se ha jugado."""
        g = self.matches.get(number)
        if g is None:
            return None
        h, a = g
        return "1" if h > a else "2" if h < a else "X"

    def result_string(self, number: int) -> Optional[str]:
        """Resultado en el formato del Excel ``"signo|local-visitante"``."""
        g = self.matches.get(number)
        if g is None:
            return None
        h, a = g
        return f"{self.sign(number)}|{h}-{a}"

    def set_match(self, number: int, home: Optional[int], away: Optional[int]) -> None:
        """Fija o borra (si home/away None) el resultado de un partido."""
        if home is None or away is None:
            self.matches.pop(number, None)
        else:
            self.matches[number] = (int(home), int(away))


def load_results(path: Path | str = DEFAULT_RESULTS) -> Results:
    path = Path(path)
    if not path.exists():
        return Results(honor={k: None for k in HONOR_KEYS})
    raw = json.loads(path.read_text(encoding="utf-8"))
    matches = {int(k): (int(v["home"]), int(v["away"])) for k, v in raw.get("matches", {}).items()}
    honor = {k: raw.get("honor", {}).get(k) for k in HONOR_KEYS}
    ko_winners = {int(k): str(v) for k, v in raw.get("ko_winners", {}).items()}
    return Results(matches=matches, honor=honor, ko_winners=ko_winners)


def to_dict(results: Results) -> dict:
    return {
        "matches": {str(n): {"home": h, "away": a} for n, (h, a) in sorted(results.matches.items())},
        "honor": {k: results.honor.get(k) for k in HONOR_KEYS},
        "ko_winners": {str(n): s for n, s in sorted(results.ko_winners.items())},
    }


def save_results(results: Results, path: Path | str = DEFAULT_RESULTS) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_dict(results), ensure_ascii=False, indent=2), encoding="utf-8")
