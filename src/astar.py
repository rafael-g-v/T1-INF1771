from __future__ import annotations

import argparse
import heapq
import math
import time
from dataclasses import dataclass, field
from itertools import count

from . import config
from .mapa import Mapa, Posicao


@dataclass
class ResultadoBusca:
    caminho: list
    custo: float
    n_expandidos: int
    n_gerados: int
    expandidos: list = field(default_factory=list)
    fronteira: list = field(default_factory=list)


class LimiteExcedido(Exception):
    def __init__(self, n_expandidos: int):
        super().__init__(f"Busca interrompida após {n_expandidos} expansões.")
        self.n_expandidos = n_expandidos


def a_estrela(problema, registrar=False, limite_expansoes=None):
    inicial = problema.estado_inicial
    g = {inicial: 0}
    pai = {inicial: None}
    ordem = count()

    h_inicial = problema.heuristica(inicial)
    fronteira = [(h_inicial, h_inicial, next(ordem), 0, inicial)]
    n_expandidos = 0
    n_gerados = 1
    expandidos = []

    while fronteira:
        _, _, _, g_no, estado = heapq.heappop(fronteira)
        if g_no > g[estado]:
            continue

        if problema.objetivo(estado):
            sobra = [e for _, _, _, g_e, e in fronteira if g_e == g[e]] if registrar else []
            return ResultadoBusca(
                caminho=_refazer_caminho(pai, estado),
                custo=g_no,
                n_expandidos=n_expandidos,
                n_gerados=n_gerados,
                expandidos=expandidos,
                fronteira=sobra,
            )

        if limite_expansoes is not None and n_expandidos >= limite_expansoes:
            raise LimiteExcedido(n_expandidos)

        n_expandidos += 1
        if registrar:
            expandidos.append(estado)
        for proximo, custo in problema.sucessores(estado):
            novo_g = g_no + custo
            if novo_g < g.get(proximo, math.inf):
                g[proximo] = novo_g
                pai[proximo] = estado
                h = problema.heuristica(proximo)
                heapq.heappush(fronteira, (novo_g + h, h, next(ordem), novo_g, proximo))
                n_gerados += 1

    return None


def _refazer_caminho(pai, estado):
    caminho = []
    while estado is not None:
        caminho.append(estado)
        estado = pai[estado]
    caminho.reverse()
    return caminho


class ProblemaCaminho:
    def __init__(self, mapa: Mapa, origem: Posicao, destino: Posicao, bloqueadas=()):
        self.mapa = mapa
        self.estado_inicial = origem
        self.destino = destino
        self.bloqueadas = frozenset(bloqueadas)

    def objetivo(self, estado: Posicao) -> bool:
        return estado == self.destino

    def sucessores(self, estado: Posicao):
        vizinhos = self.mapa.sucessores(estado)
        if not self.bloqueadas:
            return vizinhos
        return [(v, custo) for v, custo in vizinhos if v not in self.bloqueadas]

    def heuristica(self, estado: Posicao) -> float:
        passos = abs(estado[0] - self.destino[0]) + abs(estado[1] - self.destino[1])
        return passos * self.mapa.custo_minimo


def tabela_de_custos(mapa: Mapa, pontos: list[Posicao]):
    n = len(pontos)
    fim = n - 1
    custos = [[0] * n for _ in range(n)]
    n_buscas = 0
    n_expandidos = 0

    for i in range(n - 1):
        for j in range(i + 1, n):
            bloqueadas = () if j == fim else (pontos[fim],)
            busca = a_estrela(ProblemaCaminho(mapa, pontos[i], pontos[j], bloqueadas))
            if busca is None:
                raise ValueError(
                    f"Não existe caminho entre '{mapa.simbolo(pontos[i])}' "
                    f"e '{mapa.simbolo(pontos[j])}'."
                )
            n_buscas += 1
            n_expandidos += busca.n_expandidos
            custos[i][j] = busca.custo
            custos[j][i] = busca.custo - mapa.custo(pontos[j]) + mapa.custo(pontos[i])

    return custos, n_buscas, n_expandidos


