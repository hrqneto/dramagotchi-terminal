"""Regras do jogo, sem nenhum I/O.

Tudo aqui e funcao pura: recebe valores, devolve valores. Nada de rich,
input, arquivo ou relogio — o tempo entra como parametro. E esta camada
que os testes automatizados cobrem; input e render se validam jogando.
"""

MAX = 10
MINUTOS_POR_TICK = 3

# Ganho de felicidade por resultado do minigame. Calibrado para o jogo
# seguir sustentavel mesmo perdendo sempre, com vantagem clara para quem ganha.
GANHO_MINIGAME = {"ganhou": 7, "empate": 5, "perdeu": 4}

VENCE = {"pedra": "tesoura", "papel": "pedra", "tesoura": "papel"}


def limitar(valor):
    """Prende um status na faixa 0..MAX."""
    return max(0, min(MAX, valor))


def aplicar_feed(satiety):
    """Alimentar enche a saciedade. Devolve (nova_satiety, alimentou?)."""
    if satiety >= MAX:
        return satiety, False
    return limitar(satiety + 4), True


def aplicar_play(happiness, energy, personality, resultado):
    """Brincar troca energia por felicidade, conforme o resultado do jogo.

    Devolve (nova_happiness, nova_energy, ganho). Sem energia, nada muda.
    """
    if energy <= 0:
        return happiness, energy, 0
    ganho = GANHO_MINIGAME[resultado]
    if personality == "brincalhão":
        ganho += 1
    return limitar(happiness + ganho), limitar(energy - 2), ganho


def aplicar_sleep(energy, satiety, personality):
    """Dormir recupera energia e da fome. Devolve (energia, saciedade)."""
    bonus = 6 if personality == "carente" else 5
    return limitar(energy + bonus), limitar(satiety - 2)


def aplicar_tick(satiety, happiness, energy):
    """Um tick de decaimento: tudo cai 1."""
    return limitar(satiety - 1), limitar(happiness - 1), limitar(energy - 1)


def ticks_decorridos(agora, last_seen, minutos_por_tick=MINUTOS_POR_TICK):
    """Quantos ticks cabem no tempo passado, e o novo last_seen.

    O resto do periodo fica para a proxima chamada, para nao perder fracoes
    de minuto entre interacoes.
    """
    decorrido = max(0.0, agora - last_seen)
    periodo = minutos_por_tick * 60
    ticks = int(decorrido // periodo)
    if ticks <= 0:
        return 0, last_seen
    return ticks, agora - (decorrido % periodo)


def esta_vivo(satiety, happiness, energy, drama_triggered=False):
    """Vivo enquanto nenhum status zerou e o escudo nao acabou."""
    if drama_triggered:
        return False
    return satiety > 0 and happiness > 0 and energy > 0


def no_fundo(satiety, happiness, energy):
    """Algum status bateu no fundo?"""
    return satiety <= 0 or happiness <= 0 or energy <= 0


def em_estado_critico(satiety, happiness, energy):
    """Perto do fundo, mas ainda nao nele."""
    return satiety <= 1 or happiness <= 2 or energy <= 2


def resolver_crise(satiety, happiness, energy, critical_hits):
    """Escudo de duas chances antes do fim.

    Devolve (satiety, happiness, energy, hits, morreu, avisou). Ao bater no
    fundo gasta uma chance e devolve 1 ponto de folga; na terceira, morre.
    """
    if not no_fundo(satiety, happiness, energy):
        return satiety, happiness, energy, critical_hits, False, False

    hits = critical_hits + 1
    if hits >= 3:
        return satiety, happiness, energy, hits, True, False

    return (max(satiety, 1), max(happiness, 1), max(energy, 1), hits, False, True)


def jogar_jokenpo(escolha_jogador, escolha_pet):
    """'ganhou' (jogador venceu), 'perdeu' ou 'empate'."""
    if escolha_jogador == escolha_pet:
        return "empate"
    return "ganhou" if VENCE[escolha_jogador] == escolha_pet else "perdeu"


def estado_emocional(satiety, happiness, energy):
    """Rotulo composto do humor, ex 'faminto+cansado'."""
    estados = []
    if satiety <= 2:
        estados.append("faminto")
    if happiness <= 2:
        estados.append("triste")
    if energy <= 2:
        estados.append("cansado")
    return "+".join(estados) if estados else "neutro"


def humor_para_pose(satiety, happiness, energy):
    """Qual pose o boneco assume parado, conforme o humor."""
    if em_estado_critico(satiety, happiness, energy):
        return "critico"
    if satiety <= 3:
        return "faminto"
    if energy <= 4:
        return "cansado"
    if happiness <= 4:
        return "triste"
    if happiness >= 8:
        return "feliz"
    return "neutro"


def faixa_de_cor(valor):
    """Cor da barra: cheio = bom, em todos os status."""
    if valor >= 7:
        return "green"
    if valor >= 4:
        return "yellow"
    return "red"
