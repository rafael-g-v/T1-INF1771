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
├── outputs/
│   ├── busca_local.json             # Resultado (quais pokemons são usados em cada ginásio) da busca local
│   ├── distribuicao_busca_local.png # Histograma da distribuição dos scores
│   └── evolucao_busca_local.png     # Gráfico de evolução (best/mean) da busca local
├── data/
│   └── kanto.txt            # Matriz 150 x 42 com o mapa
├── tests/
│   ├── test_astar.py
│   └── test_busca_local.py
├── requirements.txt
├── .gitignore
└── README.md

---

## Busca local

Para busca local nenhum dos algoritmos permitidos garante o ótimo num tempo finito de busca, porém o algoritmo genético na teoria atinge o ótimo ao ser deixado rodando infinitamente, já que por menor que seja as chance do cruzamento/mutação necessário acontecer, se houver tempo infinito, uma hora ele vai acontecer e atingir o ótimo global. 
Por esse e outros motivos decidimos usar um AG para a busca local, o cromossomo do AG consiste em 24 genes (um para cada ginásio) onde cada gene pode valer um valor no intervalo [0, 31], essa não foi nossa primeira abordagem, mas foi que deu os melhores resultados e atingiu o ótimo global (no vídeo explicamos melhor). 
Cada gene do cromossomo de cada indivíduo do AG representa uma das 2^5 combinações de pokemons que pode atender aquele ginásio, por exemplo, 0 representa usar só o weedle enquanto 31 representa usar todos os 5 pokemons.
Usamos uma combinação de 3 formas de cruzamento no AG (cross over com 1 ponto só, com múltiplos pontos e distribuição uniforme) de forma que cada uma era escolhida para cada filho em cada geração de forma aleatória, também usamos taxas de mutação dinamicas que aumentam e diminuem "n" vezes (parâmetro) durante as gerações e existiam 3 taxas ao todo (média, baixa e grande) que eram escolhidas aleatóriamente também, isso foi feito para escapar de ótimos locais, mas ainda ter tempo (gerações) para refinar uma solução até atingir o global.

A melhor solução achada demorou 1484.675 unidades de tempo, e ao treinar o AG 20 vezes, a média das soluções foi 1485.030 com desvio padrão de 0.678, treinamos durante 10000 gerações (não era necessário tanto, mas fizemos isso para atingirmos o ótimo global de maneira mais consistente) e com 600 indíviduos.

Gráficos da distribuição das soluções e da evolução de uma rodada que atingiu a solução ótima, assim o Json da solução ótima de fato estão na pasta outputs.