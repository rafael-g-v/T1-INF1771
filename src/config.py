"""Configurações do problema: custos de terreno, ginásios e Pokémons.

Tudo aqui é editável: o mapa, o A* e a interface leem estes valores.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_MAPA = RAIZ / "data" / "kanto.txt"

# Custo (em minutos) de entrar numa célula de cada terreno.
CUSTO_TERRENO = {
    "M": 200,  # montanha
    "A": 30,   # água
    "F": 15,   # floresta
    "R": 5,    # rochoso
    ".": 1,    # livre
}
NOME_TERRENO = {
    "M": "Montanha",
    "A": "Água",
    "F": "Floresta",
    "R": "Rochoso",
    ".": "Livre",
}

# Origem, destino e ginásios custam 1 minuto para pisar (além da batalha).
CUSTO_CELULA_ESPECIAL = 1
ORIGEM = "1"
DESTINO = "U"

# Dificuldade de cada ginásio, na ordem do enunciado (Tabela 1).
DIFICULDADE_GINASIOS = {
    "2": 35, "3": 40, "4": 45, "5": 50, "6": 55, "7": 60, "8": 65, "9": 70,
    "B": 75, "C": 80, "D": 85, "E": 90, "G": 95, "H": 100, "I": 110, "J": 120,
    "K": 130, "L": 140, "N": 150, "O": 155, "P": 160, "Q": 165, "S": 170,
    "T": 180,
}

# Fator de poder de cada Pokémon (Tabela 2).
PODER_POKEMONS = {
    "Pikachu": 1.5,
    "Bulbassauro": 1.4,
    "Rattata": 1.3,
    "Caterpie": 1.2,
    "Weedle": 1.1,
}
ENERGIA_INICIAL = 6
