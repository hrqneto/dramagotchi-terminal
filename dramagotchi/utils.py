import sys
import random
import time
from collections import Counter
from rich.console import Console
import os
import matplotlib.pyplot as plt
from rich.live import Live
from rich.text import Text
from rich.console import Group
from rich.panel import Panel
from rich.columns import Columns
from rich.align import Align
from rich.layout import Layout
from rich.markup import escape
from dramagotchi import regras
from dramagotchi.constants import (
    EMOJIS, FALLBACK_DIALOG, POSES, ANIMACOES, PET_ASCII, POSE_POR_HUMOR,
)

console = Console()

def bar(value, total=10):
    """Barra colorida por faixa. Em todas as barras, cheio = bom."""
    cor = regras.faixa_de_cor(value)
    return f"[{cor}]{'█' * value}[/{cor}][dim]{'░' * (total - value)}[/dim]"


def limpar_stdin():
    """Descarta teclas digitadas durante a animacao. Sem efeito fora de um tty."""
    try:
        import termios
        sys.stdin.fileno()
        if sys.stdin.isatty():
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except (ImportError, OSError, ValueError):
        pass


def pose_do_humor(pet):
    """Pose do estado parado, derivada do humor."""
    humor = regras.humor_para_pose(pet.satiety, pet.happiness, pet.energy)
    return POSE_POR_HUMOR.get(humor)


def _borda(pet):
    """Cor da borda acompanha a gravidade do estado."""
    if regras.em_estado_critico(pet.satiety, pet.happiness, pet.energy):
        return "red"
    if regras.humor_para_pose(pet.satiety, pet.happiness, pet.energy) != "neutro":
        return "yellow"
    return "green"


OPCOES = [
    "[bold]1[/bold] Alimentar 🍗",
    "[bold]2[/bold] Brincar 🎾",
    "[bold]3[/bold] Dormir 🛌",
    "[bold]4[/bold] Gráfico 📊",
    "[bold]5[/bold] Sair ❌",
    "[bold]6[/bold] Conversar 💬",
]

LARGURA_MIN, ALTURA_MIN = 72, 20


def checar_terminal():
    """Avisa se a janela e menor que o minimo. Devolve se cabe."""
    larg, alt = console.size
    if larg < LARGURA_MIN or alt < ALTURA_MIN:
        console.print(
            f"[yellow]⚠️ Terminal {larg}x{alt} é menor que o mínimo "
            f"{LARGURA_MIN}x{ALTURA_MIN}. Aumente a janela para ver o layout "
            f"inteiro.[/yellow]"
        )
        return False
    return True


SPARK = "▁▂▃▄▅▆▇█"


def sparkline(emocoes, largura=16):
    """Mini-grafico do humor recente: quanto pior o estado, mais baixa a barra."""
    if not emocoes:
        return "[dim]sem histórico ainda[/dim]"
    peso = {"neutro": 7, "faminto": 3, "triste": 2, "cansado": 4}
    vals = []
    for e in emocoes[-largura:]:
        partes = e.split("+")
        vals.append(min(peso.get(x, 5) for x in partes))
    barras = "".join(SPARK[max(0, min(7, v))] for v in vals)
    cor = "green" if vals[-1] >= 6 else "yellow" if vals[-1] >= 3 else "red"
    return f"[{cor}]{barras}[/{cor}]"


def _painel_status(pet):
    estado, emoji = get_emotion_state(pet.satiety, pet.happiness, pet.energy)
    from dramagotchi.constants import REACTIONS
    fala = REACTIONS.get(estado) or REACTIONS.get(estado.split("+")[0], "")
    corpo = Group(
        Text.from_markup(f"[bold blue]{escape(pet.name)}[/bold blue]"),
        Text.from_markup(f"[dim]{escape(pet.personality)}[/dim]"),
        Text(""),
        Text.from_markup(f"🍔 Saciedade\n{bar(pet.satiety)} {pet.satiety}/10"),
        Text.from_markup(f"😄 Feliz\n{bar(pet.happiness)} {pet.happiness}/10"),
        Text.from_markup(f"🛌 Energia\n{bar(pet.energy)} {pet.energy}/10"),
        Text(""),
        Text.from_markup(f"[italic]{emoji} {fala}[/italic]"),
    )
    return Panel(corpo, title="[bold]Status[/bold]",
                 border_style=_borda(pet), padding=(0, 1))


def _painel_menu(prompt=None):
    """Menu + prompt. O prompt vive no layout; impresso por fora, rola a tela."""
    linhas = [
        Columns([Text.from_markup(o) for o in OPCOES],
                equal=True, expand=True, padding=(0, 1)),
    ]
    if prompt is not None:
        linhas.append(Text.from_markup(prompt))
    return Panel(Group(*linhas), border_style="blue", padding=(0, 1))


