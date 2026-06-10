"""Fidelidad al Excel: el motor reproduce los MÁXIMOS por categoría que el
propio ADMIN.xlsx declara en la hoja CLAS (fila 3, "Max: …").

Se construye un torneo completo determinista y un "jugador perfecto" cuyas
predicciones coinciden con todos los resultados; su puntuación por categoría
debe igualar exactamente el máximo documentado. Esto valida de extremo a extremo
la fórmula de puntos, los bonus, el conteo de clasificados, el emparejado KO y
el cuadro de honor sin necesidad de recalcular el Excel.
"""

import pytest

from porra.excel_loader import load_tournament
from porra.models import KO_ORDER, KnockoutPrediction, Phase, Player, Prediction
from porra.results_store import Results
from porra.scoring import score_player
from porra.tournament import compute_group_standings, group_positions, resolved_match_teams
from porra.scoring import actual_qualified_teams, actual_honor

# Máximos documentados en CLAS!fila3 (mapeados a las categorías del motor).
DOCUMENTED_MAX = {
    "F. Grupos": 630, "Pos. Grupos": 240,
    "Equipos 1/16": 320, "Partidos 1/16": 576,
    "Equipos 1/8": 240, "Partidos 1/8": 480,
    "Equipos 1/4": 160, "Partidos 1/4": 360,
    "Equipos 1/2": 100, "Partidos 1/2": 360,
    "Equipos 3-4": 60, "Partidos 3-4": 270,
    "Equipos Final": 100, "Partido Final": 405,
    "Cuadro de Honor": 345,
}


@pytest.fixture(scope="module")
def perfect():
    """Devuelve (data, results, jugador_perfecto, score) de un torneo completo."""
    data = load_tournament()
    res = Results()
    rank = {t.name: t.rank for t in data.teams}

    # fase de grupos determinista (gana el de mejor ranking; algún empate)
    for m in data.matches:
        if m.phase is Phase.GROUPS:
            if m.number % 9 == 0:
                res.set_match(m.number, 1, 1)
            elif rank[m.home] < rank[m.away]:
                res.set_match(m.number, 2, 0)
            else:
                res.set_match(m.number, 0, 1)

    # eliminatorias: local gana 2-1 (sin empates -> ganador siempre decidido)
    for _ in range(6):
        teams = resolved_match_teams(data, res)
        for n in range(73, 105):
            if not res.has(n) and teams[n][0] and teams[n][1]:
                res.set_match(n, 2, 1)

    standings = compute_group_standings(data, res)
    positions = group_positions(data, res)
    teams = resolved_match_teams(data, res, standings)
    qualified_actual = actual_qualified_teams(data, teams)

    # botas y balones reales (manuales) para poder alcanzar el máximo de honor
    res.honor.update({
        "bota_oro": "Goleador1", "bota_plata": "Goleador2", "bota_bronce": "Goleador3",
        "balon_oro": "Jugador1", "balon_plata": "Jugador2", "balon_bronce": "Jugador3",
    })
    honor_actual = actual_honor(data, res, teams)

    # jugador perfecto: predice exactamente lo que ocurre
    p = Player(name="PERFECTO", column=-1)
    for m in data.matches:
        if m.phase is Phase.GROUPS:
            h, a = res.goals(m.number)
            p.group_matches[m.number] = Prediction(m.number, f"{res.sign(m.number)}|{h}-{a}",
                                                    res.sign(m.number), h, a)
    for (g, pos), team in positions.items():
        p.group_positions[(g, pos)] = team.name
    for phase in KO_ORDER:
        p.qualified[phase] = list(qualified_actual[phase])
    for m in data.matches:
        if m.phase.is_knockout:
            ht, at = teams[m.number]
            h, a = res.goals(m.number)
            p.ko_matches[m.number] = KnockoutPrediction(
                m.number, "", ht.name, at.name, res.sign(m.number), h, a)
    p.honor = dict(honor_actual)

    score = score_player(data, res, p, positions, teams, qualified_actual, honor_actual)
    return data, res, p, score


@pytest.mark.parametrize("category,maximum", DOCUMENTED_MAX.items())
def test_perfect_player_hits_documented_max(perfect, category, maximum):
    _, _, _, score = perfect
    assert score.categories[category] == pytest.approx(maximum), (
        f"{category}: motor={score.categories[category]} vs Excel={maximum}")


def test_perfect_total(perfect):
    _, _, _, score = perfect
    assert score.total == pytest.approx(sum(DOCUMENTED_MAX.values()))  # 4364
