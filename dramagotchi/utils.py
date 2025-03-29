import time
from collections import Counter
from rich.console import Console
import matplotlib.pyplot as plt
from dramagotchi.constants import EMOJIS

console = Console()

def bar(value, total=10):
    return "█" * value + "░" * (total - value)

def animate(frames, delay=0.4, dim=False):
    for frame in frames:
        style = "[dim]" if dim else "[bold blue]"
        console.print(f"{style}{frame}[/]", highlight=False)
        time.sleep(delay)

def emotion_chart(emotions, name):
    if not emotions:
        console.print("[yellow]Sem emoções suficientes para gerar gráfico ainda.[/yellow]")
        return
    data = Counter(emotions)
    plt.figure(figsize=(6, 4))
    plt.bar(data.keys(), data.values(), color="skyblue")
    plt.title(f"Humor do {name}")
    plt.ylabel("Frequência")
    plt.xlabel("Emoções")
    plt.tight_layout()
    plt.savefig("assets/emocao_grafico.png")
    console.print("[bold green]Gráfico salvo como 'assets/emocao_grafico.png'![/bold green]")

def get_emotion_state(hunger, happiness, energy):
    estados = []
    if hunger >= 8:
        estados.append("faminto")
    if happiness <= 2:
        estados.append("triste")
    if energy <= 2:
        estados.append("cansado")
    if not estados:
        estados.append("neutro")
    return "+".join(estados), EMOJIS.get(estados[0], "🙂")

def generate_prompt(name, personality, estado, history):
    ontem = history[-2] if len(history) > 1 else "normal"
    return f"O Dramagotchi {name} é {personality}. Hoje ele está {estado}. Ontem ele estava {ontem}. Diga o que ele falaria, de forma emocional e divertida:"

def get_fallback_phrase(personality):
    from dramagotchi.constants import FALLBACK_DIALOG
    return random.choice(FALLBACK_DIALOG.get(personality, ["Hoje tá difícil 😔"]))

def summarize_emotions(name, memory):
    emocoes = Counter(memory["emotions"])
    mais_sentidas = ", ".join([f"{e}" for e, _ in emocoes.most_common(2)])
    console.print(f"\n[red bold]⚰️ Últimos momentos de {name}:[/red bold]", highlight=False)
    console.print(f"- Emoções mais sentidas: {mais_sentidas}")
    console.print(f"- Brincou {memory['play']}x, Dormiu {memory['sleep']}x, Foi alimentado {memory['feed']}x")