def render(pet, pose=None, mensagem=None, dim=False, palco=None, prompt=None):
    """Monta a tela inteira. `palco` substitui o boneco durante um minigame."""
    if pose is None and not dim:
        pose = pose_do_humor(pet)
    arte = POSES.get(pose, PET_ASCII) if pose else PET_ASCII
    estilo = "dim" if dim else "bold magenta"

    layout = Layout()
    layout.split_column(
        Layout(name="corpo", ratio=1),
        Layout(name="rodape", size=5),
    )
    layout["corpo"].split_row(
        Layout(name="palco", ratio=3),
        Layout(name="lateral", size=24),
    )
    layout["lateral"].split_column(
        Layout(name="humor", size=3),
        Layout(name="status", ratio=1),
    )

    centro = palco if palco is not None else Text(arte, style=estilo)
    aviso = Text.from_markup(mensagem) if mensagem else Text("")
    layout["palco"].update(
        Panel(
            Align.center(
                Group(Align.center(centro), Align.center(aviso)),
                vertical="middle",
            ),
            border_style=_borda(pet), title=f"[bold]{escape(pet.name)}[/bold]",
            padding=(0, 1),
        )
    )
    layout["humor"].update(
        Panel(Text.from_markup(sparkline(pet.memory.get("emotions", []))),
              title="[bold]Humor[/bold]", border_style="magenta", padding=(0, 1))
    )
    layout["status"].update(_painel_status(pet))
    layout["rodape"].update(_painel_menu(prompt))
    return layout


class Tela:
    """Sessao Live no buffer alternativo.

    Uma unica Live para a sessao inteira: imprimir por fora dela rola a
    tela e corta o header.
    """

    def __init__(self):
        self.live = None

    def __enter__(self):
        self.live = Live(
            console=console, screen=True, auto_refresh=False,
            transient=False, redirect_stdout=False, redirect_stderr=False,
        )
        self.live.start()
        return self

    def __exit__(self, *exc):
        if self.live is not None:
            self.live.stop()
            self.live = None
        return False

    def desenhar(self, renderable):
        if self.live is None:
            console.clear()
            console.print(renderable, highlight=False)
        else:
            self.live.update(renderable, refresh=True)

    def _ler_linha(self, pet, prompt, mensagem, echo):
        """Le uma linha tecla a tecla, sem parar o Live.

        Parar a Live para usar input() sai e reentra no buffer alternativo
        a cada pergunta, empilhando telas.
        """
        import termios, tty as _tty

        buf = ""
        fd = sys.stdin.fileno()
        antigo = termios.tcgetattr(fd)
        try:
            _tty.setcbreak(fd)
            termios.tcflush(fd, termios.TCIFLUSH)
            while True:
                self.desenhar(render(
                    pet, mensagem=mensagem,
                    prompt=f"{prompt}\n > {escape(buf) if echo else '*' * len(buf)}",
                ))
                # sys.stdin.read(1) bufferiza e nao retorna tecla a tecla.
                try:
                    b = os.read(fd, 1)
                except OSError:
                    return buf.strip()
                if not b:
                    return buf.strip()
                ch = b.decode("utf-8", "ignore")
                if not ch:
                    continue
                if ch in ("\r", "\n"):
                    return buf.strip()
                if ch in ("\x7f", "\b"):
                    buf = buf[:-1]
                elif ch == "\x03":
                    raise KeyboardInterrupt
                elif ch == "\x1b":
                    continue
                elif ch.isprintable():
                    buf += ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, antigo)

    def perguntar_livre(self, prompt):
        """Pergunta sem pet na tela — usada antes de existir um bichinho."""
        if self.live is None or not sys.stdin.isatty():
            limpar_stdin()
            try:
                return input(f"{prompt} ").strip()
            except EOFError:
                return ""

        import termios, tty as _tty

        buf = ""
        fd = sys.stdin.fileno()
        antigo = termios.tcgetattr(fd)
        try:
            _tty.setcbreak(fd)
            termios.tcflush(fd, termios.TCIFLUSH)
            while True:
                self.desenhar(Align.center(
                    Panel(Text.from_markup(f"{prompt}\n > {escape(buf)}"),
                          border_style="blue", padding=(1, 2)),
                    vertical="middle",
                ))
                try:
                    b = os.read(fd, 1)
                except OSError:
                    return buf.strip()
                if not b:
                    return buf.strip()
                ch = b.decode("utf-8", "ignore")
                if not ch:
                    continue
                if ch in ("\r", "\n"):
                    return buf.strip()
                if ch in ("\x7f", "\b"):
                    buf = buf[:-1]
                elif ch == "\x03":
                    raise KeyboardInterrupt
                elif ch == "\x1b":
                    continue
                elif ch.isprintable():
                    buf += ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, antigo)

    def perguntar(self, pet, prompt, mensagem=None, echo=True):
        """Mostra o quadro com o prompt no rodape e le a resposta."""
        if self.live is None or not sys.stdin.isatty():
            self.desenhar(render(pet, mensagem=mensagem, prompt=prompt))
            limpar_stdin()
            try:
                return input(" > ").strip()
            except EOFError:
                return ""
        return self._ler_linha(pet, prompt, mensagem, echo)


