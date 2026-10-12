from pathlib import Path

from . import config

ARQUIVO_MAPA = Path(__file__).resolve().parent.parent / "data" / "kanto.txt"


class Mapa:
    def __init__(self, linhas):
        self.linhas = linhas
        self.altura = len(linhas)
        self.largura = len(linhas[0])
        self.ginasios = {}
        for r, linha in enumerate(linhas):
            for c, s in enumerate(linha):
                if s == config.SIMBOLO_ORIGEM:
                    self.origem = (r, c)
                elif s == config.SIMBOLO_DESTINO:
                    self.destino = (r, c)
                elif s in config.DIFICULDADE_GINASIOS:
                    self.ginasios[s] = (r, c)

    def simbolo(self, pos):
        return self.linhas[pos[0]][pos[1]]

    @classmethod
    def carregar(cls, caminho=ARQUIVO_MAPA):
        with open(caminho, encoding="utf-8") as f:
            return cls([linha.rstrip("\r\n") for linha in f if linha.strip()])
