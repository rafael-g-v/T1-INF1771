"""Arte procedural da interface: terreno texturizado e sprites desenhados em código.

Nada aqui depende de arquivos de imagem: tudo é desenhado com pygame.draw.
"""
import math

import pygame

COR_AGUA = (58, 128, 220)
COR_GRAMA = (228, 238, 200)


def _h(r, c, k=0):
    """Hash determinístico por célula (dá variação sem aleatoriedade)."""
    return ((r * 73856093) ^ (c * 19349663) ^ (k * 83492791)) & 0xFFFF


# ------------------------------------------------------------------ terreno
def _celula_livre(sup, x, y, n, h):
    sup.fill(COR_GRAMA, (x, y, n, n))
    if h % 5 == 0:
        sup.fill((206, 224, 172), (x + h % (n - 1), y + (h >> 3) % (n - 1), 1, 1))
    if h % 11 == 0:
        sup.fill((250, 250, 235), (x + (h >> 2) % (n - 1), y + (h >> 5) % (n - 1), 1, 1))


def _celula_agua(sup, x, y, n, h, fase, vizinhos):
    sup.fill(COR_AGUA, (x, y, n, n))
    if h % 3 == 0:
        dx = (fase * 2 + (h >> 4)) % (n - 3)
        sup.fill((118, 176, 244), (x + dx, y + 2 + (h >> 7) % (n - 4), 3, 1))
    for lado, terra in vizinhos.items():  # espuma na borda com a terra
        if terra:
            espuma = (196, 226, 252)
            if lado == "N":
                sup.fill(espuma, (x, y, n, 1))
            elif lado == "S":
                sup.fill(espuma, (x, y + n - 1, n, 1))
            elif lado == "O":
                sup.fill(espuma, (x, y, 1, n))
            else:
                sup.fill(espuma, (x + n - 1, y, 1, n))


