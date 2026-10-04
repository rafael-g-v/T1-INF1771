"""Interface gráfica (pygame) que reproduz a execução do agente em Kanto.

Fase 1 (busca):    reproduz os eventos do A* (fronteira e estados expandidos).
Fase 2 (execução): o agente percorre o caminho final, acumulando custos.
Fase 3 (fim):      tela de resultados.

Uso:  python -m src.interface
"""
import math
import sys

import pygame

from . import arte, config
from .mapa import Mapa
from .replay import EXPANDIR, GERAR, NOVA
from .resumo import calcular_resumo

# ---------------------------------------------------------------- layout
LARGURA, ALTURA = 1280, 880
CELULA = 8
MAPA_X, MAPA_Y = 40, 64

# ---------------------------------------------------------------- cores
FUNDO = (22, 24, 31)
PAINEL = (33, 36, 46)
BORDA = (58, 63, 80)
TEXTO = (232, 234, 240)
TEXTO_SUAVE = (150, 156, 175)
DESTAQUE = (255, 205, 70)
ERRO = (255, 107, 107)
OK = (110, 214, 140)

COR_TERRENO = {
    "M": (140, 98, 62),
    "A": (58, 128, 220),
    "F": (60, 140, 72),
    "R": (152, 152, 164),
    ".": (228, 238, 200),
}
COR_EXPANDIDO = (255, 120, 40)
COR_FRONTEIRA = (0, 220, 235)
COR_CAMINHO = (255, 40, 150)
COR_AGENTE = (255, 60, 60)
COR_ORIGEM = (255, 205, 70)
COR_DESTINO = (170, 110, 255)
COR_GINASIO = (30, 30, 40)
COR_VISITADO = (60, 190, 110)

COR_POKEMON = {
    "Pikachu": (255, 214, 64),
    "Bulbassauro": (80, 200, 170),
    "Rattata": (176, 120, 220),
    "Caterpie": (150, 220, 90),
    "Weedle": (255, 160, 70),
}

EVENTOS_POR_QUADRO = [1, 4, 16, 64, 256, 1024, 4096, 16384]
PASSOS_POR_QUADRO = [0.1, 0.25, 0.5, 1, 2, 4, 8, 16]


