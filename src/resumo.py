"""Cálculos de custo e energia ao longo do caminho (sem dependência de interface)."""
from . import config


class Resumo:
    def __init__(self):
        self.ordem = []              # ginásios na ordem da 1ª visita
        self.ginasio_no_passo = {}   # índice do caminho -> ginásio
        self.rota_acum = []          # custo da rota até o passo i
        self.bat_acum = []           # custo das batalhas até o passo i
        self.batalhas_ate = []       # nº de batalhas feitas até o passo i
        self.energias = []           # energias[k] = energia após k batalhas
        self.pokemons_usados = {}    # ginásio -> Pokémons que lutaram
        self.tempo_batalha = {}
        self.avisos = []
        self.custo_rota = 0
        self.custo_batalhas = 0.0
        self.custo_total = 0.0
        self.energia_final = {}      # energia de cada Pokémon ao chegar ao destino


def tempo_batalha(ginasio, pokemons):
    poder = sum(config.PODER_POKEMONS[p] for p in pokemons)
    return config.DIFICULDADE_GINASIOS[ginasio] / poder if poder else 0.0


def calcular_resumo(mapa, caminho, custo_acumulado, pokemons_por_ginasio):
    s = Resumo()
    ginasio_em = {pos: g for g, pos in mapa.ginasios.items()}
    energia = {p: config.ENERGIA_INICIAL for p in config.PODER_POKEMONS}
    s.energias.append(dict(energia))
    visitados = set()
    bat = 0.0
    nbat = 0
    for i, posicao in enumerate(caminho):
        g = ginasio_em.get(posicao)
        if g is not None and g not in visitados:
            visitados.add(g)
            s.ordem.append(g)
            s.ginasio_no_passo[i] = g
            escolhidos = pokemons_por_ginasio.get(g)
            if escolhidos is None:
                s.avisos.append(f"Ginásio {g} sem Pokémons definidos")
                escolhidos = []
            validos = []
            for p in escolhidos:
                if p not in energia:
                    s.avisos.append(f"Pokémon desconhecido: {p}")
                elif energia[p] <= 0:
                    s.avisos.append(f"{p} lutou no ginásio {g} sem energia")
                else:
                    energia[p] -= 1
                    validos.append(p)
            t = tempo_batalha(g, validos)
            s.pokemons_usados[g] = validos
            s.tempo_batalha[g] = t
            bat += t
            nbat += 1
            s.energias.append(dict(energia))
        s.rota_acum.append(custo_acumulado[i])
        s.bat_acum.append(bat)
        s.batalhas_ate.append(nbat)
    rota = custo_acumulado[-1] if caminho else 0
    s.custo_rota, s.custo_batalhas = rota, bat
    s.custo_total = rota + bat
    s.energia_final = dict(energia)
    if caminho:
        if caminho[0] != mapa.origem:
            s.avisos.append("O caminho não começa na origem")
        if caminho[-1] != mapa.destino:
            s.avisos.append("O caminho não termina no destino")
    faltam = [g for g in mapa.ginasios if g not in visitados]
    if faltam:
        s.avisos.append("Ginásios não visitados: " + ", ".join(faltam))
    if not any(e > 0 for e in energia.values()):
        s.avisos.append("Nenhum Pokémon chegou ao destino com energia")
    for a, b in zip(caminho, caminho[1:]):
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            s.avisos.append(f"Passo inválido (não adjacente): {a} -> {b}")
            break
    return s
