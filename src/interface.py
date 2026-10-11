import json
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace

from . import config
from .resumo import calcular_resumo

#tipos de evento que o A* registra: (tipo, linha, coluna)
GERAR = "g"
EXPANDIR = "e"
NOVA = "n"

PASTA_OUTPUTS = Path(__file__).resolve().parent.parent / "outputs"
ARQUIVO_POKEMONS = PASTA_OUTPUTS / "busca_local.json"

CELULA = 8
QUADRO_MS = 20
EVENTOS_POR_QUADRO = 64
PASSOS_POR_QUADRO = 1

COR_TERRENO = {"M": "#8b5a2b", "A": "#4a90d9", "F": "#3a9a4a", "R": "#9a9a9a", ".": "#ffffff"}
COR_EXPANDIDO = "#8e44ad"
COR_FRONTEIRA = "#f39c12"
COR_ROTA = "#d00000"
COR_AGENTE = "#0033cc"

def _eventos(rota):
    #cada estado expandido pelo A* da rota apaga a rota anterior e desenha a rota parcial que ele estava olhando
    eventos = []
    for estado in rota.historico:
        eventos.append((NOVA, 0, 0))
        ordem = estado["rota"]
        for a, b in zip(ordem, ordem[1:]):
            eventos += [(GERAR, r, c) for r, c in rota.caminhos[f"{a}-{b}"]]
    return eventos

def _fmt(valor, casas):
    return f"{valor:.{casas}f}".replace(".", ",")

def _misturar(a, b, t):
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x * (1 - t) + y * t) for x, y in zip(ca, cb))