def _celula_montanha(sup, x, y, n, h):
    sup.fill((154, 112, 74), (x, y, n, n))
    off = (h % 3) - 1
    base = y + n - 1
    pts = [(x, base), (x + n // 2 + off, y), (x + n - 1, base)]
    pygame.draw.polygon(sup, (120, 82, 52), pts)
    # lado iluminado
    pygame.draw.polygon(sup, (176, 132, 92), [pts[0], pts[1], (pts[1][0], base)])
    # neve no cume
    px, py = pts[1]
    pygame.draw.polygon(sup, (242, 242, 248), [(px - 1, py + 2), (px, py), (px + 1, py + 2)])


def _celula_floresta(sup, x, y, n, h):
    sup.fill((92, 168, 98), (x, y, n, n))
    ox = (h % 3) - 1
    sup.fill((110, 78, 48), (x + n // 2 + ox, y + n - 3, 1, 3))
    pygame.draw.circle(sup, (36, 112, 62), (x + n // 2 + ox, y + 3), 3)
    sup.fill((78, 170, 92), (x + n // 2 + ox - 1, y + 2, 1, 1))


def _celula_rocha(sup, x, y, n, h):
    sup.fill((152, 152, 164), (x, y, n, n))
    for k in range(3):
        hk = _h(h, k, 7)
        sup.fill((112, 112, 126), (x + hk % (n - 1), y + (hk >> 4) % (n - 1), 2, 1))
    hk = _h(h, 9, 3)
    sup.fill((198, 198, 210), (x + hk % (n - 2), y + (hk >> 3) % (n - 2), 2, 2))


def desenhar_terreno(mapa, celula, fase=0):
    """Superfície do mapa inteiro. `fase` anima as ondas da água (0 ou 1)."""
    sup = pygame.Surface((mapa.largura * celula, mapa.altura * celula))
    grade = mapa.grade

    def tipo(r, c):
        if not mapa.dentro(r, c):
            return None
        ch = grade[r][c]
        return ch if ch in "MAFR." else "."

    for r in range(mapa.altura):
        for c in range(mapa.largura):
            t = tipo(r, c)
            x, y, h = c * celula, r * celula, _h(r, c)
            if t == ".":
                _celula_livre(sup, x, y, celula, h)
            elif t == "A":
                viz = {"N": tipo(r - 1, c) not in ("A", None), "S": tipo(r + 1, c) not in ("A", None),
                       "O": tipo(r, c - 1) not in ("A", None), "L": tipo(r, c + 1) not in ("A", None)}
                _celula_agua(sup, x, y, celula, h, fase, viz)
            elif t == "M":
                _celula_montanha(sup, x, y, celula, h)
            elif t == "F":
                _celula_floresta(sup, x, y, celula, h)
            else:
                _celula_rocha(sup, x, y, celula, h)
    return sup


# ------------------------------------------------------------------ sprites
def _elipse(s, cor, cx, cy, rx, ry):
    pygame.draw.ellipse(s, cor, (cx - rx, cy - ry, 2 * rx, 2 * ry))


def _olho(s, cx, cy, r=3, cor=(20, 20, 30)):
    pygame.draw.circle(s, cor, (cx, cy), r)
    pygame.draw.circle(s, (255, 255, 255), (cx - 1, cy - 1), max(1, r // 3))


def _pikachu(s):
    amarelo = (255, 214, 64)
    for sinal in (-1, 1):
        base = 32 + sinal * 12
        pygame.draw.polygon(s, amarelo, [(base - 6, 20), (32 + sinal * 20, 2), (base + 6, 18)])
        pygame.draw.polygon(s, (30, 30, 30), [(32 + sinal * 20 - 3, 7), (32 + sinal * 20, 2), (32 + sinal * 20 + 3, 9)])
    _elipse(s, amarelo, 32, 40, 17, 15)
    pygame.draw.circle(s, amarelo, (32, 30), 16)
    _olho(s, 25, 28)
    _olho(s, 39, 28)
    for sinal in (-1, 1):
        pygame.draw.circle(s, (232, 70, 60), (32 + sinal * 14, 37), 4)
    pygame.draw.arc(s, (60, 30, 20), (28, 32, 8, 6), math.pi, 2 * math.pi, 2)


def _bulbassauro(s):
    for sinal in (-1, 1):
        pygame.draw.polygon(s, (70, 150, 140), [(32 + sinal * 10, 24), (32 + sinal * 20, 18), (32 + sinal * 16, 32)])
    _elipse(s, (110, 196, 176), 32, 42, 20, 15)
    pygame.draw.circle(s, (110, 196, 176), (32, 32), 15)
    # bulbo
    pygame.draw.circle(s, (88, 170, 76), (32, 16), 12)
    pygame.draw.circle(s, (62, 138, 58), (32, 16), 12, 2)
    pygame.draw.line(s, (62, 138, 58), (32, 5), (32, 28), 2)
    _olho(s, 24, 32, 3, (200, 40, 50))
    _olho(s, 40, 32, 3, (200, 40, 50))
    pygame.draw.arc(s, (40, 70, 60), (27, 36, 10, 6), math.pi, 2 * math.pi, 2)


def _rattata(s):
    roxo = (176, 124, 216)
    for sinal in (-1, 1):
        pygame.draw.circle(s, roxo, (32 + sinal * 14, 14), 9)
        pygame.draw.circle(s, (240, 190, 210), (32 + sinal * 14, 15), 4)
    _elipse(s, roxo, 32, 40, 19, 16)
    pygame.draw.circle(s, roxo, (32, 30), 16)
    _elipse(s, (244, 228, 204), 32, 44, 10, 8)
    _olho(s, 25, 28)
    _olho(s, 39, 28)
    pygame.draw.circle(s, (40, 30, 40), (32, 34), 2)
    pygame.draw.rect(s, (255, 255, 255), (29, 38, 3, 5))
    pygame.draw.rect(s, (255, 255, 255), (33, 38, 3, 5))
    for sinal in (-1, 1):
        pygame.draw.line(s, (60, 40, 70), (32 + sinal * 8, 34), (32 + sinal * 22, 31), 1)
        pygame.draw.line(s, (60, 40, 70), (32 + sinal * 8, 36), (32 + sinal * 22, 38), 1)


def _caterpie(s):
    verde = (146, 212, 84)
    for cx, cy, r in ((12, 46, 8), (24, 44, 10), (38, 42, 12)):
        pygame.draw.circle(s, verde, (cx, cy), r)
        pygame.draw.circle(s, (96, 160, 56), (cx, cy), r, 2)
    pygame.draw.circle(s, verde, (46, 34), 15)
    pygame.draw.circle(s, (96, 160, 56), (46, 34), 15, 2)
    for dx in (-5, 5):
        pygame.draw.line(s, (220, 60, 60), (46 + dx, 21), (46 + dx * 2, 8), 3)
    _olho(s, 40, 34, 4, (30, 30, 30))
    _olho(s, 52, 34, 4, (30, 30, 30))
    pygame.draw.arc(s, (60, 70, 40), (41, 40, 10, 6), math.pi, 2 * math.pi, 2)


def _weedle(s):
    ocre = (240, 176, 76)
    for cx, cy, r in ((10, 48, 6), (22, 46, 9), (36, 44, 11)):
        pygame.draw.circle(s, ocre, (cx, cy), r)
        pygame.draw.circle(s, (176, 120, 40), (cx, cy), r, 2)
    pygame.draw.polygon(s, (230, 230, 235), [(2, 56), (6, 40), (12, 54)])  # ferrão
    pygame.draw.circle(s, (250, 220, 130), (46, 36), 14)
    pygame.draw.circle(s, (176, 120, 40), (46, 36), 14, 2)
    pygame.draw.polygon(s, (240, 240, 245), [(42, 24), (46, 4), (50, 24)])  # chifre
    _olho(s, 40, 36, 3)
    _olho(s, 52, 36, 3)
    pygame.draw.circle(s, (240, 130, 140), (46, 42), 3)


_DESENHOS = {"Pikachu": _pikachu, "Bulbassauro": _bulbassauro, "Rattata": _rattata,
             "Caterpie": _caterpie, "Weedle": _weedle}
_cache = {}


def sprite_pokemon(nome, tam):
    """Sprite do Pokémon em `tam` x `tam` px (desenhado em 64 px e reduzido)."""
    chave = (nome, tam)
    if chave not in _cache:
        grande = pygame.Surface((64, 64), pygame.SRCALPHA)
        _DESENHOS[nome](grande)
        _cache[chave] = pygame.transform.smoothscale(grande, (tam, tam))
    return _cache[chave]


def pokebola(raio, brilho=0.0):
    """Pokébola usada como agente. `brilho` (0..1) pulsa o anel externo."""
    tam = raio * 2 + 8
    s = pygame.Surface((tam, tam), pygame.SRCALPHA)
    c = tam // 2
    if brilho > 0:
        pygame.draw.circle(s, (255, 255, 255, int(130 * brilho)), (c, c), raio + 3 + int(2 * brilho))
    pygame.draw.circle(s, (250, 250, 250), (c, c), raio)
    topo = pygame.Surface((tam, tam), pygame.SRCALPHA)
    pygame.draw.circle(topo, (230, 50, 60), (c, c), raio)
    s.blit(topo, (0, 0), (0, 0, tam, c))
    pygame.draw.line(s, (30, 30, 36), (c - raio, c), (c + raio, c), 2)
    pygame.draw.circle(s, (30, 30, 36), (c, c), raio, 2)
    pygame.draw.circle(s, (250, 250, 250), (c, c), max(2, raio // 3))
    pygame.draw.circle(s, (30, 30, 36), (c, c), max(2, raio // 3), 1)
    return s
