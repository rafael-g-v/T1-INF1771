"""Leitura e representação do mapa (matriz de caracteres)."""
from pathlib import Path

from . import config


class Mapa:
    def __init__(self, linhas):
        linhas = [l.strip() for l in linhas if l.strip()]
        if not linhas:
            raise ValueError("Mapa vazio")
        if len({len(l) for l in linhas}) != 1:
            raise ValueError("Todas as linhas do mapa devem ter o mesmo tamanho")
        self.grade = linhas
        self.altura = len(linhas)
        self.largura = len(linhas[0])
        self.origem = None
        self.destino = None
        self.ginasios = {}  # id -> (linha, coluna)
        for r, linha in enumerate(linhas):
            for c, ch in enumerate(linha):
                if ch == config.ORIGEM:
                    self.origem = (r, c)
                elif ch == config.DESTINO:
                    self.destino = (r, c)
                elif ch in config.DIFICULDADE_GINASIOS:
                    self.ginasios[ch] = (r, c)
                elif ch not in config.CUSTO_TERRENO:
                    raise ValueError(f"Símbolo desconhecido {ch!r} em {(r, c)}")
        if self.origem is None or self.destino is None:
            raise ValueError("O mapa precisa ter origem e destino")
        self.ginasio_em = {pos: g for g, pos in self.ginasios.items()}

    @classmethod
    def carregar(cls, caminho=config.ARQUIVO_MAPA):
        return cls(Path(caminho).read_text(encoding="utf-8").splitlines())

    def simbolo(self, r, c):
        return self.grade[r][c]

    def custo(self, r, c):
        """Custo de entrar na célula; origem, destino e ginásios custam o valor especial."""
        return config.CUSTO_TERRENO.get(self.grade[r][c], config.CUSTO_CELULA_ESPECIAL)

    def dentro(self, r, c):
        return 0 <= r < self.altura and 0 <= c < self.largura

    def vizinhos(self, r, c):
        """Vizinhos nas 4 direções (sem diagonais)."""
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            if self.dentro(r + dr, c + dc):
                yield (r + dr, c + dc)

    def custo_caminho(self, caminho):
        """Soma do custo de todas as células do caminho, origem incluída."""
        return sum(self.custo(r, c) for r, c in caminho)
