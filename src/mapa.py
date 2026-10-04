from __future__ import annotations

from pathlib import Path

from . import config

Posicao = tuple[int, int]

MOVIMENTOS = ((-1, 0), (1, 0), (0, -1), (0, 1))


class Mapa:
    def __init__(self, linhas, custo_terreno=None, custo_origem_destino=None, custo_ginasio=None):
        if custo_terreno is None:
            custo_terreno = config.CUSTO_TERRENO
        if custo_origem_destino is None:
            custo_origem_destino = config.CUSTO_ORIGEM_DESTINO
        if custo_ginasio is None:
            custo_ginasio = config.CUSTO_GINASIO

        self.linhas = [str(linha) for linha in linhas]
        if not self.linhas or not self.linhas[0]:
            raise ValueError("Mapa vazio.")
        self.altura = len(self.linhas)
        self.largura = len(self.linhas[0])

        self.origem: Posicao | None = None
        self.destino: Posicao | None = None
        achados: dict[str, Posicao] = {}
        self._custo: list[list[float]] = []

        for l, linha in enumerate(self.linhas):
            if len(linha) != self.largura:
                raise ValueError(
                    f"Linha {l + 1} do mapa tem {len(linha)} colunas; "
                    f"esperava {self.largura}."
                )
            custos_linha = []
            for c, simbolo in enumerate(linha):
                if simbolo in custo_terreno:
                    custos_linha.append(custo_terreno[simbolo])
                    continue
                if simbolo == config.SIMBOLO_ORIGEM:
                    self._definir_unico("origem", (l, c))
                    custos_linha.append(custo_origem_destino)
                elif simbolo == config.SIMBOLO_DESTINO:
                    self._definir_unico("destino", (l, c))
                    custos_linha.append(custo_origem_destino)
                elif simbolo in config.DIFICULDADE_GINASIOS:
                    if simbolo in achados:
                        raise ValueError(f"Ginásio '{simbolo}' aparece mais de uma vez.")
                    achados[simbolo] = (l, c)
                    custos_linha.append(custo_ginasio)
                else:
                    raise ValueError(
                        f"Símbolo desconhecido '{simbolo}' na linha {l + 1}, coluna {c + 1}."
                    )
            self._custo.append(custos_linha)

        if self.origem is None:
            raise ValueError(f"Mapa sem origem ('{config.SIMBOLO_ORIGEM}').")
        if self.destino is None:
            raise ValueError(f"Mapa sem destino ('{config.SIMBOLO_DESTINO}').")

        self.ginasios: dict[str, Posicao] = {
            s: achados[s] for s in config.DIFICULDADE_GINASIOS if s in achados
        }

        self.custo_minimo = min(min(linha) for linha in self._custo)

        self._sucessores: dict[Posicao, tuple] = {}
        for l in range(self.altura):
            for c in range(self.largura):
                vizinhos = []
                for dl, dc in MOVIMENTOS:
                    nl, nc = l + dl, c + dc
                    if 0 <= nl < self.altura and 0 <= nc < self.largura:
                        vizinhos.append(((nl, nc), self._custo[nl][nc]))
                self._sucessores[(l, c)] = tuple(vizinhos)

    def _definir_unico(self, nome: str, posicao: Posicao) -> None:
        if getattr(self, nome) is not None:
            raise ValueError(f"O mapa tem mais de um ponto de {nome}.")
        setattr(self, nome, posicao)

    @classmethod
    def carregar(cls, caminho=None, **custos) -> "Mapa":
        caminho = Path(caminho) if caminho is not None else config.CAMINHO_MAPA
        texto = caminho.read_text(encoding="utf-8-sig")
        linhas = [linha.rstrip("\r") for linha in texto.split("\n")]
        while linhas and not linhas[-1].strip():
            linhas.pop()
        return cls(linhas, **custos)

    def simbolo(self, posicao: Posicao) -> str:
        return self.linhas[posicao[0]][posicao[1]]

    def custo(self, posicao: Posicao) -> float:
        return self._custo[posicao[0]][posicao[1]]

    def sucessores(self, posicao: Posicao) -> tuple:
        return self._sucessores[posicao]