from pathlib import Path


CAMINHO_MAPA = Path(__file__).resolve().parent.parent / "data" / "kanto.txt"

SIMBOLO_ORIGEM = "1"
SIMBOLO_DESTINO = "U"

CUSTO_TERRENO = {
    "M": 200,
    "A": 30,
    "F": 15,
    "R": 5,
    ".": 1,
}

CUSTO_ORIGEM_DESTINO = 1

CUSTO_GINASIO = 1

CONTAR_CUSTO_ORIGEM = False

DIFICULDADE_GINASIOS = {
    "2": 35,
    "3": 40,
    "4": 45,
    "5": 50,
    "6": 55,
    "7": 60,
    "8": 65,
    "9": 70,
    "B": 75,
    "C": 80,
    "D": 85,
    "E": 90,
    "G": 95,
    "H": 100,
    "I": 110,
    "J": 120,
    "K": 130,
    "L": 140,
    "N": 150,
    "O": 155,
    "P": 160,
    "Q": 165,
    "S": 170,
    "T": 180,
}

PODER_POKEMONS = {
    "Pikachu": 1.5,
    "Bulbassauro": 1.4,
    "Rattata": 1.3,
    "Caterpie": 1.2,
    "Weedle": 1.1,
}

ENERGIA_INICIAL = 6