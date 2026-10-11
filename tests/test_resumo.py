from src.mapa import Mapa
from src.resumo import calcular_resumo

CAMINHO = [(0, i) for i in range(5)]  # 1 . 2 . U
ACUMULADO = [0, 1, 2, 3, 4]


def _mapa():
    return Mapa(["1.2.U"])


def test_custos_e_energia():
    m = _mapa()
    r = calcular_resumo(m, CAMINHO, ACUMULADO, {"2": ["Pikachu"]})
    assert r.custo_rota == 4
    assert abs(r.custo_batalhas - 35 / 1.5) < 1e-9
    assert abs(r.custo_total - (4 + 35 / 1.5)) < 1e-9
    assert r.ordem == ["2"]
    assert r.energia_final["Pikachu"] == 5
    assert r.energia_final["Weedle"] == 6
    assert r.avisos == []


def test_acumulados_por_passo():
    m = _mapa()
    r = calcular_resumo(m, CAMINHO, ACUMULADO, {"2": ["Pikachu"]})
    assert r.rota_acum == ACUMULADO
    assert r.bat_acum[1] == 0 and r.bat_acum[2] > 0
    assert r.batalhas_ate == [0, 0, 1, 1, 1]


def test_avisos():
    m = _mapa()
    r = calcular_resumo(m, CAMINHO, ACUMULADO, {})
    assert any("sem Pokémons" in a for a in r.avisos)
    r = calcular_resumo(m, CAMINHO[:3], ACUMULADO[:3], {"2": ["Pikachu"]})
    assert any("não termina no destino" in a for a in r.avisos)
    r = calcular_resumo(m, [(0, 0), (0, 4)], [0, 4], {})
    assert any("não visitados" in a for a in r.avisos)
    assert any("não adjacente" in a for a in r.avisos)
