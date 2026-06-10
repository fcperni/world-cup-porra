"""Motor de puntuación — reproduce las fórmulas de ADMIN.xlsx en Python.

**Partidos** (grupos y eliminatorias) — fórmula de la celda T6/T164 con
``D50`` = 0.1:

* Predicción exacta (signo y marcador) → ``(signo + diferencia + exacto) * bonus``.
* Solo signo acertado → ``(signo + crédito_diferencia) * bonus`` con
  ``crédito = max(0, diferencia * (1 - dist * 0.1))``; ``dist`` =
  ``|local_real - local_predicho|`` en empates o ``|dif_real - dif_predicha|``.
* En otro caso → 0.

En **eliminatorias** además hay que acertar la **pareja** de selecciones del
cruce (en cualquier orden); el signo/marcador se evalúa en el orden del jugador.

**Clasificados** (``COUNTIF``) → puntos por cada selección que el jugador sitúa
en una ronda y que realmente la alcanza.

**Cuadro de honor** → comparación directa de nombres. Campeón/subcampeón/3º se
deducen de los partidos 104 y 103; botas y balones son de entrada manual.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import KO_ORDER, Phase, Player, Team, TournamentData
from .results_store import Results
from .tournament import compute_group_standings, group_positions, resolve_bracket

CATEGORIES = [
    "F. Grupos", "Pos. Grupos",
    "Equipos 1/16", "Partidos 1/16",
    "Equipos 1/8", "Partidos 1/8",
    "Equipos 1/4", "Partidos 1/4",
    "Equipos 1/2", "Partidos 1/2",
    "Equipos 3-4", "Partidos 3-4",
    "Equipos Final", "Partido Final",
    "Cuadro de Honor",
]

# Fase -> (categoría "Equipos…", categoría "Partidos…")
_PHASE_CATEGORIES = {
    Phase.R32: ("Equipos 1/16", "Partidos 1/16"),
    Phase.R16: ("Equipos 1/8", "Partidos 1/8"),
    Phase.QF: ("Equipos 1/4", "Partidos 1/4"),
    Phase.SF: ("Equipos 1/2", "Partidos 1/2"),
    Phase.THIRD: ("Equipos 3-4", "Partidos 3-4"),
    Phase.FINAL: ("Equipos Final", "Partido Final"),
}

HONOR_POINTS_KEY = "honor"


@dataclass
class PlayerScore:
    name: str
    categories: dict[str, float] = field(default_factory=lambda: {c: 0.0 for c in CATEGORIES})

    @property
    def total(self) -> float:
        return sum(self.categories.values())


# ---------------------------------------------------------------------------
# Puntuación de un partido (común a grupos y eliminatorias)
# ---------------------------------------------------------------------------

def diff_credit(rules, phase: Phase, actual_sign: str, actual_h: int, actual_a: int,
                pred_h: int, pred_a: int) -> float:
    base = rules.points.get((phase, "diferencia"))
    if base is None:
        return 0.0
    adjust = rules.diff_adjust
    actual_diff = abs(actual_h - actual_a)
    pred_diff = abs(pred_h - pred_a)
    if adjust == 1:  # rama vestigial del Excel (D50=1)
        dist = abs(actual_diff - pred_diff)
    elif actual_sign == "X":
        dist = abs(actual_h - pred_h)
    else:
        dist = abs(actual_diff - pred_diff)
    return max(0.0, base * (1 - dist * adjust))


def score_match(rules, phase: Phase, bonus: int,
                pred_sign, pred_h, pred_a, actual_sign, actual_h, actual_a) -> float:
    if pred_sign is None or actual_sign is None:
        return 0.0
    p_signo = rules.points.get((phase, "signo"), 0.0)
    p_exacto = rules.points.get((phase, "exacto"), 0.0)
    p_dif = rules.points.get((phase, "diferencia"), 0.0)
    if (pred_sign, pred_h, pred_a) == (actual_sign, actual_h, actual_a):
        return (p_signo + p_dif + p_exacto) * bonus
    if pred_sign == actual_sign:
        return (p_signo + diff_credit(rules, phase, actual_sign, actual_h, actual_a,
                                      pred_h, pred_a)) * bonus
    return 0.0


# ---------------------------------------------------------------------------
# Categorías
# ---------------------------------------------------------------------------

def score_group_matches(data: TournamentData, results: Results, player: Player) -> float:
    total = 0.0
    for m in data.matches:
        if m.phase is not Phase.GROUPS or not results.has(m.number):
            continue
        pred = player.group_matches.get(m.number)
        if pred is None or not pred.valid:
            continue
        ah, aa = results.goals(m.number)
        total += score_match(data.rules, Phase.GROUPS, m.bonus,
                             pred.sign, pred.home_goals, pred.away_goals,
                             results.sign(m.number), ah, aa)
    return total


def score_group_positions(data: TournamentData, results: Results, player: Player,
                          positions: dict) -> float:
    played: dict[str, int] = {}
    for m in data.matches:
        if m.phase is Phase.GROUPS and results.has(m.number):
            played[m.group] = played.get(m.group, 0) + 1
    complete = {g for g, n in played.items() if n == 6}

    total = 0.0
    for (group, pos), team in positions.items():
        if group not in complete:
            continue
        predicted = player.group_positions.get((group, pos))
        if predicted and predicted == team.name:
            total += data.rules.points.get(("group_position", pos), 0.0)
    return total


def actual_qualified_teams(data: TournamentData, resolved_teams: dict) -> dict[Phase, set[str]]:
    """Selecciones que realmente alcanzan cada fase eliminatoria (las que juegan)."""
    out: dict[Phase, set[str]] = {ph: set() for ph in KO_ORDER}
    for m in data.matches:
        if not m.phase.is_knockout:
            continue
        ht, at = resolved_teams.get(m.number, (None, None))
        for t in (ht, at):
            if t is not None:
                out[m.phase].add(t.name)
    return out


def score_qualified(data: TournamentData, player: Player, phase: Phase,
                    qualified_actual: set[str]) -> float:
    pts = data.rules.points.get((phase, "clasificado"), 0.0)
    return pts * sum(1 for name in player.qualified.get(phase, []) if name in qualified_actual)


def score_ko_matches(data: TournamentData, results: Results, player: Player, phase: Phase,
                     resolved_teams: dict) -> float:
    """Puntos de los partidos de una ronda KO.

    Reproduce el COUNTIF del Excel: el jugador acierta si la **pareja** de
    selecciones que predijo se enfrenta realmente en esta ronda (en cualquier
    orden); el resultado se evalúa en el orden que el jugador eligió.
    """
    # partidos reales de la fase con resultado y ambas selecciones determinadas
    actual = []
    for m in data.matches:
        if m.phase is not phase or not results.has(m.number):
            continue
        ht, at = resolved_teams.get(m.number, (None, None))
        if ht and at:
            actual.append((m, ht.name, at.name))

    total = 0.0
    for pred in player.ko_matches.values():
        m_obj = data.match_by_number(pred.match_number)
        if m_obj is None or m_obj.phase is not phase:
            continue
        if not pred.home_team or not pred.away_team or pred.sign is None:
            continue
        pair = {pred.home_team, pred.away_team}
        for m, ah_name, aa_name in actual:
            if {ah_name, aa_name} != pair:
                continue
            agh, aga = results.goals(m.number)
            if ah_name == pred.home_team:  # mismo orden que el jugador
                a_sign, a_h, a_a = results.sign(m.number), agh, aga
            else:  # orden invertido: trasponer el resultado real
                a_h, a_a = aga, agh
                a_sign = "1" if a_h > a_a else "2" if a_h < a_a else "X"
            total += score_match(data.rules, phase, m.bonus,
                                pred.sign, pred.home_goals, pred.away_goals, a_sign, a_h, a_a)
            break
    return total


def actual_honor(data: TournamentData, results: Results, resolved_teams: dict) -> dict[str, str | None]:
    """Cuadro de honor real: campeón/subcampeón/3º del cuadro; botas/balones manuales."""
    honor: dict[str, str | None] = {}
    final = resolved_teams.get(104, (None, None))
    third = resolved_teams.get(103, (None, None))
    side_final = results.winner_side(104)
    if side_final and final[0] and final[1]:
        champ = final[0] if side_final == "home" else final[1]
        runner = final[1] if side_final == "home" else final[0]
        honor["campeon"], honor["subcampeon"] = champ.name, runner.name
    side_third = results.winner_side(103)
    if side_third and third[0] and third[1]:
        honor["tercero"] = (third[0] if side_third == "home" else third[1]).name
    # botas y balones (manual)
    for key in ("bota_oro", "bota_plata", "bota_bronce", "balon_oro", "balon_plata", "balon_bronce"):
        honor[key] = results.honor.get(key)
    return honor


def score_honor(data: TournamentData, player: Player, honor_actual: dict[str, str | None]) -> float:
    total = 0.0
    for key, actual in honor_actual.items():
        if actual and player.honor.get(key) and player.honor[key] == actual:
            total += data.rules.points.get((HONOR_POINTS_KEY, key), 0.0)
    return total


# ---------------------------------------------------------------------------
# Agregación
# ---------------------------------------------------------------------------

def score_player(data: TournamentData, results: Results, player: Player,
                 positions: dict | None = None, resolved_teams: dict | None = None,
                 qualified_actual: dict | None = None, honor_actual: dict | None = None,
                 ) -> PlayerScore:
    if positions is None:
        positions = group_positions(data, results)
    if resolved_teams is None:
        from .tournament import resolved_match_teams
        resolved_teams = resolved_match_teams(data, results)
    if qualified_actual is None:
        qualified_actual = actual_qualified_teams(data, resolved_teams)
    if honor_actual is None:
        honor_actual = actual_honor(data, results, resolved_teams)

    s = PlayerScore(name=player.name)
    s.categories["F. Grupos"] = score_group_matches(data, results, player)
    s.categories["Pos. Grupos"] = score_group_positions(data, results, player, positions)
    for phase, (eq_cat, pa_cat) in _PHASE_CATEGORIES.items():
        s.categories[eq_cat] = score_qualified(data, player, phase, qualified_actual[phase])
        s.categories[pa_cat] = score_ko_matches(data, results, player, phase, resolved_teams)
    s.categories["Cuadro de Honor"] = score_honor(data, player, honor_actual)
    return s


def scoreboard(data: TournamentData, results: Results) -> list[PlayerScore]:
    positions = group_positions(data, results)
    standings = compute_group_standings(data, results)
    from .tournament import resolved_match_teams
    resolved_teams = resolved_match_teams(data, results, standings)
    qualified_actual = actual_qualified_teams(data, resolved_teams)
    honor_actual = actual_honor(data, results, resolved_teams)
    scores = [score_player(data, results, p, positions, resolved_teams, qualified_actual, honor_actual)
              for p in data.players]
    scores.sort(key=lambda s: s.total, reverse=True)
    return scores
