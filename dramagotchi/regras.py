"""Regras do jogo, sem I/O.

Funcoes puras: o tempo entra como parametro, nada de rich, input ou disco.
"""

MAX = 10
MINUTOS_POR_TICK = 3

# Minimo 4: abaixo disso, perder sempre torna o jogo insustentavel para as
# personalidades sem bonus de felicidade.
GANHO_MINIGAME = {"ganhou": 7, "empate": 5, "perdeu": 4}

VENCE = {"pedra": "tesoura", "papel": "pedra", "tesoura": "papel"}


def limitar(valor):
    """Prende um status na faixa 0..MAX."""
    return max(0, min(MAX, valor))


def aplicar_feed(satiety):
    """Devolve (nova_satiety, alimentou?)."""
    if satiety >= MAX:
        return satiety, False
    return limitar(satiety + 4), True


def aplicar_play(happiness, energy, personality, resultado):
    """Troca energia por felicidade. Sem energia, nada muda."""
    if energy <= 0:
        return happiness, energy, 0
    ganho = GANHO_MINIGAME[resultado]
    if personality == "brincalhão":
        ganho += 1
    return limitar(happiness + ganho), limitar(energy - 2), ganho


def aplicar_sleep(energy, satiety, personality):
    """Recupera energia ao custo de saciedade. Devolve (energia, saciedade)."""
    bonus = 6 if personality == "carente" else 5
    return limitar(energy + bonus), limitar(satiety - 2)


def aplicar_tick(satiety, happiness, energy):
    """Um tick de decaimento: tudo cai 1."""
    return limitar(satiety - 1), limitar(happiness - 1), limitar(energy - 1)


def ticks_decorridos(agora, last_seen, minutos_por_tick=MINUTOS_POR_TICK):
    """Ticks cabidos no tempo passado e o novo last_seen, guardando o resto."""
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

    Devolve (satiety, happiness, energy, hits, morreu, avisou). No fundo,
    gasta uma chance e devolve 1 ponto de folga; na terceira, morre.
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
    """Cor da barra. Cheio = bom em todos os status."""
    if valor >= 7:
        return "green"
    if valor >= 4:
        return "yellow"
    return "red"


COOLDOWN_FALA = 90          # segundos entre falas espontaneas
OCIOSO_PARA_FALAR = 5 * 60  # silencio que ja e motivo de fala


def instantaneo(satiety, happiness, energy):
    """Fotografia do estado, para comparar entre turnos."""
    return {
        "faminto": satiety <= 3,
        "critico": em_estado_critico(satiety, happiness, energy),
        "cansado": energy <= 4,
        "feliz": happiness >= 8,
    }


def transicoes(antes, depois):
    """Gatilhos entre duas fotografias, do mais urgente para o menos."""
    if antes is None:
        return []
    eventos = []
    if not antes["critico"] and depois["critico"]:
        eventos.append("entrou_critico")
    if antes["critico"] and not depois["critico"]:
        eventos.append("saiu_critico")
    if not antes["faminto"] and depois["faminto"]:
        eventos.append("ficou_faminto")
    if antes["cansado"] and not depois["cansado"]:
        eventos.append("acordou")
    if not antes["feliz"] and depois["feliz"]:
        eventos.append("ficou_feliz")
    return eventos


def deve_falar(agora, ultima_fala, eventos, ocioso_desde=None,
               cooldown=COOLDOWN_FALA, limite_ocioso=OCIOSO_PARA_FALAR):
    """Motivo da fala espontanea, ou None.

    So dispara em transicao de estado ou silencio longo, nunca a cada turno,
    e nunca antes do cooldown.
    """
    if ultima_fala is not None and agora - ultima_fala < cooldown:
        return None
    if eventos:
        return eventos[0]
    if ocioso_desde is not None and agora - ocioso_desde >= limite_ocioso:
        return "ocioso"
    return None


def montar_prompt_fala(nome, personality, satiety, happiness, energy,
                       motivo, ultima_acao=None):
    """Prompt da fala espontanea, com personalidade, stats e ultima acao."""
    motivos = {
        "entrou_critico": "voce acabou de entrar em estado critico",
        "saiu_critico": "voce acabou de sair do estado critico",
        "ficou_faminto": "a fome acabou de apertar",
        "acordou": "voce acabou de acordar descansado",
        "ficou_feliz": "voce acabou de ficar muito feliz",
        "ocioso": "faz tempo que seu dono nao interage",
    }
    acao = f" A ultima coisa que fizeram com voce foi: {ultima_acao}." if ultima_acao else ""
    return (
        f"Voce e {nome}, um bichinho virtual {personality}. "
        f"Saciedade {satiety}/10, felicidade {happiness}/10, energia {energy}/10. "
        f"Contexto: {motivos.get(motivo, motivo)}.{acao} "
        f"Diga uma unica frase curta, na primeira pessoa, sobre isso."
    )
