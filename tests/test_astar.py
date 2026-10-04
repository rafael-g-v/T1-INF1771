import heapq
import itertools
import random
import unittest

from src import config
from src.astar import (
    LimiteExcedido,
    ProblemaCaminho,
    ProblemaRota,
    a_estrela,
    calcular_pedagios,
    planejar_rota,
    tabela_de_custos,
)
from src.mapa import Mapa

CUSTOS = {
    "custo_terreno": {"M": 200, "A": 30, "F": 15, "R": 5, ".": 1},
    "custo_origem_destino": 1,
    "custo_ginasio": 1,
}

CUSTO_OTIMO_KANTO = 1099


def criar_mapa(linhas, **outros_custos):
    return Mapa(linhas, **{**CUSTOS, **outros_custos})


def mapa_aleatorio(gerador, altura, largura, n_ginasios, **outros_custos):
    celulas = [
        gerador.choices("MAFR.", weights=(1, 2, 2, 3, 6))[0]
        for _ in range(altura * largura)
    ]
    simbolos = [config.SIMBOLO_ORIGEM, config.SIMBOLO_DESTINO]
    simbolos += list(config.DIFICULDADE_GINASIOS)[:n_ginasios]
    for indice, simbolo in zip(gerador.sample(range(altura * largura), len(simbolos)), simbolos):
        celulas[indice] = simbolo
    linhas = ["".join(celulas[l * largura:(l + 1) * largura]) for l in range(altura)]
    return criar_mapa(linhas, **outros_custos)


def custo_uniforme(mapa, origem, bloqueadas=()):
    custo = {origem: 0}
    fila = [(0, origem)]
    while fila:
        c, posicao = heapq.heappop(fila)
        if c > custo[posicao]:
            continue
        for vizinho, passo in mapa.sucessores(posicao):
            if vizinho in bloqueadas:
                continue
            if c + passo < custo.get(vizinho, float("inf")):
                custo[vizinho] = c + passo
                heapq.heappush(fila, (c + passo, vizinho))
    return custo


def rota_otima_no_espaco_completo(mapa):
    bit = {posicao: 1 << i for i, posicao in enumerate(mapa.ginasios.values())}
    todos = (1 << len(bit)) - 1
    inicial = (mapa.origem, 0)
    custo = {inicial: 0}
    fila = [(0, inicial)]
    while fila:
        c, estado = heapq.heappop(fila)
        if c > custo[estado]:
            continue
        posicao, visitados = estado
        if posicao == mapa.destino:
            return c
        for vizinho, passo in mapa.sucessores(posicao):
            if vizinho == mapa.destino and visitados != todos:
                continue
            proximo = (vizinho, visitados | bit.get(vizinho, 0))
            if c + passo < custo.get(proximo, float("inf")):
                custo[proximo] = c + passo
                heapq.heappush(fila, (c + passo, proximo))
    return None


def custo_restante_exato(custos, ponto, visitados, memoria):
    n = len(custos) - 2
    destino = n + 1
    chave = (ponto, visitados)
    if chave not in memoria:
        faltam = [i for i in range(1, n + 1) if not visitados & (1 << (i - 1))]
        if not faltam:
            memoria[chave] = 0 if ponto == destino else custos[ponto][destino]
        else:
            memoria[chave] = min(
                custos[ponto][i]
                + custo_restante_exato(custos, i, visitados | (1 << (i - 1)), memoria)
                for i in faltam
            )
    return memoria[chave]


class TesteMapa(unittest.TestCase):
    def test_kanto_tem_o_tamanho_e_os_pontos_do_enunciado(self):
        mapa = Mapa.carregar()
        self.assertEqual((mapa.altura, mapa.largura), (42, 150))
        self.assertEqual(len(mapa.ginasios), 24)
        self.assertEqual(list(mapa.ginasios), list(config.DIFICULDADE_GINASIOS))
        self.assertEqual(mapa.simbolo(mapa.origem), "1")
        self.assertEqual(mapa.simbolo(mapa.destino), "U")

    def test_custo_e_vizinhos(self):
        mapa = criar_mapa(["1MA", "FR.", "2.U"])
        self.assertEqual(mapa.custo((0, 0)), 1)
        self.assertEqual(mapa.custo((0, 1)), 200)
        self.assertEqual(mapa.custo((0, 2)), 30)
        self.assertEqual(mapa.custo((1, 0)), 15)
        self.assertEqual(mapa.custo((1, 1)), 5)
        self.assertEqual(mapa.custo((1, 2)), 1)
        self.assertEqual(mapa.custo((2, 0)), 1)
        self.assertEqual(mapa.custo((2, 2)), 1)
        self.assertEqual(dict(mapa.sucessores((0, 0))), {(1, 0): 15, (0, 1): 200})
        self.assertEqual(len(mapa.sucessores((1, 1))), 4)

    def test_mapa_invalido(self):
        with self.assertRaises(ValueError):
            criar_mapa(["1.U", ".."])
        with self.assertRaises(ValueError):
            criar_mapa(["1.?", "..U"])
        with self.assertRaises(ValueError):
            criar_mapa(["...", "..U"])
        with self.assertRaises(ValueError):
            criar_mapa(["1..", "..."])
        with self.assertRaises(ValueError):
            criar_mapa(["1.2", "2.U"])