class Interface:
    def __init__(self, mapa, rota, pokemons_por_ginasio):
        self.mapa = mapa
        self.rota = rota
        self.eventos = _eventos(rota)
        self.caminho = rota.caminho
        self.resumo = calcular_resumo(mapa, rota.caminho, rota.custo_acumulado, pokemons_por_ginasio)
        self.cores = {t: (c, _misturar(c, COR_EXPANDIDO, 0.55), _misturar(c, COR_FRONTEIRA, 0.9)) for t, c in COR_TERRENO.items()}
        self.raiz = tk.Tk()
        self.raiz.title("Kanto")
        self.raiz.resizable(False, False)
        self._montar_tela()
        self.fase = "busca" if self.eventos else "exec"
        self.idx_evento = 0
        self.passo = 0.0
        self.fronteira = set()
        self.expandidos = set()
        self.pendentes = {}
        self.estado_busca = 0
        self.atualizar()

    def _montar_tela(self):
        m = self.mapa
        self.canvas = tk.Canvas(self.raiz, width=m.largura * CELULA, height=m.altura * CELULA, highlightthickness=0)
        self.canvas.pack(padx=10, pady=10)
        self.celulas = {}
        self.tipo_celula = {}
        for r in range(m.altura):
            for c in range(m.largura):
                t = m.simbolo((r, c))
                t = t if t in COR_TERRENO else "."
                self.tipo_celula[(r, c)] = t
                x = c * CELULA
                y = r * CELULA
                self.celulas[(r, c)] = self.canvas.create_rectangle(x, y, x + CELULA, y + CELULA, fill=COR_TERRENO[t], outline="")

        self.pontos = [(c * CELULA + CELULA // 2, r * CELULA + CELULA // 2) for r, c in self.caminho]
        self.linha = self.canvas.create_line(0, 0, 0, 0, fill=COR_ROTA, width=2, state="hidden")
        fixos = list(m.ginasios.items()) + [(config.SIMBOLO_ORIGEM, m.origem), (config.SIMBOLO_DESTINO, m.destino)]
        for rotulo, pos in fixos:
            x, y = pos[1] * CELULA + CELULA // 2, pos[0] * CELULA + CELULA // 2
            self.canvas.create_oval(x - 7, y - 7, x + 7, y + 7, fill="white", outline="black")
            self.canvas.create_text(x, y, text=rotulo, font=("TkDefaultFont", 8, "bold"))
        self.agente = self.canvas.create_oval(0, 0, 0, 0, fill=COR_AGENTE, outline="white", state="hidden")

        legenda = tk.Frame(self.raiz)
        legenda.pack(anchor="w", padx=10)
        for cor, nome in ((COR_FRONTEIRA, "Rota olhada pelo A*"), (COR_ROTA, "Caminho final"), (COR_AGENTE, "Agente")):
            tk.Frame(legenda, width=12, height=12, bg=cor).pack(side="left")
            tk.Label(legenda, text=nome).pack(side="left", padx=(3, 12))

        self.texto = tk.Text(self.raiz, width=120, height=20, font="TkFixedFont", relief="flat", bg=self.raiz.cget("bg"), state="disabled")
        self.texto.pack(padx=10, pady=10)

    #andamento
    def _aplicar_evento(self, ev):
        tipo, r, c = ev
        cel = (r, c)
        if tipo == NOVA:
            self.estado_busca += 1
            for f in self.fronteira:
                self.pendentes[f] = 0
            self.fronteira.clear()
        elif tipo == GERAR:
            if cel not in self.expandidos:
                self.pendentes[cel] = 2
                self.fronteira.add(cel)
        elif tipo == EXPANDIR:
            self.expandidos.add(cel)
            self.fronteira.discard(cel)
            self.pendentes[cel] = 1

    def _avancar_busca(self, n):
        eventos = self.eventos
        fim = min(self.idx_evento + n, len(eventos))
        for ev in eventos[self.idx_evento:fim]:
            self._aplicar_evento(ev)
        self.idx_evento = fim
        if fim >= len(eventos):
            self.fase = "exec"

    def _avancar_exec(self, n):
        self.passo = min(self.passo + n, len(self.caminho) - 1)
        if self.passo >= len(self.caminho) - 1:
            self.fase = "fim"

    def avancar(self):
        if self.fase == "busca":
            self._avancar_busca(EVENTOS_POR_QUADRO)
        elif self.fase == "exec":
            self._avancar_exec(PASSOS_POR_QUADRO)
        self.atualizar()

    #desenho
    def atualizar(self):
        for cel, estado in self.pendentes.items():
            self.canvas.itemconfigure(self.celulas[cel], fill=self.cores[self.tipo_celula[cel]][estado])
        self.pendentes.clear()

        i = min(int(self.passo), len(self.caminho) - 1)
        andando = self.fase != "busca"
        if andando:
            x, y = self.pontos[i]
            self.canvas.coords(self.agente, x - 5, y - 5, x + 5, y + 5)
            self.canvas.itemconfigure(self.agente, state="normal")
            self.canvas.tag_raise(self.agente)
            
            if i > 0:
                self.canvas.coords(self.linha, *[v for p in self.pontos[: i + 1] for v in p])
                self.canvas.itemconfigure(self.linha, state="normal")
        
        rota = self.resumo.rota_acum[i] if andando else 0
        bat = self.resumo.bat_acum[i] if andando else 0.0
        energia = self.resumo.energias[self.resumo.batalhas_ate[i]] if andando else self.resumo.energias[0]
        if self.fase == "fim":
            self._escrever(self._texto_final())
        elif self.fase == "busca":
            self._escrever(self._texto_busca())
        else:
            self._escrever(self._texto_custos(rota, bat, energia))

    def _texto_busca(self):
        n = min(self.estado_busca, len(self.rota.historico))
        texto = f"Busca A* da rota: estado expandido {n} de {len(self.rota.historico)}\n"
        if n > 0:
            estado = self.rota.historico[n - 1]
            pontos = [self.rota.pontos[k] for k in estado["rota"]]
            texto += (f"g(n) = {estado['g']}   h(n) = {_fmt(estado['f'] - estado['g'], 1)}   f(n) = {_fmt(estado['f'], 1)}\n"
                      f"Rota olhada: {' -> '.join(pontos)}\n")
        return texto

    def _texto_custos(self, rota, bat, energia):
        texto = (f"Custo da rota:      {rota} min\n"
                 f"Custo das batalhas: {_fmt(bat, 1)} min\n"
                 f"Custo total:        {_fmt(rota + bat, 1)} min\n\n")
        texto += "Energia dos Pokémons:\n"
        for nome, e in energia.items():
            texto += f"  {nome:<12} {'█' * e:<6} {e}\n"
        return texto

    def _texto_final(self):
        r = self.resumo
        linhas = ["Ordem de visita e Pokémons usados em cada batalha (tempo em min):"]
        for lin in range(12):
            partes = []
            for k in (lin, lin + 12):
                g = r.ordem[k]
                pokes = ", ".join(r.pokemons_usados[g])
                partes.append(f"{k + 1:>2}. {g}  {pokes:<22}{_fmt(r.tempo_batalha[g], 2):>7}")
            linhas.append("    ".join(partes))
        linhas.append("")
        energia = [f"{nome}: {e}" for nome, e in r.energia_final.items()]
        custos = [f"Custo da rota:      {r.custo_rota} min",
                  f"Custo das batalhas: {_fmt(r.custo_batalhas, 2)} min",
                  f"Custo total:        {_fmt(r.custo_total, 2)} min",
                  f"Estados expandidos (rota): {self.rota.expandidos_rota}"]
        linhas.append(f"{'Energia final':<40}")
        for k in range(len(energia)):
            linhas.append(f"{energia[k]:<40}{custos[k] if k < len(custos) else ''}")
        return "\n".join(linhas)

    def _escrever(self, conteudo):
        self.texto.configure(state="normal")
        self.texto.delete("1.0", "end")
        self.texto.insert("1.0", conteudo)
        self.texto.configure(state="disabled")

    def _quadro(self):
        if self.fase != "fim":
            self.avancar()
        self.raiz.after(QUADRO_MS, self._quadro)

    def executar(self):
        self.raiz.after(QUADRO_MS, self._quadro)
        self.raiz.mainloop()

def carregar_rota(mapa):
    #lê os jsons gerados pelo A* e monta o caminho célula por célula com o custo acumulado (o init já custa 1)
    final = json.loads((PASTA_OUTPUTS / "rota_final.json").read_text(encoding="utf-8"))
    historico = json.loads((PASTA_OUTPUTS / "historico_astar_rota.json").read_text(encoding="utf-8"))
    caminhos = json.loads((PASTA_OUTPUTS / "caminhos_grid.json").read_text(encoding="utf-8"))
    caminho = [tuple(c) for c in final["trechos"][0]]
    for trecho in final["trechos"][1:]:
        caminho += [tuple(c) for c in trecho[1:]]
    custo_acumulado = [1]
    for pos in caminho[1:]:
        custo_acumulado.append(custo_acumulado[-1] + config.CUSTO_TERRENO.get(mapa.simbolo(pos), 0))
    return SimpleNamespace(caminho=caminho, custo_acumulado=custo_acumulado, historico=historico,
                           caminhos=caminhos, pontos=final["pontos"], expandidos_rota=len(historico))

def main():
    from .mapa import Mapa

    mapa = Mapa.carregar()
    rota = carregar_rota(mapa)
    pokemons = json.loads(ARQUIVO_POKEMONS.read_text(encoding="utf-8"))
    Interface(mapa, rota, pokemons).executar()

if __name__ == "__main__":
    main()
