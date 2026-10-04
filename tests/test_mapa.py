import pytest

from src import config
from src.mapa import Mapa


def test_carrega_mapa_kanto():
    m = Mapa.carregar()
    assert (m.altura, m.largura) == (42, 150)
    assert m.origem == (23, 35)
    assert m.destino == (1, 16)
    assert len(m.ginasios) == 24
    assert set(m.ginasios) == set(config.DIFICULDADE_GINASIOS)


def test_custos():
    m = Mapa(["1MAFR.U"])
    assert [m.custo(0, c) for c in range(7)] == [1, 200, 30, 15, 5, 1, 1]


def test_vizinhos_sem_diagonal():
    m = Mapa(["1..", "...", "..U"])
    assert sorted(m.vizinhos(0, 0)) == [(0, 1), (1, 0)]
    assert len(list(m.vizinhos(1, 1))) == 4


def test_simbolo_desconhecido():
    with pytest.raises(ValueError):
        Mapa(["1?U"])
