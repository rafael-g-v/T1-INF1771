"""Cálculos de custo e energia ao longo do caminho (sem dependência de interface)."""
from dataclasses import dataclass, field

from . import config


@dataclass
class Resumo:
    ordem: list = field(default_factory=list)             # ginásios na ordem da 1ª visita
    ginasio_no_passo: dict = field(default_factory=dict)  # índice do caminho -> ginásio
    rota_acum: list = field(default_factory=list)         # custo da rota até o passo i
    bat_acum: list = field(default_factory=list)          # custo das batalhas até o passo i
    batalhas_ate: list = field(default_factory=list)      # nº de batalhas feitas até o passo i
    energias: list = field(default_factory=list)          # energias[k] = energia após k batalhas
    pokemons_usados: dict = field(default_factory=dict)   # ginásio -> Pokémons que lutaram
    tempo_batalha: dict = field(default_factory=dict)
    avisos: list = field(default_factory=list)
    custo_rota: int = 0
    custo_batalhas: float = 0.0

    @property
    def custo_total(self):
        return self.custo_rota + self.custo_batalhas

    @property
    def energia_final(self):
        return self.energias[-1]


def tempo_batalha(ginasio, pokemons):
    poder = sum(config.PODER_POKEMONS[p] for p in pokemons)
    return config.DIFICULDADE_GINASIOS[ginasio] / poder if poder else 0.0


def calcular_resumo(mapa, replay):
    s = Resumo()
    caminho = replay.caminho
    energia = {p: config.ENERGIA_INICIAL for p in config.PODER_POKEMONS}
    s.energias.append(dict(energia))
    visitados = set()
    rota = 0
    bat = 0.0
    nbat = 0
    for i, (r, c) in enumerate(caminho):
        rota += mapa.custo(r, c)
        g = mapa.ginasio_em.get((r, c))
        if g is not None and g not in visitados:
            visitados.add(g)
            s.ordem.append(g)
            s.ginasio_no_passo[i] = g
            escolhidos = replay.pokemons_por_ginasio.get(g)
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
        s.rota_acum.append(rota)
        s.bat_acum.append(bat)
        s.batalhas_ate.append(nbat)
    s.custo_rota, s.custo_batalhas = rota, bat
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
