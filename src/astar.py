import heapq
import json


def convert_map(terrain):
    """
    Converte a matriz de caracteres lida do arquivo em uma matriz de custos de terreno,
    substituindo cada caractere pelo custo correspondente (ou pelo nome do ponto, 
    quando a célula for um ponto especial como init, OBJ ou G1-G24).
    Também monta o dicionário de coordenadas de cada ponto especial.
    """
    terrain_dict = {
        "M": 200, "A": 30, "F": 15, "R": 5, ".": 1,
        "2": "G1", "3": "G2", "4": "G3", "5": "G4", "6": "G5",
        "7": "G6", "8": "G7", "9": "G8", "B": "G9", "C": "G10",
        "D": "G11", "E": "G12", "G": "G13", "H": "G14", "I": "G15",
        "J": "G16", "K": "G17", "L": "G18", "N": "G19", "O": "G20",
        "P": "G21", "Q": "G22", "S": "G23", "T": "G24", "U": "OBJ",
        "1": "init"
    }

    coordenadas = {}

    for i in range(len(terrain)):
        for j in range(len(terrain[i])):
            terrain[i][j] = terrain_dict[terrain[i][j]]
            if type(terrain[i][j]) == str:
                coordenadas[terrain[i][j]] = [i, j]

    return terrain, coordenadas


def read_txt(path):
    """
    Lê o arquivo de mapa linha a linha e monta a matriz de caracteres bruta,
    depois chama convert_map para transformar isso em custos e coordenadas.
    """
    terrain = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            terrain.append(list(line))
    return convert_map(terrain)


def custo_celula(terrain, c):
    cell = terrain[c[0]][c[1]]
    if cell == "init" or cell == "OBJ":
        return 1
    if type(cell) == str:
        return 0
    return cell


def astar(origem, destino, terrain):
    """
    Busca o caminho mais barato entre dois pontos do grid usando A* padrão,
    com heurística de distância de Manhattan e movimento em 4 direções.
    Devolve o custo do caminho, o caminho e as células exploradas.
    """
    heap = [[abs(origem[0]-destino[0]) + abs(origem[1]-destino[1]), 0, origem]]
    g_score = {tuple(origem): 0}
    parent = {tuple(origem): None}
    closed = set()

    while heap:
        menor = heapq.heappop(heap)
        coord = menor[2]
        coord_key = tuple(coord)

        if coord == destino:
            caminho = []
            while coord_key is not None:
                caminho.insert(0, list(coord_key))
                coord_key = parent[coord_key]
            return menor[1], caminho
        if coord_key in closed:
            continue
        closed.add(coord_key)

        adj = [[coord[0]+di, coord[1]+dj] for di, dj in [(-1,0),(1,0),(0,-1),(0,1)]]
        adj = [c for c in adj if 0 <= c[0] < len(terrain) and 0 <= c[1] < len(terrain[0])]

        for adj_i in adj:
            adj_key = tuple(adj_i)
            if adj_key in closed:
                continue
            g_n = menor[1] + custo_celula(terrain, adj_i)
            if adj_key not in g_score or g_n < g_score[adj_key]:
                g_score[adj_key] = g_n
                parent[adj_key] = coord_key
                h_n = abs(adj_i[0]-destino[0]) + abs(adj_i[1]-destino[1])
                heapq.heappush(heap, [g_n+h_n, g_n, adj_i])


def montar_matriz(coordenadas, terrain, pontos):
    """
    Roda o A* do grid entre todo par de pontos especiais e monta a matriz de distâncias
    """
    M = [[0]*len(pontos) for _ in pontos]
    caminhos = {}
    for i in range(len(pontos)):
        for j in range(i+1, len(pontos)):
            custo, caminho = astar(coordenadas[pontos[i]], coordenadas[pontos[j]], terrain)
            M[i][j] = M[j][i] = custo
            caminhos[(i, j)] = caminho
            caminhos[(j, i)] = caminho[::-1]
    return M, caminhos


def mst(nos, M):
    """
    Devolve o custo da árvore geradora minima e o grau de cada no
    A função recebe a lista de nos (ginasios + ponto inicial + objetivo) e uma matriz de custos M
    M pode ser a matriz de distancias, mas também pode ser uma outra matriz de custo
    """
    total = 0
    graus = {n:0 for n in nos}
    arvore = [nos[0]]
    while(True in [graus[n]==0 for n in graus]):
        best = None
        for n in nos:
            if n in arvore:
                continue
            for narv in arvore:
                d = M[narv][n]
                if best == None or d < best[0]:
                    best = [d, [narv,n]]
        total += best[0]
        arvore.append(best[1][1])
        for n in best[1]:
            graus[n] += 1
    return total, graus