TELA = Tela()


DICA_CONTINUAR = "[dim]▸ tecla para continuar[/dim]"

DELAY_QUADRO = 0.2


def _pode_esperar_tecla():
    """So da para bloquear em tecla dentro de um tty com a Live no ar."""
    return sys.stdin.isatty() and TELA.live is not None


PULAR = ("\x1b", "q", "Q")


def esperar_tecla():
    """Bloqueia ate uma tecla e devolve ela. Fora de um tty, nao espera nada."""
    if not _pode_esperar_tecla():
        return None
    import termios, tty as _tty

    fd = sys.stdin.fileno()
    antigo = termios.tcgetattr(fd)
    try:
        _tty.setcbreak(fd)
        termios.tcflush(fd, termios.TCIFLUSH)
        while True:
            b = os.read(fd, 1)
            if not b:
                return None
            ch = b.decode("utf-8", "ignore")
            if ch == "\x03":
                raise KeyboardInterrupt
            if ch:
                return ch
    except OSError:
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, antigo)


def mostrar_texto(pet, mensagem=None, pose=None, dim=False, palco=None):
    """Porta unica de todo texto que o jogador precisa ler.

    Regra do jogo: quadro de animacao avanca sozinho, texto so sai com
    tecla. Toda mensagem, legenda, fala ou palco com texto passa por aqui —
    e por isso que nenhum caso novo escapa da pausa.
    """
    if mensagem is None and palco is None:
        return
    corpo = f"{mensagem}\n{DICA_CONTINUAR}" if mensagem else DICA_CONTINUAR
    TELA.desenhar(render(pet, pose, corpo, dim, palco))
    esperar_tecla()


def animate(pet, chave, delay=DELAY_QUADRO, mensagem=None, dim=False, palco=None):
    """Anima o boneco no lugar; a mensagem so entra no ultimo frame."""
    poses = ANIMACOES.get(chave, ["ocioso"])
    for pose in poses:
        TELA.desenhar(render(pet, pose, None, dim, palco))
        time.sleep(delay)
    if mensagem:
        mostrar_texto(pet, mensagem, dim=dim, palco=palco)
    else:
        TELA.desenhar(render(pet, None, None, dim, palco))


def cutscene(pet, quadros, delay=DELAY_QUADRO):
    """Roda uma cutscene narrada. Devolve a fracao de quadros lidos.

    Cada quadro e (pose, legenda) e a legenda e narracao: espera tecla,
    como todo texto. ESC (ou 'q') pula o resto; o retorno alimenta o ganho
    da acao, entao pular custa recompensa, nao a acao.
    """
    if not quadros:
        return 1.0

    total = len(quadros)
    if not _pode_esperar_tecla():
        for pose, legenda in quadros:
            TELA.desenhar(render(pet, pose, legenda))
            time.sleep(delay)
        return 1.0

    dica = f"{DICA_CONTINUAR}[dim]   ·   {escape('[esc]')} pular[/dim]"
    for i, (pose, legenda) in enumerate(quadros):
        TELA.desenhar(render(pet, pose, f"{legenda}\n{dica}"))
        if esperar_tecla() in PULAR:
            return i / total
    return 1.0

def emotion_chart(emotions, name):
    """Gera o PNG e devolve o caminho, ou None se nao houver dados."""
    if not emotions:
        return None
    data = Counter(emotions)
    plt.figure(figsize=(6, 4))
    plt.bar(data.keys(), data.values(), color="skyblue")
    plt.title(f"Humor do {name}")
    plt.ylabel("Frequência")
    plt.xlabel("Emoções")
    plt.tight_layout()
    os.makedirs("assets", exist_ok=True)
    plt.savefig("assets/emocao_grafico.png")
    plt.close()
    return "assets/emocao_grafico.png"

def get_emotion_state(satiety, happiness, energy):
    estado = regras.estado_emocional(satiety, happiness, energy)
    return estado, EMOJIS.get(estado.split("+")[0], "🙂")