class ProblemaRota:
    def __init__(self, custos, pedagios=None):
        self.custos = custos
        self.n = len(custos) - 2
        self.destino = self.n + 1
        self.todos = (1 << self.n) - 1
        self.estado_inicial = (0, 0)
        self.pedagios = list(pedagios) if pedagios is not None else [0.0] * len(custos)

        self._bits = [(i, 1 << (i - 1)) for i in range(1, self.n + 1)]
        self._ligacao = [
            [min(custos[i][j], custos[j][i]) for j in range(len(custos))]
            for i in range(len(custos))
        ]
        self._inteiros = all(isinstance(c, int) for linha in custos for c in linha)
        self._cache: dict[int, tuple] = {}

    def objetivo(self, estado) -> bool:
        ponto, visitados = estado
        return ponto == self.destino and visitados == self.todos

    def sucessores(self, estado):
        ponto, visitados = estado
        if ponto == self.destino:
            return []
        linha = self.custos[ponto]
        if visitados == self.todos:
            return [((self.destino, visitados), linha[self.destino])]
        return [
            ((i, visitados | bit), linha[i])
            for i, bit in self._bits
            if not visitados & bit
        ]


    def heuristica(self, estado) -> float:
        ponto, visitados = estado
        if visitados == self.todos:
            return 0 if ponto == self.destino else self.custos[ponto][self.destino]

        em_cache = self._cache.get(visitados)
        if em_cache is None:
            restantes = tuple(i for i, bit in self._bits if not visitados & bit)
            base, _ = self.limite_sem_ponto(restantes, self.pedagios)
            em_cache = self._cache[visitados] = (base, restantes)
        base, restantes = em_cache

        linha = self.custos[ponto]
        pedagios = self.pedagios
        chegada = min(linha[u] + pedagios[u] for u in restantes)
        return self._arredondar(base + chegada)

    def limite_sem_ponto(self, restantes, pedagios):
        custos, destino = self.custos, self.destino
        arvore, grau = _arvore_geradora_minima(restantes, self._ligacao, pedagios)
        saida = min(restantes, key=lambda u: custos[u][destino] + pedagios[u])
        grau[saida] += 1
        valor = (
            arvore
            + custos[saida][destino] + pedagios[saida]
            - 2 * sum(pedagios[u] for u in restantes)
        )
        return valor, grau

    def _arredondar(self, valor: float) -> float:
        valor -= 1e-9
        if self._inteiros:
            valor = math.ceil(valor)
        return max(valor, 0)


def _arvore_geradora_minima(nos, ligacao, pedagios):
    grau = {u: 0 for u in nos}
    if len(nos) <= 1:
        return 0, grau

    raiz = nos[0]
    melhor = {u: ligacao[raiz][u] + pedagios[raiz] + pedagios[u] for u in nos[1:]}
    origem = {u: raiz for u in nos[1:]}
    total = 0
    while melhor:
        u = min(melhor, key=melhor.get)
        total += melhor.pop(u)
        grau[u] += 1
        grau[origem[u]] += 1
        linha, pedagio_u = ligacao[u], pedagios[u]
        for v in melhor:
            custo = linha[v] + pedagio_u + pedagios[v]
            if custo < melhor[v]:
                melhor[v] = custo
                origem[v] = u
    return total, grau


def calcular_pedagios(custos, iteracoes=300):
    problema = ProblemaRota(custos)
    n = problema.n
    pedagios = [0.0] * len(custos)
    if n == 0:
        return pedagios

    ginasios = tuple(range(1, n + 1))
    da_origem = custos[0]
    melhor_valor = -math.inf
    melhores = list(pedagios)
    passo = None

    for _ in range(iteracoes):
        valor, grau = problema.limite_sem_ponto(ginasios, pedagios)
        entrada = min(ginasios, key=lambda u: da_origem[u] + pedagios[u])
        grau[entrada] += 1
        valor += da_origem[entrada] + pedagios[entrada]

        if valor > melhor_valor:
            melhor_valor = valor
            melhores = list(pedagios)
        if all(grau[u] == 2 for u in ginasios):
            break
        if passo is None:
            passo = max(1.0, valor / (4 * n))
        for u in ginasios:
            pedagios[u] += passo * (grau[u] - 2)
        passo *= 0.97

    return melhores


@dataclass
class Trecho:
    origem: str
    destino: str
    caminho: list[Posicao]
    custo: float
    expandidos: list[Posicao]
    fronteira: list[Posicao]


@dataclass
class ResultadoRota:
    ordem_ginasios: list[str]
    trechos: list[Trecho]
    caminho: list[Posicao]
    custo_acumulado: list[float]
    custo_rota: float
    expandidos_rota: int
    gerados_rota: int
    buscas_tabela: int
    expandidos_tabela: int
    heuristica_inicial: float