def _sup_transparente(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


class Interface:
    def __init__(self, mapa, replay):
        self.mapa = mapa
        self.replay = replay
        self.resumo = calcular_resumo(mapa, replay)
        self.caminho = replay.caminho

        pygame.init()
        pygame.display.set_caption("Kanto — Busca Heurística (INF1771)")
        self.tela = pygame.display.set_mode((LARGURA, ALTURA), pygame.SCALED | pygame.RESIZABLE)
        self.relogio = pygame.time.Clock()
        self._fontes = {}

        mw, mh = mapa.largura * CELULA, mapa.altura * CELULA
        self.mapa_rect = pygame.Rect(MAPA_X, MAPA_Y, mw, mh)
        self.sup_terreno = [arte.desenhar_terreno(mapa, CELULA, f) for f in (0, 1)]
        self.sup_exp = _sup_transparente(mw, mh)
        self.sup_fro = _sup_transparente(mw, mh)
        self.pontos_caminho = [
            (c * CELULA + CELULA // 2, r * CELULA + CELULA // 2) for r, c in self.caminho
        ]
        self.camadas = {"expandidos": True, "fronteira": True, "caminho": True, "rotulos": True}
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
                self.sup_fro.fill((*COR_FRONTEIRA, 190), rect)
        elif tipo == EXPANDIR:
            self.n_expandidos += 1
            n = self.contagem.get((r, c), 0) + 1
            self.contagem[(r, c)] = n
            self.sup_fro.fill((0, 0, 0, 0), rect)
            self.sup_exp.fill((*COR_EXPANDIDO, min(70 + 35 * n, 200)), rect)

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
    def fonte(self, tamanho, negrito=False):
        chave = (tamanho, negrito)
        if chave not in self._fontes:
            self._fontes[chave] = pygame.font.SysFont("segoeui,arial,dejavusans", tamanho, bold=negrito)
        return self._fontes[chave]

    def texto(self, txt, x, y, tam=15, cor=TEXTO, negrito=False, centro=False, direita=False):
        img = self.fonte(tam, negrito).render(str(txt), True, cor)
        rect = img.get_rect()
        if centro:
            rect.center = (x, y)
        elif direita:
            rect.topright = (x, y)
        else:
            rect.topleft = (x, y)
        self.tela.blit(img, rect)
        return rect

    def _centro(self, pos):
        r, c = pos
        return (MAPA_X + c * CELULA + CELULA // 2, MAPA_Y + r * CELULA + CELULA // 2)

    def _painel(self, rect, titulo=None):
        pygame.draw.rect(self.tela, PAINEL, rect, border_radius=10)
        pygame.draw.rect(self.tela, BORDA, rect, width=1, border_radius=10)
        if titulo:
            self.texto(titulo, rect.x + 14, rect.y + 10, 15, TEXTO_SUAVE, negrito=True)

    def _marcador(self, pos, rotulo, cor_fundo, cor_texto=TEXTO, raio=8):
        cx, cy = self._centro(pos)
        pygame.draw.circle(self.tela, (255, 255, 255), (cx, cy), raio + 1)
        pygame.draw.circle(self.tela, cor_fundo, (cx, cy), raio)
        if self.camadas["rotulos"]:
            self.texto(rotulo, cx, cy, 12, cor_texto, negrito=True, centro=True)

    def desenhar_mapa(self):
        t = pygame.time.get_ticks() / 1000
        pygame.draw.rect(self.tela, BORDA, self.mapa_rect.inflate(6, 6), border_radius=4)
        self.tela.blit(self.sup_terreno[int(t * 1.5) % 2], self.mapa_rect)
        if self.camadas["expandidos"]:
            self.tela.blit(self.sup_exp, self.mapa_rect)
        if self.camadas["fronteira"]:
            self.sup_fro.set_alpha(int(170 + 85 * math.sin(t * 6)))
            self.tela.blit(self.sup_fro, self.mapa_rect)

        i = self.passo_i
        if self.camadas["caminho"] and self.fase != "busca" and len(self.pontos_caminho) > 1:
            off = [(x + MAPA_X, y + MAPA_Y) for x, y in self.pontos_caminho]
            pygame.draw.lines(self.tela, (255, 255, 255), False, off, 1)
            if i > 0:
                pygame.draw.lines(self.tela, (90, 10, 60), False, off[: i + 1], 5)
                pygame.draw.lines(self.tela, COR_CAMINHO, False, off[: i + 1], 3)

        visitados = {g: k + 1 for k, g in enumerate(self.resumo.ordem)
                     if self.fase != "busca" and self._passo_do(g) <= i}
        for g, pos in self.mapa.ginasios.items():
            if g in visitados:
                self._marcador(pos, str(visitados[g]), COR_VISITADO, (10, 30, 15), raio=9)
            else:
                self._marcador(pos, g, COR_GINASIO)
        self._marcador(self.mapa.origem, config.ORIGEM, COR_ORIGEM, (40, 30, 0), raio=9)
        self._marcador(self.mapa.destino, config.DESTINO, COR_DESTINO, (255, 255, 255), raio=9)

        if self.fase != "busca" and self.caminho:
            cx, cy = self._centro(self.caminho[i])
            cy += int(1.5 * math.sin(t * 8))
            bola = arte.pokebola(8, 0.5 + 0.5 * math.sin(t * 5))
            self.tela.blit(bola, bola.get_rect(center=(cx, cy)))
            if self.batalha is not None:
                self._balao_batalha(cx, cy, t)

    def _balao_batalha(self, cx, cy, t):
        """Balão sobre o ginásio mostrando quem luta e quanto tempo a batalha leva."""
        g = self.batalha
        pokes = self.resumo.pokemons_usados[g]
        larg = max(190, 30 + 34 * len(pokes) + 20)
        alt = 74
        x = min(max(cx - larg // 2, self.mapa_rect.x + 4), self.mapa_rect.right - larg - 4)
        y = cy - alt - 18
        if y < self.mapa_rect.y + 4:
            y = cy + 18
        rect = pygame.Rect(x, y, larg, alt)
        pygame.draw.rect(self.tela, (18, 20, 28), rect, border_radius=10)
        pygame.draw.rect(self.tela, DESTAQUE, rect, 2, border_radius=10)
        self.texto(f"Ginásio {g} · dificuldade {config.DIFICULDADE_GINASIOS[g]}", rect.centerx, rect.y + 12,
                   13, TEXTO, negrito=True, centro=True)
        n = len(pokes)
        x0 = rect.centerx - (n * 34) // 2
        for k, p in enumerate(pokes):
            spr = arte.sprite_pokemon(p, 28)
            self.tela.blit(spr, (x0 + k * 34, rect.y + 24 + int(2 * math.sin(t * 9 + k))))
        self.texto(f"{self.resumo.tempo_batalha[g]:.1f} min", rect.centerx, rect.bottom - 11, 13, DESTAQUE,
                   negrito=True, centro=True)

    def _passo_do(self, g):
        if not hasattr(self, "_passos_ginasio"):
            self._passos_ginasio = {gid: p for p, gid in self.resumo.ginasio_no_passo.items()}
        return self._passos_ginasio.get(g, 10**9)

    def desenhar_cabecalho(self):
        bola = arte.pokebola(14)
        self.tela.blit(bola, (MAPA_X - 4, 8))
        self.texto("Kanto — Busca Heurística", MAPA_X + 38, 14, 26, TEXTO, negrito=True)
        rotulos = {"busca": f"Fase 1/2 · Busca {self.replay.rotulo}",
                   "exec": "Fase 2/2 · Agente em movimento",
                   "fim": "Concluído"}
        self.texto(rotulos[self.fase], MAPA_X + 370, 22, 16, DESTAQUE, negrito=True)
        mx, my = pygame.mouse.get_pos()
        c, r = (mx - MAPA_X) // CELULA, (my - MAPA_Y) // CELULA
        if self.mapa_rect.collidepoint(mx, my) and self.mapa.dentro(r, c):
            ch = self.mapa.simbolo(r, c)
            if ch in config.NOME_TERRENO:
                nome = f"{config.NOME_TERRENO[ch]} (+{config.CUSTO_TERRENO[ch]} min)"
            elif ch in config.DIFICULDADE_GINASIOS:
                nome = f"Ginásio {ch} · dificuldade {config.DIFICULDADE_GINASIOS[ch]}"
            else:
                nome = "Origem" if ch == config.ORIGEM else "Destino"
            self.texto(f"({r}, {c})  {nome}", LARGURA - MAPA_X, 24, 15, TEXTO_SUAVE, direita=True)

    def _valores_atuais(self):
        r = self.resumo
        if self.fase == "busca":
            return 0, 0.0, 0, 0
        i = self.passo_i
        return r.rota_acum[i], r.bat_acum[i], r.batalhas_ate[i], len(r.ginasio_no_passo)

    def desenhar_custos(self, rect):
        self._painel(rect, "CUSTOS")
        rota, bat, nbat, _ = self._valores_atuais()
        linhas = [("Rota", f"{rota} min"), ("Batalhas", f"{bat:.1f} min"),
                  ("Total", f"{rota + bat:.1f} min")]
        y = rect.y + 38
        for k, (nome, val) in enumerate(linhas):
            forte = k == 2
            self.texto(nome, rect.x + 16, y, 18 if forte else 16, TEXTO_SUAVE if not forte else TEXTO)
            self.texto(val, rect.right - 16, y - (2 if forte else 0), 24 if forte else 18,
                       DESTAQUE if forte else TEXTO, negrito=True, direita=True)
            y += 34 if not forte else 0
        y = rect.y + 38 + 34 * 2 + 40
        self.texto("Estados expandidos", rect.x + 16, y, 14, TEXTO_SUAVE)
        self.texto(str(self.n_expandidos), rect.right - 16, y - 2, 16, COR_EXPANDIDO,
                   negrito=True, direita=True)
        self.texto("Estados gerados (fronteira)", rect.x + 16, y + 24, 14, TEXTO_SUAVE)
        self.texto(str(self.n_gerados), rect.right - 16, y + 22, 16, COR_FRONTEIRA,
                   negrito=True, direita=True)
        self.texto("Ginásios visitados", rect.x + 16, y + 48, 14, TEXTO_SUAVE)
        n = sum(1 for p in self.resumo.ginasio_no_passo if p <= self.passo_i) if self.fase != "busca" else 0
        self.texto(f"{n}/{len(self.mapa.ginasios)}", rect.right - 16, y + 46, 16, COR_VISITADO,
                   negrito=True, direita=True)

    def desenhar_pokemons(self, rect):
        self._painel(rect, "ENERGIA DOS POKÉMONS")
        k = 0 if self.fase == "busca" else self.resumo.batalhas_ate[self.passo_i]
        energias = self.resumo.energias[k]
        y = rect.y + 40
        for nome, poder in config.PODER_POKEMONS.items():
            e = energias[nome]
            cor = COR_POKEMON[nome] if e > 0 else (90, 94, 108)
            spr = arte.sprite_pokemon(nome, 36)
            if e <= 0:
                spr = spr.copy()
                spr.fill((90, 90, 100, 255), special_flags=pygame.BLEND_RGBA_MIN)
            self.tela.blit(spr, (rect.x + 10, y - 6))
            self.texto(nome, rect.x + 52, y, 15, TEXTO if e > 0 else TEXTO_SUAVE)
            self.texto(f"poder {poder}", rect.x + 52, y + 17, 11, TEXTO_SUAVE)
            for s in range(config.ENERGIA_INICIAL):
                bx = rect.x + 160 + s * 30
                pygame.draw.rect(self.tela, cor if s < e else (52, 56, 70), (bx, y + 4, 26, 16),
                                 border_radius=4)
            self.texto(f"{e}/{config.ENERGIA_INICIAL}", rect.right - 14, y + 2, 15,
                       TEXTO if e > 0 else ERRO, negrito=True, direita=True)
            y += 46

    def desenhar_ginasios(self, rect):
        self._painel(rect, "GINÁSIOS (ordem de visita)")
        r = self.resumo
        n = 0 if self.fase == "busca" else sum(1 for p in r.ginasio_no_passo if p <= self.passo_i)
        col_w = (rect.w - 20) // 2
        for k, g in enumerate(r.ordem):
            col, lin = divmod(k, 12)
            x = rect.x + 12 + col * col_w
            y = rect.y + 40 + lin * 28
            feito = k < n
            atual = k == n - 1
            if atual:
                pygame.draw.rect(self.tela, (60, 66, 88), (x - 4, y - 3, col_w - 6, 25), border_radius=5)
            cor = TEXTO if feito else (95, 100, 118)
            self.texto(f"{k + 1:>2}", x, y, 13, cor, negrito=atual)
            self.texto(g if self.fase != "busca" else "?", x + 26, y, 13,
                       COR_VISITADO if feito else cor, negrito=True)
            if feito:
                x2 = x + 48
                for p in r.pokemons_usados[g]:
                    self.tela.blit(arte.sprite_pokemon(p, 20), (x2, y - 1))
                    x2 += 21
                self.texto(f"{r.tempo_batalha[g]:.1f}", x + col_w - 14, y, 13, cor, direita=True)
            else:
                self.texto("—", x + 48, y, 13, cor)

    def desenhar_legenda(self, rect):
        self._painel(rect, "LEGENDA")
        itens = [(COR_TERRENO[t], f"{config.NOME_TERRENO[t]} +{config.CUSTO_TERRENO[t]}")
                 for t in ("M", "A", "F", "R", ".")]
        itens += [(COR_EXPANDIDO, "Expandido"), (COR_FRONTEIRA, "Fronteira"),
                  (COR_CAMINHO, "Caminho"), (COR_AGENTE, "Agente")]
        for k, (cor, nome) in enumerate(itens):
            col, lin = divmod(k, 5)
            x = rect.x + 16 + col * 150
            y = rect.y + 38 + lin * 22
            pygame.draw.rect(self.tela, cor, (x, y + 2, 16, 14), border_radius=3)
            pygame.draw.rect(self.tela, BORDA, (x, y + 2, 16, 14), 1, border_radius=3)
            self.texto(nome, x + 24, y, 14)

    def desenhar_controles(self, rect):
        self._painel(rect)
        self.texto(f"{'Tocando' if self.tocando else 'Pausado'}  ·  velocidade {self.velocidade + 1}/8",
                   rect.x + 14, rect.y + 10, 14, DESTAQUE, negrito=True)
        self.texto("Espaço play/pausa · → passo · ↑/↓ velocidade", rect.x + 14, rect.y + 34, 12, TEXTO_SUAVE)
        self.texto("S pular · R reiniciar · Tab resultados · Esc sair", rect.x + 14, rect.y + 52, 12, TEXTO_SUAVE)
        x = rect.x + 14
        for k, nome in enumerate(self.camadas):
            cor = OK if self.camadas[nome] else (95, 100, 118)
            x = self.texto(f"[{k + 1}] {nome}", x, rect.y + 74, 12, cor).right + 14
        for k, a in enumerate(self.resumo.avisos[:2]):
            self.texto("⚠ " + a, rect.x + 14, rect.y + 96 + k * 16, 12, ERRO)

    def desenhar_resultado(self):
        sombra = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        sombra.fill((10, 11, 16, 225))
        self.tela.blit(sombra, (0, 0))
        r = self.resumo
        painel = pygame.Rect(40, 40, LARGURA - 80, ALTURA - 80)
        self._painel(painel)
        self.texto("Resultado final", painel.x + 24, painel.y + 16, 28, TEXTO, negrito=True)
        self.texto("Tab ou Esc para fechar", painel.right - 24, painel.y + 26, 14, TEXTO_SUAVE, direita=True)

        topo = painel.y + 76
        cab = ["#", "Gin.", "Dif.", "Pokémons", "Tempo"]
        col_w = (painel.w - 48) // 2 - 220
        for col in range(2):
            x0 = painel.x + 24 + col * ((painel.w - 48) // 2)
            for txt, dx in zip(cab, (0, 34, 74, 124, 360)):
                self.texto(txt, x0 + dx, topo, 13, TEXTO_SUAVE, negrito=True)
            for lin in range(12):
                k = col * 12 + lin
                if k >= len(r.ordem):
                    break
                g = r.ordem[k]
                y = topo + 26 + lin * 27
                if lin % 2 == 0:
                    pygame.draw.rect(self.tela, (40, 44, 56), (x0 - 6, y - 3, (painel.w - 48) // 2 - 16, 25),
                                     border_radius=4)
                self.texto(k + 1, x0, y, 15)
                self.texto(g, x0 + 34, y, 15, DESTAQUE, negrito=True)
                self.texto(config.DIFICULDADE_GINASIOS[g], x0 + 74, y, 15, TEXTO_SUAVE)
                xp = x0 + 124
                for p in r.pokemons_usados[g]:
                    self.tela.blit(arte.sprite_pokemon(p, 24), (xp, y - 1))
                    xp += 28
                self.texto(f"{r.tempo_batalha[g]:.2f}", x0 + 360, y, 15)

        y = topo + 26 + 12 * 27 + 20
        # custos
        cx = painel.x + 24
        self.texto("CUSTOS", cx, y, 14, TEXTO_SUAVE, negrito=True)
        dados = [("Rota", f"{r.custo_rota} min"), ("Batalhas", f"{r.custo_batalhas:.2f} min"),
                 ("Total", f"{r.custo_total:.2f} min"),
                 ("Estados expandidos", f"{self.n_expandidos}")]
        for k, (nome, val) in enumerate(dados):
            forte = nome == "Total"
            self.texto(nome, cx, y + 26 + k * 28, 17 if forte else 16, TEXTO if forte else TEXTO_SUAVE)
            self.texto(val, cx + 380, y + 26 + k * 28, 18, DESTAQUE if forte else TEXTO, negrito=True,
                       direita=True)
        # energia final
        ex = painel.x + 24 + (painel.w - 48) // 2
        self.texto("ENERGIA FINAL", ex, y, 14, TEXTO_SUAVE, negrito=True)
        for k, (nome, e) in enumerate(r.energia_final.items()):
            cor = COR_POKEMON[nome] if e > 0 else (90, 94, 108)
            yy = y + 26 + k * 24
            self.tela.blit(arte.sprite_pokemon(nome, 22), (ex, yy - 1))
            self.texto(nome, ex + 28, yy, 15, TEXTO if e > 0 else TEXTO_SUAVE)
            for s in range(config.ENERGIA_INICIAL):
                pygame.draw.rect(self.tela, cor if s < e else (52, 56, 70), (ex + 190 + s * 26, yy + 3, 22, 14),
                                 border_radius=3)
            self.texto(f"{e}/{config.ENERGIA_INICIAL}", ex + 360, yy, 15, TEXTO if e > 0 else ERRO,
                       negrito=True)
        for k, a in enumerate(r.avisos[:2]):
            self.texto("⚠ " + a, painel.x + 24, painel.bottom - 40 + k * 16, 12, ERRO)

    def desenhar(self):
        self.tela.fill(FUNDO)
        self.desenhar_cabecalho()
        self.desenhar_mapa()
        topo = MAPA_Y + self.mapa_rect.h + 22
        self.desenhar_custos(pygame.Rect(40, topo, 330, 250))
        self.desenhar_legenda(pygame.Rect(40, topo + 262, 330, 154))
        self.desenhar_pokemons(pygame.Rect(386, topo, 420, 270))
        self.desenhar_controles(pygame.Rect(386, topo + 282, 420, 134))
        self.desenhar_ginasios(pygame.Rect(822, topo, 418, 416))
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
