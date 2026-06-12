"""Validación del motor de puntuación frente a casos calculados a mano."""

import pytest

from porra.excel_loader import load_tournament
from porra.models import Phase
from porra.results_store import Results
from porra.scoring import position_history, score_match


@pytest.fixture(scope="module")
def rules():
    return load_tournament().rules


def s(rules, bonus, ph, pa, ah, aa):
    """Atajo: predicción ph-pa (signo deducido) vs resultado real ah-aa."""
    psign = "1" if ph > pa else "2" if ph < pa else "X"
    asign = "1" if ah > aa else "2" if ah < aa else "X"
    return score_match(rules, Phase.GROUPS, bonus, psign, ph, pa, asign, ah, aa)


def test_exacto(rules):
    # signo(1)+diferencia(3)+exacto(3) = 7
    assert s(rules, 1, 2, 1, 2, 1) == 7


def test_exacto_con_bonus(rules):
    assert s(rules, 3, 2, 1, 2, 1) == 21


def test_signo_y_diferencia_exacta(rules):
    # pred 3-1 (dif 2, signo 1) vs real 2-0 (dif 2, signo 1): dist 0 -> 1 + 3 = 4
    assert s(rules, 1, 3, 1, 2, 0) == 4


def test_signo_diferencia_off_by_one(rules):
    # pred 2-0 (dif 2) vs real 1-0 (dif 1): dist 1 -> 1 + 3*(1-0.1) = 3.7
    assert s(rules, 1, 2, 0, 1, 0) == pytest.approx(3.7)


def test_empate_distancia_por_goles(rules):
    # pred 2-2 vs real 1-1 (empate): dist |1-2| = 1 -> 1 + 3*0.9 = 3.7
    assert s(rules, 1, 2, 2, 1, 1) == pytest.approx(3.7)


def test_empate_exacto(rules):
    assert s(rules, 1, 1, 1, 1, 1) == 7


def test_empate_distancia_grande(rules):
    # pred 5-5 vs real 0-0: dist 5 -> 1 + 3*(1-0.5) = 2.5
    assert s(rules, 1, 5, 5, 0, 0) == pytest.approx(2.5)


def test_credito_no_negativo(rules):
    # pred 9-0 (dif 9) vs real 1-0 (dif 1): dist 8 -> 3*(1-0.8)=0.6 -> 1.6
    assert s(rules, 1, 9, 0, 1, 0) == pytest.approx(1.6)
    # dist 10+ -> crédito acotado a 0, solo signo
    assert s(rules, 1, 12, 0, 1, 0) == pytest.approx(1.0)


def test_signo_fallado(rules):
    # pred local gana vs real visitante gana -> 0
    assert s(rules, 1, 2, 1, 0, 1) == 0


# --------------------------------------------------------------- evolución de posiciones

def test_position_history_vacio_sin_resultados():
    data = load_tournament()
    days, history = position_history(data, Results())
    assert days == []
    assert all(positions == [] for positions in history.values())


def test_position_history_un_dia_por_fecha_y_rango_valido():
    data = load_tournament()
    res = Results()
    # primeros 12 partidos de grupos (reparten varias fechas), resultados variados
    gm = [m for m in data.matches if m.phase is Phase.GROUPS and m.date][:12]
    for i, m in enumerate(gm):
        res.set_match(m.number, i % 3, (i + 1) % 3)

    days, history = position_history(data, res)
    n = len(data.players)

    # un día por fecha distinta con resultado, en orden ascendente
    fechas = sorted({m.date.date() for m in gm})
    assert days == fechas
    # cada jugador tiene una posición por día y todas están en [1, n]
    assert set(history) == {p.name for p in data.players}
    assert all(len(positions) == len(days) for positions in history.values())
    assert all(1 <= v <= n for positions in history.values() for v in positions)
    # ranking de competición: cada día hay un líder (posición 1)
    for di in range(len(days)):
        assert min(positions[di] for positions in history.values()) == 1