def planejar_rota(mapa: Mapa, usar_pedagios=True, contar_origem=None, limite_expansoes=None):
    if contar_origem is None:
        contar_origem = config.CONTAR_CUSTO_ORIGEM

    simbolos = [mapa.simbolo(mapa.origem), *mapa.ginasios, mapa.simbolo(mapa.destino)]
    pontos = [mapa.origem, *mapa.ginasios.values(), mapa.destino]

    custos, n_buscas, expandidos_tabela = tabela_de_custos(mapa, pontos)

    pedagios = calcular_pedagios(custos) if usar_pedagios else None
    problema = ProblemaRota(custos, pedagios)
    busca = a_estrela(problema, limite_expansoes=limite_expansoes)
    if busca is None:
        raise ValueError("Não foi encontrada rota que visite todos os ginásios.")
    sequencia = [ponto for ponto, _ in busca.caminho]

    destino = pontos[-1]
    trechos = []
    for a, b in zip(sequencia, sequencia[1:]):
        bloqueadas = () if pontos[b] == destino else (destino,)
        trecho = a_estrela(
            ProblemaCaminho(mapa, pontos[a], pontos[b], bloqueadas), registrar=True
        )
        trechos.append(
            Trecho(
                origem=simbolos[a],
                destino=simbolos[b],
                caminho=trecho.caminho,
                custo=trecho.custo,
                expandidos=trecho.expandidos,
                fronteira=trecho.fronteira,
            )
        )

    caminho = [mapa.origem]
    custo_acumulado = [mapa.custo(mapa.origem) if contar_origem else 0]
    for trecho in trechos:
        for celula in trecho.caminho[1:]:
            caminho.append(celula)
            custo_acumulado.append(custo_acumulado[-1] + mapa.custo(celula))

    simbolo_em = {posicao: s for s, posicao in mapa.ginasios.items()}
    ordem_ginasios = []
    for celula in caminho:
        simbolo = simbolo_em.get(celula)
        if simbolo is not None and simbolo not in ordem_ginasios:
            ordem_ginasios.append(simbolo)

    return ResultadoRota(
        ordem_ginasios=ordem_ginasios,
        trechos=trechos,
        caminho=caminho,
        custo_acumulado=custo_acumulado,
        custo_rota=custo_acumulado[-1],
        expandidos_rota=busca.n_expandidos,
        gerados_rota=busca.n_gerados,
        buscas_tabela=n_buscas,
        expandidos_tabela=expandidos_tabela,
        heuristica_inicial=problema.heuristica(problema.estado_inicial),
    )


def desenhar_rota(mapa: Mapa, caminho: list[Posicao]) -> str:
    desenho = [list(linha) for linha in mapa.linhas]
    for l, c in caminho:
        if desenho[l][c] in config.CUSTO_TERRENO:
            desenho[l][c] = "*"
    return "\n".join("".join(linha) for linha in desenho)


def main(argumentos=None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m src.astar",
        description="Rota de menor custo pelos ginásios com A*.",
    )
    parser.add_argument("--mapa", default=None, help="arquivo do mapa (padrão: data/kanto.txt)")
    parser.add_argument(
        "--heuristica",
        choices=("pedagios", "agm"),
        default="pedagios",
        help="pedagios = AGM com pedágios (padrão); agm = AGM simples, para comparar",
    )
    parser.add_argument("--limite", type=int, default=None, help="máximo de expansões do A* da rota")
    parser.add_argument("--desenhar", action="store_true", help="desenha o mapa com a rota")
    args = parser.parse_args(argumentos)

    mapa = Mapa.carregar(args.mapa)
    print(
        f"Mapa: {mapa.altura} linhas x {mapa.largura} colunas, "
        f"{len(mapa.ginasios)} ginásios"
    )
    print(f"Heurística da rota: {'AGM com pedágios' if args.heuristica == 'pedagios' else 'AGM simples'}")

    inicio = time.perf_counter()
    try:
        rota = planejar_rota(
            mapa,
            usar_pedagios=args.heuristica == "pedagios",
            limite_expansoes=args.limite,
        )
    except LimiteExcedido as erro:
        print(f"\n{erro} Nenhuma rota foi encontrada dentro do limite.")
        print(f"Tempo: {time.perf_counter() - inicio:.2f} s")
        return
    tempo = time.perf_counter() - inicio

    print("\nOrdem de visita:")
    print("  " + " -> ".join([rota.trechos[0].origem, *rota.ordem_ginasios, rota.trechos[-1].destino]))

    print("\nTrecho      Custo  Acumulado  Expandidos no mapa")
    acumulado = rota.custo_acumulado[0]
    for trecho in rota.trechos:
        acumulado += trecho.custo
        print(
            f"{trecho.origem} -> {trecho.destino}   {trecho.custo:>7}  {acumulado:>9}  "
            f"{len(trecho.expandidos):>18}"
        )

    print(f"\nCusto da rota: {rota.custo_rota}")
    print(f"Heurística no estado inicial: {rota.heuristica_inicial}")
    print(
        f"A* da ordem dos ginásios: {rota.expandidos_rota} estados expandidos, "
        f"{rota.gerados_rota} gerados"
    )
    print(
        f"A* no mapa (tabela de custos): {rota.buscas_tabela} buscas, "
        f"{rota.expandidos_tabela} estados expandidos"
    )
    print(f"Tempo: {tempo:.2f} s")

    if args.desenhar:
        print("\n" + desenhar_rota(mapa, rota.caminho))


if __name__ == "__main__":
    main()