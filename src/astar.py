import heapq
import time


def convert_map(terrain):
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
                coordenadas[terrain[i][j]] = (i,j)

    return terrain, coordenadas


def read_txt(path):
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
    heap = [[abs(origem[0]-destino[0]) + abs(origem[1]-destino[1]), 0, origem]]
    g_score = {tuple(origem): 0}
    closed = set()

    while heap:
        menor = heapq.heappop(heap)
        coord = menor[2]
        coord_key = tuple(coord)

        if coord == list(destino):
            return menor[1]
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
                h_n = abs(adj_i[0]-destino[0]) + abs(adj_i[1]-destino[1])
                heapq.heappush(heap, [g_n+h_n, g_n, adj_i])


def dist(p, q, coordenadas, terrain, cache):
    if p == q:
        return 0
    chave = (p, q) if p < q else (q, p)
    if chave not in cache:
        cache[chave] = astar(list(coordenadas[p]), list(coordenadas[q]), terrain)
    return cache[chave]


def mst(pontos, coordenadas, terrain, cache):
    pontos = list(pontos)
    visitados = [pontos[0]]
    restantes = pontos[1:]
    total = 0

    while restantes:
        menor_dist = float('inf')
        menor_ponto = None
        for p in restantes:
            d = min(dist(p, v, coordenadas, terrain, cache) for v in visitados)
            if d < menor_dist:
                menor_dist = d
                menor_ponto = p
        total += menor_dist
        visitados.append(menor_ponto)
        restantes.remove(menor_ponto)

    return total


def lower_bound(atual, restantes, fim, coordenadas, terrain, cache):
    pontos = list(restantes) + [fim]
    entrada = min(dist(atual, p, coordenadas, terrain, cache) for p in pontos)
    return entrada + mst(pontos, coordenadas, terrain, cache)


def dfs(atual, restantes, g, caminho, fim, coordenadas, terrain, cache, estado):
    if estado["parou"]:
        return

    estado["contador"] += 1
    if estado["contador"] % 1000 == 0:
        if time.time() - estado["inicio"] >= estado["limite_tempo"]:
            estado["parou"] = True
            return
        print(f"Chamadas {estado['contador']} | pos {atual} | "
              f"visitados {25-len(restantes)}/25 | g={g} | melhor={estado['melhor']}")

    if g >= estado["melhor"]:
        return

    chave = (atual, restantes)
    if chave in estado["memo"] and estado["memo"][chave] <= g:
        return
    estado["memo"][chave] = g

    if not restantes:
        g_final = g + dist(atual, fim, coordenadas, terrain, cache)
        if g_final < estado["melhor"]:
            estado["melhor"] = g_final
            estado["melhor_caminho"] = caminho + [fim]
            print(f"  >> nova melhor solução: {g_final} (em {estado['contador']} chamadas)")
        return

    lb = g + lower_bound(atual, restantes, fim, coordenadas, terrain, cache)
    if lb >= estado["melhor"]:
        return

    candidatos = sorted(restantes, key=lambda p: dist(atual, p, coordenadas, terrain, cache))
    for prox in candidatos:
        dfs(prox, restantes - {prox}, g + dist(atual, prox, coordenadas, terrain, cache),
            caminho + [prox], fim, coordenadas, terrain, cache, estado)


def branch_and_bound(coordenadas, terrain, limite_tempo):
    pontos = frozenset(f"G{i}" for i in range(1,25))
    cache = {}

    estado = {
        "melhor": float('inf'),
        "melhor_caminho": None,
        "memo": {},
        "contador": 0,
        "parou": False,
        "inicio": time.time(),
        "limite_tempo": limite_tempo,
    }

    dfs("init", pontos, 1, ["init"], "OBJ", coordenadas, terrain, cache, estado)

    if estado["parou"]:
        print(f"Tempo esgotado ({limite_tempo}s) — retornando melhor solução encontrada.")
    else:
        print("Busca concluída: resultado é ótimo garantido.")

    return estado["melhor_caminho"], estado["melhor"]


terrain, coordenadas = read_txt(r"data\kanto.txt")
caminho, custo = branch_and_bound(coordenadas, terrain, limite_tempo=60)

print(caminho)
print(custo)