def calcula_pesos(M):
    """
    O MST devolve uma árvore que pode ser uma rota, mas quase sempre vai ter pontos que vão funcionar como um hub
    de forma que vão ter varias arestas saindo destes pontos e terminando em pontos intermediários que não teriam ligação com nenhum outro
    Isso faz com que o MST tenha um custo muito mais barato que o real, serve como heuristica, mas fica muito folgado tornando a execução
    do A* muito lenta.
    Para resolver isso essa função calcula pesos pros pontos e uma matriz de custos alternativa que vai ter os custos da original mais
    os pesos dos pontos das arestas, e esses pesos são ajustados iterativamente de forma a aumentar pesos de pontos que possuem graus maiores
    do que deveria e diminui dos que possuem menor, de forma a ir aproximando a MST de uma rota
    Usar esses pesos não invalida o A* pq no fim todas as rotas vão ter um parcela igual de custos de pesos, de forma que a rota mais barata
    vai continuar sendo a mais barata, a segunda mais barata vai continuar sendo a segunda mais barata e etc, assim como a árvore vai continuar
    sendo mais barata que a rota mais barata, só que a tendência é que a diferença entre o custo da árvore e da rota vai ficar menor de forma
    que ela vai ser uma heuristica mais apertada pro A* o que vai acelerar o algoritmo.
    """
    n = len(M)
    p = [0.0] * n
    alvo = [1] + [2] * (n - 2) + [1]
    for ite in range(1000):
        M2 = [[M[i][j] + p[i] + p[j] for j in range(n)] for i in range(n)]
        _, graus = mst(list(range(n)), M2)
        for i in range(n):
            p[i] += (graus[i] - alvo[i]) * 0.99 ** ite
    return p


def h(atual, restantes, M2, p, fim):
    """
    Funções heuristica, vai pegar o custo da matriz de custos alternativa gerada pelos ajustes de pesos feitos pela calcula_pesos,
    calcular o custo da MST usando essa matriz, retirando o peso do ponto inicial, do final e 2 vezes a soma do peso dos intermediários
    já que o peso do inicial e final só entram na conta uma vez porque eles tem grau 1 e dos intermediários 2 já que tem grau 2
    Na prática é como se rota minima com custos originais tivesse custo R e a MST custo M, de forma que M <= R, ao considerar os pesos
    o custo da rota minima vai ser R+K por exemplo e da árvore vai ser M' de forma que M' <= R+K, logo M'-K <= R, por isso podemos usar
    M'-K como o custo da heuristíca no lugar de M, e a tendencia é que M'-K seja > M, portanto seja uma heuristica melhor
    """
    total, _ = mst([atual] + list(restantes) + [fim], M2)
    return total - 2 * sum(p[k] for k in restantes) - p[atual] - p[fim]


def ordem_ate(estado, parent):
    ordem = []
    while estado is not None:
        ordem.insert(0, estado[0])
        estado = parent[estado]
    return ordem


def astar_rota(M, caminhos):
    """
    A* para achar a ordem de visita dos ginásios usando a matriz de distancias pré-calculada
    Para usar o A* para resolver a ordem dos ginásios precisamos usar estados para informar em que ponto ele está,
    estes estados ficaram sendo uma tupla (ponto atual, set de pontos que faltam)
    Também resaltasse que o g(n) começa sendo 1 no heap porque o enunciado explicitou que só para sair do bloco inicial
    há um custo = 1
    """
    fim = len(M) - 1
    p = calcula_pesos(M)
    M2 = [[M[i][j] + p[i] + p[j] for j in range(len(M))] for i in range(len(M))]

    inicio = (0, frozenset(range(1, fim)))
    heap = [[1+h(0, inicio[1], M2, p, fim), 1, inicio]]
    g_score = {inicio: 1}
    parent = {inicio: None}
    closed = set()
    historico = []

    iteracoes = 0

    while heap:
        iteracoes += 1
        f, g, estado = heapq.heappop(heap)
        atual, restantes = estado
        if estado in closed:
            continue
        print(f"Iteracao {iteracoes}: Falta passar por {len(restantes) + (0 if atual == fim else 1)} pontos || g(n) = {g} || h(n) = {f-g} || LB = {f}")
        historico.append({"rota": ordem_ate(estado, parent), "g": g, "f": f})
        if atual == fim:
            ordem = ordem_ate(estado, parent)
            trechos = [caminhos[(ordem[k], ordem[k+1])] for k in range(len(ordem)-1)]
            return g, ordem, trechos, historico
        closed.add(estado)

        for prox in (restantes if restantes else [fim]):
            novo = (prox, restantes - {prox})
            g_n = g + M[atual][prox]
            if novo not in closed and (novo not in g_score or g_n < g_score[novo]):
                g_score[novo] = g_n
                parent[novo] = estado
                f_n = g_n + (0 if prox == fim else h(prox, novo[1], M2, p, fim))
                heapq.heappush(heap, [f_n, g_n, novo])


terrain, coordenadas = read_txt(r"data\kanto.txt")
pontos = ["init"] + [f"G{k+1}" for k in range(24)] + ["OBJ"]

M, caminhos = montar_matriz(coordenadas, terrain, pontos)
custo, ordem, trechos, historico = astar_rota(M, caminhos)

print([pontos[i] for i in ordem])
print(custo)

json.dump(historico, open("outputs/historico_astar_rota.json", "w"), indent=2)
json.dump({"custo": custo, "pontos": pontos, "ordem": ordem, "trechos": trechos}, open("outputs/rota_final.json", "w"), indent=2)
json.dump({f"{i}-{j}": c for (i, j), c in caminhos.items()}, open("outputs/caminhos_grid.json", "w"))