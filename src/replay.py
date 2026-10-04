"""Contrato entre os algoritmos e a interface.

A interface não executa o A*: ela apenas reproduz o que foi registrado.
"""
from dataclasses import dataclass, field

# Tipos de evento do A* (tupla: tipo, linha, coluna)
GERAR = "g"      # célula entrou na fronteira
EXPANDIR = "e"   # célula foi expandida (visitada)
NOVA = "n"       # nova busca: esvazia a fronteira exibida


@dataclass
class Replay:
    eventos: list = field(default_factory=list)   # [(tipo, r, c), ...]
    caminho: list = field(default_factory=list)   # [(r, c), ...] da origem ao destino
    pokemons_por_ginasio: dict = field(default_factory=dict)  # {"2": ["Weedle"], ...}
    rotulo: str = "A*"
