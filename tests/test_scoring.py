"""Validación del motor de puntuación frente a casos calculados a mano."""

import pytest

from porra.excel_loader import load_tournament
from porra.models import Phase
from porra.scoring import score_match


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
