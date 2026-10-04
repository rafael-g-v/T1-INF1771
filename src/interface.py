"""Interface gráfica (pygame) que reproduz a execução do agente em Kanto.

Fase 1 (busca):    reproduz os eventos do A* (fronteira e estados expandidos).
Fase 2 (execução): o agente percorre o caminho final, acumulando custos.
Fase 3 (fim):      tela de resultados.

Uso:  python -m src.interface
"""
import sys

import pygame

from . import config
from .mapa import Mapa
from .replay import EXPANDIR, GERAR, NOVA
from .resumo import calcular_resumo

# ---------------------------------------------------------------- layout
LARGURA, ALTURA = 1280, 880
CELULA = 8
MAPA_X, MAPA_Y = 40, 64

# ---------------------------------------------------------------- cores
# Paleta sóbria, de figura de artigo: fundo de papel, texto escuro, cores chapadas.
FUNDO = (251, 250, 247)
BRANCO = (255, 255, 255)
TEXTO = (28, 28, 32)
TEXTO_SUAVE = (96, 96, 104)
BORDA = (190, 188, 182)
REGRA = (40, 40, 44)
ERRO = (160, 30, 30)

COR_TERRENO = {
    "M": (176, 146, 112),
    "A": (180, 205, 228),
    "F": (160, 190, 148),
    "R": (205, 201, 194),
    ".": (247, 245, 238),
}
COR_EXPANDIDO = (112, 72, 160)
COR_FRONTEIRA = (230, 126, 34)
COR_CAMINHO = (170, 25, 25)

# Paleta de Okabe-Ito (distinguível por daltônicos) + abreviações.
COR_POKEMON = {
    "Pikachu": (240, 200, 70),
    "Bulbassauro": (110, 190, 160),
    "Rattata": (214, 160, 196),
    "Caterpie": (140, 200, 236),
    "Weedle": (230, 150, 100),
}
ABREV = {"Pikachu": "Pk", "Bulbassauro": "Bu", "Rattata": "Ra", "Caterpie": "Ca", "Weedle": "We"}

EVENTOS_POR_QUADRO = [1, 4, 16, 64, 256, 1024, 4096, 16384]
PASSOS_POR_QUADRO = [0.1, 0.25, 0.5, 1, 2, 4, 8, 16]


def _fmt(valor, casas):
    """Número com vírgula decimal, como em português."""
    return f"{valor:.{casas}f}".replace(".", ",")


def _milhar(n):
    return f"{n:,}".replace(",", ".")