def generate_prompt(name, personality, estado, history):
    ontem = history[-2] if len(history) > 1 else "normal"
    return f"O Dramagotchi {name} é {personality}. Hoje ele está {estado}. Ontem ele estava {ontem}. Diga o que ele falaria, de forma emocional e divertida:"

def get_fallback_phrase(personality):
    return random.choice(FALLBACK_DIALOG.get(personality, ["Hoje tá difícil 😔"]))

def _linhas_do_desfecho(name, memory):
    emocoes = Counter(memory.get("emotions", []))
    mais_sentidas = ", ".join(e for e, _ in emocoes.most_common(2)) or "nenhuma registrada"
    return [
        f"[red bold]⚰️ Últimos momentos de {escape(name)}[/red bold]",
        "",
        f"Emoções mais sentidas: {mais_sentidas}",
        (f"Brincou {memory.get('play', 0)}x, dormiu {memory.get('sleep', 0)}x, "
         f"foi alimentado {memory.get('feed', 0)}x"),
    ]


def summarize_emotions(name, memory):
    for linha in _linhas_do_desfecho(name, memory):
        console.print(linha, highlight=False)


def palco_do_desfecho(name, memory):
    """Painel do desfecho, para ocupar o palco dentro da Live."""
    return Group(*[Align.center(Text.from_markup(l))
                   for l in _linhas_do_desfecho(name, memory)])


def mostrar_desfecho(pet):
    """Mostra o desfecho no palco e segura ate uma tecla.

    Fora da Live nao ha palco: cai no print simples.
    """
    if TELA.live is None:
        summarize_emotions(pet.name, pet.memory)
        return
    mostrar_texto(pet, pose="chorando", palco=palco_do_desfecho(pet.name, pet.memory))


JOKENPO_OCULTO = " _____\n|     |\n|  ?  |\n|_____|"

JOKENPO = {
    "pedra":   " _____\n(     )\n( PEDRA )\n(_____)",
    "papel":   " _____\n|     |\n|PAPEL|\n|_____|",
    "tesoura": " __ __\n \\ V /\n TESOURA\n  / \\ ",
}


def _palco_jokenpo(pet, escolha_jogador, escolha_pet=None, titulo=None):
    """Mesa do jokenpo. Sem `escolha_pet` a mao do bicho fica escondida."""
    mao_pet = JOKENPO[escolha_pet] if escolha_pet else JOKENPO_OCULTO
    linhas = [
        Align.center(Text.from_markup(
            f"[bold]Você[/bold]        [bold]{escape(pet.name)}[/bold]")),
        Align.center(Text("")),
        Align.center(Columns(
            [Text(JOKENPO[escolha_jogador]), Text("   vs   "), Text(mao_pet)],
            padding=(0, 2),
        )),
    ]
    if titulo:
        linhas += [Align.center(Text("")),
                   Align.center(Text.from_markup(titulo))]
    return Group(*linhas)


TITULO_JOKENPO = {
    "ganhou": "[bold green]Você venceu! 🎉[/bold green]",
    "perdeu": "[bold red]{nome} venceu! 😜[/bold red]",
    "empate": "[bold yellow]Empate! 🤝[/bold yellow]",
}


def minigame_jokenpo(pet, escolha_jogador):
    """Pedra-papel-tesoura em tres tempos, cada um esperando tecla.

    Escolha, revelacao e resultado sao beats separados de proposito: numa
    tela so, o placar aparece junto com as maos e estraga a revelacao.
    """
    escolha_pet = random.choice(list(JOKENPO))
    resultado = regras.jogar_jokenpo(escolha_jogador, escolha_pet)

    # 1. a escolha do jogador entra na mesa, a do bicho ainda escondida
    mostrar_texto(pet, f"[dim]Você jogou {escolha_jogador}. E {escape(pet.name)}...?[/dim]",
                  palco=_palco_jokenpo(pet, escolha_jogador))
    # 2. a revelacao, ainda sem veredito
    mostrar_texto(pet, f"[bold]{escape(pet.name)} jogou {escolha_pet}![/bold]",
                  palco=_palco_jokenpo(pet, escolha_jogador, escolha_pet))
    # 3. o resultado
    titulo = TITULO_JOKENPO[resultado].format(nome=escape(pet.name))
    return resultado, _palco_jokenpo(pet, escolha_jogador, escolha_pet, titulo)


def mostrar_palco(pet, palco, mensagem=None, segundos=1.8):
    """Palco customizado que espera tecla. `segundos` so vale fora de um tty."""
    if _pode_esperar_tecla():
        mostrar_texto(pet, mensagem, palco=palco)
    else:
        TELA.desenhar(render(pet, mensagem=mensagem, palco=palco))
        time.sleep(segundos)
