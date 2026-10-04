"""Replay de demonstração (NÃO é a solução do trabalho).

Faz um A* simples perna a perna (ginásio mais próximo primeiro) só para gerar
eventos realistas e permitir desenvolver a interface sem depender do A* final.
"""
import heapq
import json

from . import config
from .replay import EXPANDIR, GERAR, NOVA, Replay


def _perna(mapa, ini, fim, eventos):
    def h(p):
        return abs(p[0] - fim[0]) + abs(p[1] - fim[1])

    eventos.append((NOVA, 0, 0))
    g = {ini: 0}
    pai = {}
    fechado = set()
    heap = [(h(ini), 0, ini)]
    while heap:
        _, gc, p = heapq.heappop(heap)
        if p in fechado:
            continue
        fechado.add(p)
        eventos.append((EXPANDIR, *p))
        if p == fim:
            break
        for v in mapa.vizinhos(*p):
            ng = gc + mapa.custo(*v)
            if ng < g.get(v, float("inf")):
                g[v] = ng
                pai[v] = p
                heapq.heappush(heap, (ng + h(v), ng, v))
                eventos.append((GERAR, *v))
    caminho = [fim]
    while caminho[-1] != ini:
        caminho.append(pai[caminho[-1]])
    return caminho[::-1]


def gerar_replay(mapa):
    eventos = []
    caminho = [mapa.origem]
    restantes = dict(mapa.ginasios)
    while restantes:
        atual = caminho[-1]
        g = min(restantes, key=lambda k: abs(restantes[k][0] - atual[0]) + abs(restantes[k][1] - atual[1]))
        perna = _perna(mapa, atual, restantes.pop(g), eventos)
        caminho += perna[1:]
        for p in perna:  # ginásios pisados no meio do caminho já contam como visitados
            restantes.pop(mapa.ginasio_em.get(p), None)
    caminho += _perna(mapa, caminho[-1], mapa.destino, eventos)[1:]
    arq = config.RAIZ / "data" / "demo_busca_local.json"
    pokemons = json.loads(arq.read_text(encoding="utf-8"))
    return Replay(eventos, caminho, pokemons, rotulo="A* (demo)")