def _sup_transparente(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


class Interface:
    def __init__(self, mapa, replay):
        self.mapa = mapa
        self.replay = replay
        self.resumo = calcular_resumo(mapa, replay)
        self.caminho = replay.caminho

        pygame.init()
        pygame.display.set_caption("Busca heurística em Kanto (INF1771)")
        self.tela = pygame.display.set_mode((LARGURA, ALTURA), pygame.SCALED | pygame.RESIZABLE)
        self.relogio = pygame.time.Clock()
        self._fontes = {}

        mw, mh = mapa.largura * CELULA, mapa.altura * CELULA
        self.mapa_rect = pygame.Rect(MAPA_X, MAPA_Y, mw, mh)
        self.sup_terreno = self._desenhar_terreno()
        self.sup_exp = _sup_transparente(mw, mh)
        self.sup_fro = _sup_transparente(mw, mh)
        self.pontos_caminho = [
            (c * CELULA + CELULA // 2, r * CELULA + CELULA // 2) for r, c in self.caminho
        ]
        self.camadas = {"expandidos": True, "fronteira": True, "caminho": True, "rótulos": True}
        self.velocidade = 3
        self.batalha = None
        self.timer = 0
        self.reiniciar()

    # ------------------------------------------------------------ estado
    def reiniciar(self):
        self.fase = "busca" if self.replay.eventos else "exec"
        self.idx_evento = 0
        self.passo = 0.0
        self.tocando = True
        self.mostrar_resultado = False
        self.batalha = None
        self.timer = 0
        self.contagem = {}
        self.n_gerados = 0
        self.n_expandidos = 0
        self.sup_exp.fill((0, 0, 0, 0))
        self.sup_fro.fill((0, 0, 0, 0))

    @property
    def passo_i(self):
        return min(int(self.passo), len(self.caminho) - 1)

    def _aplicar_evento(self, ev):
        tipo, r, c = ev
        rect = (c * CELULA, r * CELULA, CELULA, CELULA)
        if tipo == NOVA:
            self.sup_fro.fill((0, 0, 0, 0))
        elif tipo == GERAR:
            self.n_gerados += 1
            if (r, c) not in self.contagem:
                self.sup_fro.fill((*COR_FRONTEIRA, 235), rect)
        elif tipo == EXPANDIR:
            self.n_expandidos += 1
            n = self.contagem.get((r, c), 0) + 1
            self.contagem[(r, c)] = n
            self.sup_fro.fill((0, 0, 0, 0), rect)
            self.sup_exp.fill((*COR_EXPANDIDO, min(50 + 25 * n, 130)), rect)

    def _avancar_busca(self, n):
        eventos = self.replay.eventos
        fim = min(self.idx_evento + n, len(eventos))
        for ev in eventos[self.idx_evento:fim]:
            self._aplicar_evento(ev)
        self.idx_evento = fim
        if fim >= len(eventos):
            self.sup_fro.fill((0, 0, 0, 0))
            self.fase = "exec"

    def _avancar_exec(self, n, batalhas=True):
        ultimo = len(self.caminho) - 1
        destino = min(self.passo + n, ultimo)
        if batalhas:
            for i in range(int(self.passo) + 1, int(destino) + 1):
                if i in self.resumo.ginasio_no_passo:  # para no ginásio e luta
                    self.passo = float(i)
                    self.batalha = self.resumo.ginasio_no_passo[i]
                    self.timer = max(10, 80 // (self.velocidade + 1))
                    return
        self.passo = destino
        if self.passo >= ultimo:
            self.fase = "fim"
            self.mostrar_resultado = True
            self.tocando = False
            self.batalha = None

    def avancar(self, passos_unitarios=None):
        """Avança um quadro (ou um passo, se `passos_unitarios` for dado)."""
        if self.batalha is not None:
            if passos_unitarios:
                self.batalha, self.timer = None, 0
            else:
                self.timer -= 1
                if self.timer <= 0:
                    self.batalha = None
            return
        if self.fase == "busca":
            self._avancar_busca(1 if passos_unitarios else EVENTOS_POR_QUADRO[self.velocidade])
        elif self.fase == "exec":
            self._avancar_exec(1 if passos_unitarios else PASSOS_POR_QUADRO[self.velocidade])

    def pular_para(self, fase, fracao=1.0):
        """Usado nas capturas de tela: busca | exec | batalha | fim."""
        eventos = self.replay.eventos
        if fase == "busca":
            self._avancar_busca(int(len(eventos) * fracao) - self.idx_evento)
            self.fase = "busca"
        else:
            self._avancar_busca(len(eventos) - self.idx_evento)
            if fase == "batalha":
                for _ in range(max(1, int(fracao))):
                    self.batalha, self.timer = None, 0
                    self._avancar_exec(10**6)
            else:
                self._avancar_exec(len(self.caminho) * (fracao if fase == "exec" else 1.0), batalhas=False)
                if fase == "exec":
                    self.fase, self.mostrar_resultado = "exec", False
        self.tocando = False

    def pular(self):
        self.batalha, self.timer = None, 0
        if self.fase == "busca":
            self._avancar_busca(len(self.replay.eventos))
        else:
            self._avancar_exec(len(self.caminho), batalhas=False)

    # ------------------------------------------------------------ desenho
    def fonte(self, tamanho, negrito=False, mono=False, italico=False):
        chave = (tamanho, negrito, mono, italico)
        if chave not in self._fontes:
            nomes = "consolas,couriernew,dejavusansmono" if mono else "cambria,georgia,timesnewroman,dejavuserif"
            self._fontes[chave] = pygame.font.SysFont(nomes, tamanho, bold=negrito, italic=italico)
        return self._fontes[chave]

    def texto(self, txt, x, y, tam=15, cor=TEXTO, negrito=False, centro=False, direita=False,
              mono=False, italico=False):
        img = self.fonte(tam, negrito, mono, italico).render(str(txt), True, cor)
        rect = img.get_rect()
        if centro:
            rect.center = (x, y)
        elif direita:
            rect.topright = (x, y)
        else:
            rect.topleft = (x, y)
        self.tela.blit(img, rect)
        return rect

    def _desenhar_terreno(self):
        """Terreno em cores chapadas e discretas, como uma figura de artigo."""
        sup = pygame.Surface((self.mapa.largura * CELULA, self.mapa.altura * CELULA))
        for r in range(self.mapa.altura):
            for c in range(self.mapa.largura):
                cor = COR_TERRENO.get(self.mapa.simbolo(r, c), COR_TERRENO["."])
                sup.fill(cor, (c * CELULA, r * CELULA, CELULA, CELULA))
        return sup

    def _centro(self, pos):
        r, c = pos
        return (MAPA_X + c * CELULA + CELULA // 2, MAPA_Y + r * CELULA + CELULA // 2)

    def _painel(self, rect, titulo=None):
        pygame.draw.rect(self.tela, BRANCO, rect)
        pygame.draw.rect(self.tela, BORDA, rect, 1)
        if titulo:
            self.texto(titulo, rect.x + 12, rect.y + 8, 15, TEXTO, negrito=True)
            pygame.draw.line(self.tela, REGRA, (rect.x + 12, rect.y + 30), (rect.right - 12, rect.y + 30), 1)

    def _chip(self, nome, x, y, ativo=True):
        """Etiqueta curta (duas letras) que identifica o Pokémon."""
        cor = COR_POKEMON[nome] if ativo else (214, 212, 206)
        rect = pygame.Rect(x, y, 24, 16)
        pygame.draw.rect(self.tela, cor, rect)
        pygame.draw.rect(self.tela, REGRA, rect, 1)
        self.texto(ABREV[nome], rect.centerx, rect.centery, 12, TEXTO, negrito=True, centro=True)
        return rect

    def _marcador(self, pos, rotulo, tipo):
        cx, cy = self._centro(pos)
        if tipo == "ginasio":
            pygame.draw.circle(self.tela, BRANCO, (cx, cy), 8)
            pygame.draw.circle(self.tela, REGRA, (cx, cy), 8, 1)
            cor_txt = TEXTO
        elif tipo == "visitado":
            pygame.draw.circle(self.tela, REGRA, (cx, cy), 8)
            cor_txt = BRANCO
        elif tipo == "origem":
            pygame.draw.rect(self.tela, BRANCO, (cx - 8, cy - 8, 16, 16))
            pygame.draw.rect(self.tela, REGRA, (cx - 8, cy - 8, 16, 16), 2)
            cor_txt = TEXTO
        else:  # destino
            pygame.draw.rect(self.tela, REGRA, (cx - 8, cy - 8, 16, 16))
            cor_txt = BRANCO
        if self.camadas["rótulos"]:
            self.texto(rotulo, cx, cy, 12, cor_txt, negrito=True, centro=True)

    def desenhar_mapa(self):
        pygame.draw.rect(self.tela, REGRA, self.mapa_rect.inflate(2, 2), 1)
        self.tela.blit(self.sup_terreno, self.mapa_rect)
        if self.camadas["expandidos"]:
            self.tela.blit(self.sup_exp, self.mapa_rect)
        if self.camadas["fronteira"]:
            self.tela.blit(self.sup_fro, self.mapa_rect)

        i = self.passo_i
        if self.camadas["caminho"] and self.fase != "busca" and len(self.pontos_caminho) > 1:
            off = [(x + MAPA_X, y + MAPA_Y) for x, y in self.pontos_caminho]
            if i > 0:
                pygame.draw.lines(self.tela, COR_CAMINHO, False, off[: i + 1], 2)
            if i < len(off) - 1:  # trecho ainda não percorrido, tracejado fino
                for a, b in zip(off[i::2], off[i + 1::2]):
                    pygame.draw.line(self.tela, COR_CAMINHO, a, b, 1)

        visitados = {g: k + 1 for k, g in enumerate(self.resumo.ordem)
                     if self.fase != "busca" and self._passo_do(g) <= i}
        for g, pos in self.mapa.ginasios.items():
            if g in visitados:
                self._marcador(pos, str(visitados[g]), "visitado")
            else:
                self._marcador(pos, g, "ginasio")
        self._marcador(self.mapa.origem, config.ORIGEM, "origem")
        self._marcador(self.mapa.destino, config.DESTINO, "destino")

        if self.fase != "busca" and self.caminho:
            cx, cy = self._centro(self.caminho[i])
            pygame.draw.circle(self.tela, BRANCO, (cx, cy), 6)
            pygame.draw.circle(self.tela, COR_CAMINHO, (cx, cy), 5)
            if self.batalha is not None:
                self._caixa_batalha(cx, cy)

    def _caixa_batalha(self, cx, cy):
        """Caixa simples sobre o ginásio com quem luta e quanto dura a batalha."""
        g = self.batalha
        pokes = self.resumo.pokemons_usados[g]
        larg, alt = 210, 62
        x = min(max(cx - larg // 2, self.mapa_rect.x + 4), self.mapa_rect.right - larg - 4)
        y = cy - alt - 14
        if y < self.mapa_rect.y + 4:
            y = cy + 14
        rect = pygame.Rect(x, y, larg, alt)
        pygame.draw.rect(self.tela, BRANCO, rect)
        pygame.draw.rect(self.tela, REGRA, rect, 1)
        self.texto(f"Ginásio {g} (dificuldade {config.DIFICULDADE_GINASIOS[g]})", rect.x + 8, rect.y + 6, 13,
                   TEXTO, negrito=True)
        xp = rect.x + 8
        for p in pokes:
            xp = self._chip(p, xp, rect.y + 25).right + 4
        self.texto(f"Duração da batalha: {_fmt(self.resumo.tempo_batalha[g], 1)} min", rect.x + 8,
                   rect.y + 43, 12, TEXTO_SUAVE)

    def _passo_do(self, g):
        if not hasattr(self, "_passos_ginasio"):
            self._passos_ginasio = {gid: p for p, gid in self.resumo.ginasio_no_passo.items()}
        return self._passos_ginasio.get(g, 10**9)

    def desenhar_cabecalho(self):
        self.texto("Busca heurística em Kanto", MAPA_X, 10, 26, TEXTO, negrito=True)
        self.texto("INF1771 · Inteligência Artificial · Trabalho 1", MAPA_X, 40, 13, TEXTO_SUAVE)
        rotulos = {"busca": f"Etapa 1 de 2: busca com {self.replay.rotulo}",
                   "exec": "Etapa 2 de 2: execução da rota",
                   "fim": "Execução concluída"}
        self.texto(rotulos[self.fase], LARGURA - MAPA_X, 12, 15, TEXTO, negrito=True, direita=True)
        mx, my = pygame.mouse.get_pos()
        c, r = (mx - MAPA_X) // CELULA, (my - MAPA_Y) // CELULA
        if self.mapa_rect.collidepoint(mx, my) and self.mapa.dentro(r, c):
            ch = self.mapa.simbolo(r, c)
            if ch in config.NOME_TERRENO:
                nome = f"{config.NOME_TERRENO[ch]} (+{config.CUSTO_TERRENO[ch]} min)"
            elif ch in config.DIFICULDADE_GINASIOS:
                nome = f"Ginásio {ch}, dificuldade {config.DIFICULDADE_GINASIOS[ch]}"
            else:
                nome = "Origem" if ch == config.ORIGEM else "Destino"
            self.texto(f"Linha {r}, coluna {c}: {nome}", LARGURA - MAPA_X, 38, 13, TEXTO_SUAVE, direita=True)

    def desenhar_legenda_figura(self):
        y = MAPA_Y + self.mapa_rect.h + 8
        self.texto("Figura 1. Mapa de Kanto (150 × 42 células). Roxo: estados expandidos; laranja: fronteira; "
                   "vermelho: rota; círculos: ginásios; quadrados: origem (1) e destino (U).",
                   MAPA_X, y, 13, TEXTO_SUAVE, italico=True)

    def _valores_atuais(self):
        r = self.resumo
        if self.fase == "busca":
            return 0, 0.0, 0, 0
        i = self.passo_i
        return r.rota_acum[i], r.bat_acum[i], r.batalhas_ate[i], len(r.ginasio_no_passo)

    def _linha_tabela(self, rect, y, nome, valor, forte=False, tam=15):
        self.texto(nome, rect.x + 12, y, tam, TEXTO, negrito=forte)
        self.texto(valor, rect.right - 12, y, tam, TEXTO, negrito=forte, direita=True, mono=True)

    def desenhar_custos(self, rect):
        self._painel(rect, "Custos")
        rota, bat, nbat, _ = self._valores_atuais()
        y = rect.y + 42
        self._linha_tabela(rect, y, "Rota", f"{rota} min")
        self._linha_tabela(rect, y + 26, "Batalhas", f"{_fmt(bat, 1)} min")
        pygame.draw.line(self.tela, REGRA, (rect.x + 12, y + 54), (rect.right - 12, y + 54), 1)
        self._linha_tabela(rect, y + 60, "Total", f"{_fmt(rota + bat, 1)} min", forte=True, tam=17)
        y += 108
        pygame.draw.line(self.tela, BORDA, (rect.x + 12, y - 8), (rect.right - 12, y - 8), 1)
        n = sum(1 for p in self.resumo.ginasio_no_passo if p <= self.passo_i) if self.fase != "busca" else 0
        self._linha_tabela(rect, y, "Estados expandidos", _milhar(self.n_expandidos), tam=14)
        self._linha_tabela(rect, y + 24, "Estados gerados", _milhar(self.n_gerados), tam=14)
        self._linha_tabela(rect, y + 48, "Ginásios visitados", f"{n} de {len(self.mapa.ginasios)}", tam=14)

    def desenhar_pokemons(self, rect):
        self._painel(rect, "Energia dos Pokémons")
        k = 0 if self.fase == "busca" else self.resumo.batalhas_ate[self.passo_i]
        energias = self.resumo.energias[k]
        y = rect.y + 44
        for nome, poder in config.PODER_POKEMONS.items():
            e = energias[nome]
            self._chip(nome, rect.x + 12, y + 2, e > 0)
            self.texto(nome, rect.x + 44, y, 15, TEXTO if e > 0 else TEXTO_SUAVE)
            self.texto(f"poder {_fmt(poder, 1)}", rect.x + 44, y + 18, 11, TEXTO_SUAVE)
            for s in range(config.ENERGIA_INICIAL):
                bx = rect.x + 172 + s * 28
                quad = pygame.Rect(bx, y + 4, 24, 14)
                if s < e:
                    pygame.draw.rect(self.tela, COR_POKEMON[nome], quad)
                pygame.draw.rect(self.tela, REGRA if s < e else BORDA, quad, 1)
            self.texto(f"{e}/{config.ENERGIA_INICIAL}", rect.right - 12, y + 2, 14,
                       TEXTO if e > 0 else ERRO, direita=True, mono=True)
            y += 44

    def desenhar_ginasios(self, rect):
        self._painel(rect, "Ginásios (ordem de visita)")
        r = self.resumo
        n = 0 if self.fase == "busca" else sum(1 for p in r.ginasio_no_passo if p <= self.passo_i)
        col_w = (rect.w - 24) // 2
        for k, g in enumerate(r.ordem):
            col, lin = divmod(k, 12)
            x = rect.x + 12 + col * col_w
            y = rect.y + 40 + lin * 28
            feito = k < n
            if k == n - 1:
                pygame.draw.rect(self.tela, (236, 233, 224), (x - 4, y - 3, col_w - 8, 25))
            cor = TEXTO if feito else (160, 158, 152)
            self.texto(f"{k + 1}.", x, y, 13, cor, mono=True)
            self.texto(g if self.fase != "busca" else "?", x + 28, y, 14, cor, negrito=True)
            if feito:
                x2 = x + 50
                for p in r.pokemons_usados[g]:
                    x2 = self._chip(p, x2, y + 1).right + 3
                self.texto(_fmt(r.tempo_batalha[g], 1), x + col_w - 12, y, 13, cor, direita=True, mono=True)
            else:
                self.texto("–", x + 50, y, 13, cor)

    def desenhar_legenda(self, rect):
        self._painel(rect, "Legenda")
        itens = [(COR_TERRENO[t], f"{config.NOME_TERRENO[t]} (+{config.CUSTO_TERRENO[t]})")
                 for t in ("M", "A", "F", "R", ".")]
        itens += [(COR_EXPANDIDO, "Estado expandido"), (COR_FRONTEIRA, "Fronteira"),
                  (COR_CAMINHO, "Rota percorrida")]
        for k, (cor, nome) in enumerate(itens):
            col, lin = divmod(k, 5)
            x = rect.x + 12 + col * 165
            y = rect.y + 40 + lin * 22
            pygame.draw.rect(self.tela, cor, (x, y + 2, 16, 12))
            pygame.draw.rect(self.tela, REGRA, (x, y + 2, 16, 12), 1)
            self.texto(nome, x + 24, y, 14)

    def desenhar_controles(self, rect):
        self._painel(rect, "Controles")
        self.texto(f"{'Em execução' if self.tocando else 'Pausado'} · velocidade {self.velocidade + 1} de 8",
                   rect.x + 12, rect.y + 38, 14, TEXTO, negrito=True)
        self.texto("Espaço: iniciar ou pausar · Seta direita: um passo", rect.x + 12, rect.y + 60, 12, TEXTO_SUAVE)
        self.texto("Setas cima e baixo: velocidade · S: pular etapa", rect.x + 12, rect.y + 77, 12, TEXTO_SUAVE)
        self.texto("R: reiniciar · Tab: resultados · Esc: sair", rect.x + 12, rect.y + 94, 12, TEXTO_SUAVE)
        x = rect.x + 12
        for k, nome in enumerate(self.camadas):
            cor = TEXTO if self.camadas[nome] else (170, 168, 162)
            x = self.texto(f"[{k + 1}] {nome}", x, rect.y + 114, 12, cor).right + 12
        for k, a in enumerate(self.resumo.avisos[:1]):
            self.texto("Aviso: " + a, rect.x + 12, rect.y + 132 + k * 16, 12, ERRO)

    def _regra(self, x0, x1, y, grossa=False):
        pygame.draw.line(self.tela, REGRA, (x0, y), (x1, y), 2 if grossa else 1)

    def desenhar_resultado(self):
        veu = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        veu.fill((236, 234, 228, 240))
        self.tela.blit(veu, (0, 0))
        r = self.resumo
        painel = pygame.Rect(40, 36, LARGURA - 80, ALTURA - 72)
        pygame.draw.rect(self.tela, BRANCO, painel)
        pygame.draw.rect(self.tela, BORDA, painel, 1)
        self.texto("Resultados", painel.x + 24, painel.y + 14, 26, TEXTO, negrito=True)
        self.texto("Tab ou Esc para voltar", painel.right - 24, painel.y + 24, 13, TEXTO_SUAVE, direita=True)

        meia = (painel.w - 48) // 2
        topo = painel.y + 66
        self.texto("Tabela 1. Ordem de visita aos ginásios e Pokémons usados em cada batalha.",
                   painel.x + 24, topo, 13, TEXTO_SUAVE, italico=True)
        topo += 26
        cab = [("Ordem", 0), ("Ginásio", 56), ("Dific.", 126), ("Pokémons", 190), ("Tempo (min)", meia - 36)]
        for col in range(2):
            x0 = painel.x + 24 + col * meia
            x1 = x0 + meia - 24
            self._regra(x0, x1, topo, grossa=True)
            for txt, dx in cab:
                self.texto(txt, x0 + dx if dx != meia - 36 else x1, topo + 4, 13, TEXTO, negrito=True,
                           direita=dx == meia - 36)
            self._regra(x0, x1, topo + 26)
            for lin in range(12):
                k = col * 12 + lin
                if k >= len(r.ordem):
                    break
                g = r.ordem[k]
                y = topo + 32 + lin * 25
                self.texto(k + 1, x0 + 14, y, 14, mono=True)
                self.texto(g, x0 + 56, y, 14, negrito=True)
                self.texto(config.DIFICULDADE_GINASIOS[g], x0 + 126, y, 14, mono=True)
                xp = x0 + 190
                for p in r.pokemons_usados[g]:
                    xp = self._chip(p, xp, y + 1).right + 3
                self.texto(_fmt(r.tempo_batalha[g], 2), x1, y, 14, direita=True, mono=True)
            self._regra(x0, x1, topo + 32 + 12 * 25 + 2, grossa=True)

        y = topo + 32 + 12 * 25 + 28
        x0 = painel.x + 24
        self.texto("Tabela 2. Custos da solução.", x0, y, 13, TEXTO_SUAVE, italico=True)
        y += 24
        larg = meia - 48
        self._regra(x0, x0 + larg, y, grossa=True)
        dados = [("Custo da rota", f"{r.custo_rota} min"),
                 ("Custo das batalhas", f"{_fmt(r.custo_batalhas, 2)} min"),
                 ("Custo total", f"{_fmt(r.custo_total, 2)} min"),
                 ("Estados expandidos pelo A*", _milhar(self.n_expandidos))]
        for k, (nome, val) in enumerate(dados):
            yy = y + 8 + k * 26
            if nome == "Custo total":
                self._regra(x0, x0 + larg, yy - 4)
            self.texto(nome, x0, yy, 15, negrito=nome == "Custo total")
            self.texto(val, x0 + larg, yy, 15, negrito=nome == "Custo total", direita=True, mono=True)
        self._regra(x0, x0 + larg, y + 8 + 4 * 26 + 2, grossa=True)

        ex = painel.x + 24 + meia
        self.texto("Tabela 3. Energia final de cada Pokémon.", ex, y - 24, 13, TEXTO_SUAVE, italico=True)
        self._regra(ex, ex + larg, y, grossa=True)
        for k, (nome, e) in enumerate(r.energia_final.items()):
            yy = y + 8 + k * 26
            self._chip(nome, ex, yy + 1, e > 0)
            self.texto(nome, ex + 34, yy, 15)
            for s in range(config.ENERGIA_INICIAL):
                quad = pygame.Rect(ex + 170 + s * 26, yy + 3, 22, 14)
                if s < e:
                    pygame.draw.rect(self.tela, COR_POKEMON[nome], quad)
                pygame.draw.rect(self.tela, REGRA if s < e else BORDA, quad, 1)
            self.texto(f"{e}/{config.ENERGIA_INICIAL}", ex + larg, yy, 15, direita=True, mono=True,
                       cor=TEXTO if e > 0 else ERRO)
        self._regra(ex, ex + larg, y + 8 + 5 * 26 + 2, grossa=True)
        for k, a in enumerate(r.avisos[:2]):
            self.texto("Aviso: " + a, painel.x + 24, painel.bottom - 40 + k * 16, 12, ERRO)

    def desenhar(self):
        self.tela.fill(FUNDO)
        self.desenhar_cabecalho()
        self.desenhar_mapa()
        self.desenhar_legenda_figura()
        topo = MAPA_Y + self.mapa_rect.h + 40
        self.desenhar_custos(pygame.Rect(40, topo, 330, 230))
        self.desenhar_legenda(pygame.Rect(40, topo + 242, 330, 158))
        self.desenhar_pokemons(pygame.Rect(386, topo, 420, 262))
        self.desenhar_controles(pygame.Rect(386, topo + 274, 420, 148))
        self.desenhar_ginasios(pygame.Rect(822, topo, 418, 422))
        if self.mostrar_resultado:
            self.desenhar_resultado()

    # ------------------------------------------------------------ laço
    def tratar_evento(self, ev):
        if ev.type == pygame.QUIT:
            return False
        if ev.type != pygame.KEYDOWN:
            return True
        if ev.key == pygame.K_ESCAPE:
            if self.mostrar_resultado:
                self.mostrar_resultado = False
            else:
                return False
        elif ev.key == pygame.K_SPACE:
            if self.fase == "fim":
                self.reiniciar()
            else:
                self.tocando = not self.tocando
        elif ev.key == pygame.K_RIGHT:
            self.tocando = False
            self.avancar(passos_unitarios=1)
        elif ev.key == pygame.K_UP:
            self.velocidade = min(self.velocidade + 1, 7)
        elif ev.key == pygame.K_DOWN:
            self.velocidade = max(self.velocidade - 1, 0)
        elif ev.key == pygame.K_s:
            self.pular()
        elif ev.key == pygame.K_r:
            self.reiniciar()
        elif ev.key == pygame.K_TAB:
            self.mostrar_resultado = not self.mostrar_resultado
        elif pygame.K_1 <= ev.key <= pygame.K_4:
            nome = list(self.camadas)[ev.key - pygame.K_1]
            self.camadas[nome] = not self.camadas[nome]
        return True

    def executar(self):
        rodando = True
        while rodando:
            for ev in pygame.event.get():
                rodando = self.tratar_evento(ev) and rodando
            if self.tocando and not self.mostrar_resultado:
                self.avancar()
            self.desenhar()
            pygame.display.flip()
            self.relogio.tick(60)
        pygame.quit()

    def salvar_captura(self, caminho):
        self.desenhar()
        pygame.image.save(self.tela, caminho)


def main(argv=None):
    from .demo_mock import gerar_replay

    argv = sys.argv[1:] if argv is None else argv
    mapa = Mapa.carregar()
    ui = Interface(mapa, gerar_replay(mapa))
    if "--captura" in argv:  # --captura arquivo.png [busca|exec|fim] [fracao]
        k = argv.index("--captura")
        arq = argv[k + 1]
        fase = argv[k + 2] if len(argv) > k + 2 else "fim"
        fracao = float(argv[k + 3]) if len(argv) > k + 3 else 0.5
        ui.pular_para(fase, fracao)
        ui.salvar_captura(arq)
        pygame.quit()
        return
    ui.executar()


if __name__ == "__main__":
    main()
