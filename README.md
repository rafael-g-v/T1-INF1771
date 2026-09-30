# INF1771 - Trabalho 1 - Busca Heurística (Kanto)

Trabalho da disciplina **INF1771 - Inteligência Artificial** (2026.2).

O objetivo é implementar um agente capaz de atravessar a região de Kanto, visitar os 24 ginásios Pokémon e terminar no Plateau Indigo (destino **U**), utilizando:

1. **Busca local** para decidir quais Pokémons lutam em cada ginásio.
2. **A\*** para encontrar a rota de menor custo que visita todos os ginásios.
3. Uma **interface gráfica** simples para visualizar o agente, o caminho e os estados expandidos.

---

## Integrantes
Arthur Hammond Aragão Poggy
Jayme Augusto Avelino de Paiva
Rafael Gama Vergilio

---

## Estrutura do repositório

```text
kanto-ia/
├── main.py                 # Ponto de entrada do programa
├── src/
│   ├── astar.py            # Implementação do A*
│   ├── busca_local.py      # Implementação da busca local
│   ├── interface.py        # Interface gráfica
│   ├── mapa.py             # Leitura e representação do mapa
│   └── config.py           # Configurações de custos, ginásios e Pokémons
├── data/
│   └── kanto.txt           # Matriz 150 x 42 com o mapa
├── tests/
│   ├── test_astar.py
│   └── test_busca_local.py
├── requirements.txt
├── .gitignore
└── README.md
