import random
import numpy as np
import matplotlib.pyplot as plt
import json


def gera_combinacoes(n):
    if n == 0:
        return [[]]  

    menores = gera_combinacoes(n - 1)
    return [c + [0] for c in menores] + [c + [1] for c in menores]

COMBINACOES = [tuple(c) for c in gera_combinacoes(5)]


def calcula_score(ind, pokemon_str, ginasio_diff):
    vida = [6,6,6,6,6]
    score = 0
    for i in range(24):
        pokemons = COMBINACOES[ind[i]]

        if sum(pokemons) == 0:
            score += 90000

        div = 0
        for j in range(5):
            if pokemons[j] == 1:
                if vida[j] <= 0:
                    score += 5000
                else:
                    vida[j] -= 1
                div += pokemon_str[j]
        if div > 0:
            score += ginasio_diff[i]/div
        else:
            score += ginasio_diff[i]*20

    if all(v <= 0 for v in vida):
        score += 4600

    return score


def cruza(pop, scores, ind, y, gen, Gen, ciclos=4):
    ranking = np.argsort(scores)
    weight = np.arange(ind,0,-1)
    probs = np.zeros(ind)
    probs[ranking]=weight/weight.sum()

    onda = (1 - np.cos(2*np.pi*ciclos*gen/Gen)) / 2

    p_baixa = 0.4 - 0.2*onda
    p_media = 0.1
    valor_alta = 2*(0.005 + 0.145*onda)

    mutation_str = random.random()
    limite1 = p_baixa
    limite2 = p_baixa + p_media
    mutation_chance = 0.01 if mutation_str <= limite1 else (0.002 if mutation_str <= limite2 else valor_alta)

    new_pop = np.zeros((ind-30, y), dtype=int)
    for i in range(ind-30):
        indexes = np.random.choice(len(pop), size=2, p=probs)
        parent1, parent2 = pop[indexes[0]], pop[indexes[1]]
        son = np.zeros(y, dtype=int)

        method_chance = random.random()

        if method_chance <= 1/3:
            c = random.randint(0, y)
            son[0:c] = parent1[0:c]
            son[c:] = parent2[c:]

            for g in range(y):
                if random.random() <= mutation_chance:
                    son[g] = random.randint(0, 31)

        elif method_chance <= 2/3:
            parents = np.array([parent1, parent2])
            parent = random.choice([0, 1])
            prob_troca = 6 / y 

            for g in range(y):
                son[g] = parents[parent, g]
                if random.random() < prob_troca:
                    parent = 1 - parent

            for g in range(y):
                if random.random() <= mutation_chance:
                    son[g] = random.randint(0, 31)

        else:
            parents = np.array([parent1, parent2])
            for g in range(y):
                parent = random.choice([0,1])
                son[g] = parents[parent, g]
                if random.random() <= mutation_chance:
                    son[g] = random.randint(0, 31)

        new_pop[i] = son

    return new_pop



def treina(pokemons_str, ginasios_diff, ind=100, Gen=500):
    y = len(ginasios_diff)
    pop = np.array([[random.randint(0, 31) for _ in range(y)] for _ in range(ind)])

    plot_mean = []
    plot_best = []
    gen = Gen
    for gen in range(gen):
        scores = np.array([calcula_score(indi, pokemons_str, ginasios_diff) for indi in pop])
        if gen > 0:
            pop = np.vstack([pop, elite])
            scores = np.concatenate([scores, elite_scores])

        mean_score = sum(scores)/ind
        best_score = min(scores)
        best = pop[np.argsort(scores)[0]]
        plot_mean.append(mean_score)
        plot_best.append(best_score)
        print(f"Gen: {gen+1} || Mean: {mean_score} || Best: {best_score}")
        top_five = np.argsort(scores)[:30]
        elite = pop[top_five]
        elite_scores = scores[top_five]
        new_pop = cruza(pop, scores, ind, y, gen, Gen)
        pop = new_pop

    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(10, 8))

    ax1.plot(range(Gen), plot_best, label="Best", color="tab:blue")
    ax1.set_ylabel("Score (Best)")
    ax1.set_title("Evolução do AG")
    ax1.legend()

    ax2.plot(range(Gen), plot_mean, label="Mean", color="tab:orange")
    ax2.set_xlabel("Geração")
    ax2.set_ylabel("Score (Mean)")
    ax2.legend()

    plt.tight_layout()
    plt.show()

    return best


def mostra_vida(result, pokemons):
    vida = [6, 6, 6, 6, 6]
    for i in range(24):
        pokemons_usados = COMBINACOES[result[i]]
        for j in range(5):
            if pokemons_usados[j] == 1:
                vida[j] -= 1

        print(f"Ginásio {i+1}:")
        for nome, v in zip(pokemons, vida):
            print(f"  {nome}: {v}")
        print()


def escreve_json(result, pokemons, ginasios, caminho="resultado.json"):
    dados = {}
    for i in range(len(ginasios)):
        pokemons_usados = COMBINACOES[int(result[i])]
        nomes = [pokemons[j] for j in range(5) if pokemons_usados[j] == 1]
        dados[str(ginasios[i])] = nomes

    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

    return dados


def main():
    pokemons = ["Pikachu", "Bulbassauro", "Rattata", "Caterpie", "Weedle"]
    pokemons_str = [1.5, 1.4, 1.3, 1.2, 1.1]
    ginasios = [2,3,4,5,6,7,8,9,"B","C","D","E","G","H","I","J","K","L","N","O","P","Q","S","T"]
    ginasios_diff = [35,40,45,50,55,60,65,70,75,80,85,90,95,100,110,120,130,140,150,155,160,165,170,180]

    result = treina(pokemons_str, ginasios_diff, ind=600, Gen=10000)
    mostra_vida(result, pokemons)

    escreve_json(result, pokemons, ginasios)

main()