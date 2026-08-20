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
    """Descarta o que foi digitado durante a animacao.

    Sem isso, Enters batidos enquanto o boneco anima ficam no buffer e viram
    uma rajada de "Opcao invalida" assim que o input abre. Silencioso quando
    nao ha terminal (pipe, teste, CI), onde tcflush nao se aplica.
    """
    try:
        import termios
        sys.stdin.fileno()
        if sys.stdin.isatty():
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except (ImportError, OSError, ValueError):
        pass


def pose_do_humor(pet):
    """Pose do estado parado, derivada do humor atual."""
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
    """Avisa se a janela e menor que o layout precisa."""
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
    """Mini-grafico do humor recente, para caber no canto da tela.

    Mapeia cada emocao registrada para uma altura: quanto pior o estado,
    mais baixa a barra.
    """
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
    """Menu + linha de prompt, ambos dentro do layout.

    O prompt precisa morar aqui: impresso por fora, ele empurrava o layout
    para cima e cortava o header.
    """
    linhas = [
        Columns([Text.from_markup(o) for o in OPCOES],
                equal=True, expand=True, padding=(0, 1)),
    ]
    if prompt is not None:
        linhas.append(Text.from_markup(prompt))
    return Panel(Group(*linhas), border_style="blue", padding=(0, 1))


def render(pet, pose=None, mensagem=None, dim=False, palco=None, prompt=None):
    """Monta a tela inteira com Layout.

    Bichinho grande no centro (o palco, onde as interacoes acontecem),
    status na coluna lateral, sparkline no canto superior direito e menu
    fixo no rodape. `palco` substitui o boneco durante um minigame.
    """
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
    # Align externo centraliza o conjunto (boneco + aviso) no palco inteiro,
    # em vez de gruda-lo no topo.
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
    """Sessao Live no buffer alternativo (screen=True).

    Uma unica Live segura a tela inteira: nada e impresso por fora, entao o
    layout cabe exatamente na janela e o header nao e cortado por rolagem.
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
        """Le uma linha lendo tecla a tecla, sem parar o Live.

        Parar a Live para usar input() faria o terminal sair e reentrar no
        buffer alternativo a cada pergunta, redesenhando o layout no buffer
        normal e empilhando telas. Aqui o buffer alternativo nunca e deixado.
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
                # os.read no descritor cru: sys.stdin.read(1) fica preso no
                # buffer interno do Python e nao retorna tecla a tecla.
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
            # Sem terminal (pipe, teste, CI): cai no input() simples.
            self.desenhar(render(pet, mensagem=mensagem, prompt=prompt))
            limpar_stdin()
            try:
                return input(" > ").strip()
            except EOFError:
                return ""
        return self._ler_linha(pet, prompt, mensagem, echo)


TELA = Tela()


def animate(pet, chave, delay=0.35, mensagem=None, dim=False, palco=None):
    """Anima o boneco no lugar e so entao mostra a mensagem.

    O efeito ja foi aplicado pelo chamador; aqui a animacao roda inteira com
    o quadro limpo e a mensagem entra no ultimo frame, para o texto nunca
    aparecer antes do movimento terminar.
    """
    poses = ANIMACOES.get(chave, ["ocioso"])
    for pose in poses:
        TELA.desenhar(render(pet, pose, None, dim, palco))
        time.sleep(delay)
    # Ultimo quadro: pose de repouso + a mensagem de resultado.
    TELA.desenhar(render(pet, None, mensagem, dim, palco))
    if mensagem:
        time.sleep(0.9)


def emotion_chart(emotions, name):
    """Gera o PNG e devolve o caminho, ou None se nao houver dados.

    Nao imprime nada: quem chama mostra o resultado dentro do layout.
    """
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

def summarize_emotions(name, memory):
    emocoes = Counter(memory["emotions"])
    mais_sentidas = ", ".join([f"{e}" for e, _ in emocoes.most_common(2)])
    console.print(f"\n[red bold]⚰️ Últimos momentos de {name}:[/red bold]", highlight=False)
    console.print(f"- Emoções mais sentidas: {mais_sentidas}")
    console.print(f"- Brincou {memory['play']}x, Dormiu {memory['sleep']}x, Foi alimentado {memory['feed']}x")


JOKENPO = {
    "pedra":   " _____\n(     )\n( PEDRA )\n(_____)",
    "papel":   " _____\n|     |\n|PAPEL|\n|_____|",
    "tesoura": " __ __\n \\ V /\n TESOURA\n  / \\ ",
}


def minigame_jokenpo(pet, escolha_jogador):
    """Pedra-papel-tesoura no palco. Devolve (resultado, painel_do_palco).

    resultado: 'ganhou' | 'perdeu' | 'empate'
    """
    escolha_pet = random.choice(list(JOKENPO))
    resultado = regras.jogar_jokenpo(escolha_jogador, escolha_pet)

    titulo = {
        "ganhou": "[bold green]Você venceu! 🎉[/bold green]",
        "perdeu": f"[bold red]{pet.name} venceu! 😜[/bold red]",
        "empate": "[bold yellow]Empate! 🤝[/bold yellow]",
    }[resultado]

    palco = Group(
        Align.center(Text.from_markup(f"[bold]Você[/bold]        [bold]{pet.name}[/bold]")),
        Align.center(Text("")),
        Align.center(Columns(
            [Text(JOKENPO[escolha_jogador]), Text("   vs   "), Text(JOKENPO[escolha_pet])],
            padding=(0, 2),
        )),
        Align.center(Text("")),
        Align.center(Text.from_markup(titulo)),
    )
    return resultado, palco


def mostrar_palco(pet, palco, segundos=1.8):
    """Desenha o quadro com um palco customizado e segura na tela."""
    TELA.desenhar(render(pet, palco=palco))
    time.sleep(segundos)