class TesteCaminhoNoMapa(unittest.TestCase):
    def test_desvia_da_montanha(self):
        mapa = criar_mapa([
            "1MMM2",
            ".MMM.",
            ".....",
            "....U",
        ])
        busca = a_estrela(ProblemaCaminho(mapa, mapa.origem, mapa.ginasios["2"]))
        self.assertEqual(busca.custo, 8)
        self.assertEqual(busca.caminho[0], mapa.origem)
        self.assertEqual(busca.caminho[-1], mapa.ginasios["2"])
        self.assertTrue(all(mapa.simbolo(p) != "M" for p in busca.caminho))

    def test_sem_caminho_devolve_none(self):
        mapa = criar_mapa(["1.U"])
        busca = a_estrela(ProblemaCaminho(mapa, (0, 0), (0, 2), bloqueadas=[(0, 1)]))
        self.assertIsNone(busca)

    def test_custo_igual_ao_da_busca_de_custo_uniforme(self):
        gerador = random.Random(1771)
        for _ in range(30):
            mapa = mapa_aleatorio(gerador, 9, 12, 3)
            gabarito = custo_uniforme(mapa, mapa.origem)
            for alvo in [mapa.destino, *mapa.ginasios.values()]:
                busca = a_estrela(ProblemaCaminho(mapa, mapa.origem, alvo))
                self.assertEqual(busca.custo, gabarito[alvo])
                self.assertEqual(busca.custo, sum(mapa.custo(p) for p in busca.caminho[1:]))

    def test_manhattan_nunca_superestima(self):
        gerador = random.Random(7)
        for _ in range(10):
            mapa = mapa_aleatorio(gerador, 9, 12, 3)
            do_destino = custo_uniforme(mapa, mapa.destino)
            problema = ProblemaCaminho(mapa, mapa.origem, mapa.destino)
            for posicao, custo in do_destino.items():
                real = custo - mapa.custo(posicao) + mapa.custo(mapa.destino)
                self.assertLessEqual(problema.heuristica(posicao), real)

    def test_registra_expandidos_e_fronteira(self):
        mapa = mapa_aleatorio(random.Random(3), 9, 12, 3)
        busca = a_estrela(ProblemaCaminho(mapa, mapa.origem, mapa.destino), registrar=True)
        self.assertEqual(len(busca.expandidos), busca.n_expandidos)
        self.assertEqual(busca.expandidos[0], mapa.origem)
        self.assertEqual(len(set(busca.expandidos)), len(busca.expandidos))
        self.assertFalse(set(busca.expandidos) & set(busca.fronteira))
        self.assertTrue(set(busca.caminho[:-1]) <= set(busca.expandidos))

    def test_tabela_de_custos_confere_nos_dois_sentidos(self):
        mapa = mapa_aleatorio(random.Random(11), 10, 14, 5)
        pontos = [mapa.origem, *mapa.ginasios.values(), mapa.destino]
        custos, n_buscas, _ = tabela_de_custos(mapa, pontos)
        self.assertEqual(n_buscas, len(pontos) * (len(pontos) - 1) // 2)
        fim = len(pontos) - 1
        for i, origem in enumerate(pontos[:-1]):
            sem_destino = custo_uniforme(mapa, origem, bloqueadas={mapa.destino})
            livre = custo_uniforme(mapa, origem)
            for j, alvo in enumerate(pontos):
                if j == i:
                    continue
                esperado = livre[alvo] if j == fim else sem_destino[alvo]
                self.assertEqual(custos[i][j], esperado)


class TesteOrdemDosGinasios(unittest.TestCase):
    def tabela_aleatoria(self, gerador, n_ginasios):
        mapa = mapa_aleatorio(gerador, 10, 14, n_ginasios)
        pontos = [mapa.origem, *mapa.ginasios.values(), mapa.destino]
        return tabela_de_custos(mapa, pontos)[0]

    def test_heuristica_nunca_superestima(self):
        gerador = random.Random(42)
        for _ in range(15):
            custos = self.tabela_aleatoria(gerador, 5)
            n = len(custos) - 2
            opcoes = [
                None,
                calcular_pedagios(custos),
                [gerador.uniform(-30, 30) for _ in custos],
            ]
            for pedagios in opcoes:
                problema = ProblemaRota(custos, pedagios)
                memoria = {}
                for visitados in range(1 << n):
                    pontos_possiveis = [0] if visitados == 0 else [
                        i for i in range(1, n + 1) if visitados & (1 << (i - 1))
                    ]
                    for ponto in pontos_possiveis:
                        real = custo_restante_exato(custos, ponto, visitados, memoria)
                        self.assertLessEqual(problema.heuristica((ponto, visitados)), real)
                self.assertEqual(problema.heuristica((n + 1, (1 << n) - 1)), 0)

    def test_a_estrela_acha_o_mesmo_custo_da_forca_bruta(self):
        gerador = random.Random(2026)
        for _ in range(15):
            custos = self.tabela_aleatoria(gerador, 6)
            n = len(custos) - 2
            forca_bruta = min(
                custos[0][ordem[0]]
                + sum(custos[a][b] for a, b in zip(ordem, ordem[1:]))
                + custos[ordem[-1]][n + 1]
                for ordem in itertools.permutations(range(1, n + 1))
            )
            for pedagios in (None, calcular_pedagios(custos)):
                busca = a_estrela(ProblemaRota(custos, pedagios))
                self.assertEqual(busca.custo, forca_bruta)
                visitados = [ponto for ponto, _ in busca.caminho]
                self.assertEqual(visitados[0], 0)
                self.assertEqual(visitados[-1], n + 1)
                self.assertEqual(sorted(visitados[1:-1]), list(range(1, n + 1)))

    def test_pedagios_expandem_menos_que_a_agm_simples(self):
        gerador = random.Random(5)
        custos = self.tabela_aleatoria(gerador, 9)
        simples = a_estrela(ProblemaRota(custos))
        com_pedagios = a_estrela(ProblemaRota(custos, calcular_pedagios(custos)))
        self.assertEqual(simples.custo, com_pedagios.custo)
        self.assertLessEqual(com_pedagios.n_expandidos, simples.n_expandidos)

    def test_limite_de_expansoes(self):
        custos = self.tabela_aleatoria(random.Random(9), 6)
        with self.assertRaises(LimiteExcedido):
            a_estrela(ProblemaRota(custos), limite_expansoes=2)


class TesteRotaCompleta(unittest.TestCase):
    def conferir_rota(self, mapa, rota):
        self.assertEqual(rota.caminho[0], mapa.origem)
        self.assertEqual(rota.caminho[-1], mapa.destino)
        self.assertNotIn(mapa.destino, rota.caminho[:-1])
        for (l1, c1), (l2, c2) in zip(rota.caminho, rota.caminho[1:]):
            self.assertEqual(abs(l1 - l2) + abs(c1 - c2), 1)
        self.assertEqual(sorted(rota.ordem_ginasios), sorted(mapa.ginasios))
        self.assertTrue(set(mapa.ginasios.values()) <= set(rota.caminho))
        self.assertEqual(len(rota.custo_acumulado), len(rota.caminho))
        self.assertEqual(rota.custo_rota, sum(mapa.custo(p) for p in rota.caminho[1:]))
        self.assertEqual(rota.custo_rota, sum(t.custo for t in rota.trechos))
        self.assertEqual(rota.custo_acumulado[-1], rota.custo_rota)
        self.assertLessEqual(rota.heuristica_inicial, rota.custo_rota)
        self.assertEqual(len(rota.trechos), len(mapa.ginasios) + 1)
        self.assertEqual(rota.trechos[0].origem, "1")
        self.assertEqual(rota.trechos[-1].destino, "U")
        for anterior, seguinte in zip(rota.trechos, rota.trechos[1:]):
            self.assertEqual(anterior.destino, seguinte.origem)
            self.assertEqual(anterior.caminho[-1], seguinte.caminho[0])

    def test_igual_ao_otimo_no_espaco_completo(self):
        gerador = random.Random(99)
        for _ in range(25):
            mapa = mapa_aleatorio(gerador, 7, 9, 4)
            rota = planejar_rota(mapa, contar_origem=False)
            self.conferir_rota(mapa, rota)
            self.assertEqual(rota.custo_rota, rota_otima_no_espaco_completo(mapa))

    def test_ginasio_com_custo_diferente_da_origem(self):
        gerador = random.Random(123)
        for _ in range(25):
            mapa = mapa_aleatorio(gerador, 7, 9, 4, custo_ginasio=40, custo_origem_destino=3)
            rota = planejar_rota(mapa, contar_origem=False)
            self.conferir_rota(mapa, rota)
            self.assertEqual(rota.custo_rota, rota_otima_no_espaco_completo(mapa))

    def test_contar_origem_soma_o_custo_da_origem(self):
        mapa = mapa_aleatorio(random.Random(4), 7, 9, 3)
        sem = planejar_rota(mapa, contar_origem=False)
        com = planejar_rota(mapa, contar_origem=True)
        self.assertEqual(com.custo_rota, sem.custo_rota + mapa.custo(mapa.origem))
        self.assertEqual(com.caminho, sem.caminho)

    def test_mapa_sem_ginasios(self):
        mapa = criar_mapa(["1..", ".M.", "..U"])
        rota = planejar_rota(mapa, contar_origem=False)
        self.assertEqual(rota.ordem_ginasios, [])
        self.assertEqual(rota.custo_rota, 4)

    def test_kanto(self):
        mapa = Mapa.carregar(**CUSTOS)
        rota = planejar_rota(mapa, contar_origem=False)
        self.conferir_rota(mapa, rota)
        self.assertEqual(len(rota.ordem_ginasios), 24)
        self.assertEqual(rota.custo_rota, CUSTO_OTIMO_KANTO)


if __name__ == "__main__":
    unittest.main()