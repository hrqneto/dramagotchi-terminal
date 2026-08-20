# tamagotchi/core.py

import random
import json
import time
from openai import OpenAI, OpenAIError
import os
from dotenv import load_dotenv
from rich.console import Console
from collections import Counter

from dramagotchi import regras
from dramagotchi.constants import EMOJIS, FALLBACK_DIALOG
from rich.console import Group
from rich.align import Align
from rich.text import Text
from rich.markup import escape
from dramagotchi.utils import animate, render, minigame_jokenpo, mostrar_palco, limpar_stdin, TELA, emotion_chart, get_emotion_state, generate_prompt, get_fallback_phrase, summarize_emotions

console = Console()
load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")


def _get_client():
    """Cria o client da OpenAI sob demanda.

    O construtor levanta OpenAIError quando OPENAI_API_KEY não está definida,
    entao ele nao pode rodar no import: o jogo precisa funcionar sem chave,
    caindo nas falas de fallback.
    """
    if _get_client.cached is None:
        try:
            # base_url permite apontar para um servidor local (Ollama etc);
            # timeout curto para o jogo nao travar esperando o modelo.
            _get_client.cached = OpenAI(
                base_url=os.getenv("OPENAI_BASE_URL") or None,
                api_key=os.getenv("OPENAI_API_KEY"),
                timeout=8.0,
            )
        except OpenAIError:
            return None
    return _get_client.cached


_get_client.cached = None


def _ask(prompt):
    """Devolve a resposta do modelo, ou None se a API não estiver disponível."""
    client = _get_client()
    if client is None:
        return None
    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return res.choices[0].message.content
    except (OpenAIError, OSError):
        return None

class Dramagotchi:
    def __init__(self, name, data=None):
        self.name = name
        self.satiety = 5
        self.happiness = 5
        self.energy = 5
        self.personality = random.choice(["carente", "brincalhão", "resmungão"])
        self.birth = time.time()
        self.last_seen = time.time()
        self.memory = {
            "feed": 0,
            "play": 0,
            "sleep": 0,
            "emotions": [],
            "conversations": 0,
            "crisis_count": 0,
            "critical_hits": 0,
            "drama_triggered": False,
            "in_critical": False
        }
        if data:
            self.__dict__.update(data)
            for k in self.memory:
                self.memory.setdefault(k, self.memory[k])

    def serialize(self):
        return self.__dict__

    def save(self):
        os.makedirs("data", exist_ok=True)
        with open("data/save.json", "w") as f:
            json.dump(self.serialize(), f)

    @staticmethod
    def load():
        with open("data/save.json") as f:
            data = json.load(f)
        # Saves antigos guardavam "hunger" (alto = ruim). Converte para
        # saciedade (alto = bom) para nao perder o bichinho na migracao.
        if "hunger" in data and "satiety" not in data:
            data["satiety"] = 10 - data.pop("hunger")
        return Dramagotchi(data['name'], data)

    def status(self, mensagem=None):
        """Desenha o quadro parado, o mesmo que animate() deixa na tela."""
        pendente = self.memory.pop("aviso_pendente", None)
        if pendente:
            mensagem = f"[bold red]{pendente}[/bold red]"
        TELA.desenhar(render(self, None, mensagem))

    def emotion(self):
        return get_emotion_state(self.satiety, self.happiness, self.energy)

    def speak(self):
        estado, emoji = self.emotion()
        self.memory["emotions"].append(estado)
        context = generate_prompt(self.name, self.personality, estado, self.memory["emotions"])
        fala = _ask(context)
        if fala is None:
            fala = get_fallback_phrase(self.personality)
        console.print(f"[bold green]{self.name} diz:[/bold green] {emoji} {fala}")

    def talk(self):
        """Conversa sem sair do Layout: pergunta e resposta no palco."""
        if self.memory["conversations"] >= 3:
            animate(self, "idle", dim=True,
                    mensagem=f"{escape(self.name)}: Chega de papo, quero fazer outra coisa! 😅")
            return

        pergunta = TELA.perguntar(self, "[bold]💬 O que você quer dizer?[/bold]")
        if not pergunta:
            return

        # Enquanto o modelo responde, o quadro segue de pe com um aviso.
        TELA.desenhar(render(self, "ocioso", mensagem="[dim]💬 pensando...[/dim]"))
        estado, _ = self.emotion()
        prompt = (
            f"Seu dono disse: '{pergunta}'. Você está {estado} e é um tamagotchi "
            f"{self.personality}. Responda em uma ou duas frases, de acordo com seu humor:"
        )
        resposta = _ask(prompt) or "Vamos conversar mais tarde? 🛌"

        self.memory["conversations"] += 1
        palco = Group(
            Align.center(Text.from_markup(f"[dim]você:[/dim] {escape(pergunta)}")),
            Align.center(Text("")),
            Align.center(Text.from_markup(
                f"[bold green]{escape(self.name)}:[/bold green] 💬 {escape(resposta.strip())}"
            )),
        )
        mostrar_palco(self, palco, segundos=3.0)

    def _final_drama(self):
        """Estado critico maximo: leva direto ao desfecho, sem resgate."""
        self.memory["drama_triggered"] = True
        animate(self, "drama", delay=0.3,
                mensagem="[bold red]😭 Você me deixou chegar no estado crítico máximo...[/bold red]")
        time.sleep(1.0)
        self.satiety = 0
        self.happiness = 0
        self.energy = 0

    def feed(self):
        self.satiety, comeu = regras.aplicar_feed(self.satiety)
        if comeu:
            self.memory["feed"] += 1
            msg = f"{escape(self.name)} foi alimentado. 🍖"
        else:
            msg = f"{escape(self.name)} já está satisfeito! 🙂"
        animate(self, "feed", mensagem=msg)

    def play(self):
        """Brincar e um minigame: o ganho de felicidade depende do resultado."""
        if self.energy <= 0:
            animate(self, "idle",
                    mensagem=f"{escape(self.name)} está muito cansado para brincar. 😓", dim=True)
            return

        animate(self, "correr", delay=0.25)
        escolha = TELA.perguntar(
            self,
            "[bold]🎾 Pedra, papel ou tesoura?[/bold]  "
            + escape("[p]edra  [a]papel  [t]esoura"),
        ).lower()[:1]
        escolha = {"p": "pedra", "a": "papel", "t": "tesoura"}.get(escolha)
        if escolha is None:
            animate(self, "idle", mensagem="Escolha inválida — a brincadeira passou. 🤷", dim=True)
            return

        resultado, palco = minigame_jokenpo(self, escolha)
        mostrar_palco(self, palco)

        self.happiness, self.energy, ganho = regras.aplicar_play(
            self.happiness, self.energy, self.personality, resultado
        )
        self.memory["play"] += 1
        self.memory.setdefault("wins", 0)
        if resultado == "ganhou":
            self.memory["wins"] += 1

        msg = {
            "ganhou": f"{escape(self.name)} adorou perder pra você! +{ganho} 🎉",
            "empate": f"Empate justo! +{ganho} 🤝",
            "perdeu": f"{escape(self.name)} ganhou e tirou sarro. +{ganho} 😜",
        }[resultado]
        animate(self, {"ganhou": "ganhou", "empate": "play", "perdeu": "perdeu"}[resultado],
                mensagem=msg)

    def sleep(self):
        # Dormir recupera energia, mas da fome: nao da pra so dormir.
        self.energy, self.satiety = regras.aplicar_sleep(
            self.energy, self.satiety, self.personality
        )
        self.memory["sleep"] += 1
        animate(self, "sleep", mensagem=f"{escape(self.name)} tirou um cochilo. 🛌")

    def idle(self):
        animate(self, "idle", dim=True)

    # Um "tick" de decaimento a cada MINUTOS_POR_TICK minutos de tempo real.
    MINUTOS_POR_TICK = regras.MINUTOS_POR_TICK

    def decay(self):
        """Aplica o decaimento acumulado desde a ultima interacao.

        O tempo e que passa, nao as escolhas de menu: abrir o grafico ou
        conversar nao custa mais nada. Devolve quantos ticks passaram.
        """
        agora = time.time()
        ticks, novo = regras.ticks_decorridos(
            agora, getattr(self, "last_seen", agora), self.MINUTOS_POR_TICK
        )
        if ticks <= 0:
            return 0
        self.last_seen = novo

        for _ in range(min(ticks, 100)):   # teto evita loop enorme apos dias
            self.satiety, self.happiness, self.energy = regras.aplicar_tick(
                self.satiety, self.happiness, self.energy
            )
            estado, _ = get_emotion_state(self.satiety, self.happiness, self.energy)
            self.memory["emotions"].append(estado)
            self._checar_crise()
        return ticks

    def tocar(self):
        """Marca interacao sem aplicar decaimento (usado apos uma acao)."""
        self.last_seen = time.time()

    def _checar_crise(self):
        """Escudo de duas chances antes do fim.

        Antes isso vivia no status(), entao um decaimento que zerasse os
        status encerrava o loop sem nunca mostrar o aviso. Agora roda junto
        do decaimento: ao bater no fundo, gasta uma chance e devolve um
        minimo de folga; so na terceira vez o bichinho se vai.
        """
        if not regras.no_fundo(self.satiety, self.happiness, self.energy):
            if not regras.em_estado_critico(self.satiety, self.happiness, self.energy):
                self.memory["in_critical"] = False
            return

        if self.memory.get("drama_triggered"):
            return

        (self.satiety, self.happiness, self.energy,
         self.memory["critical_hits"], morreu, avisou) = regras.resolver_crise(
            self.satiety, self.happiness, self.energy, self.memory["critical_hits"]
        )
        self.memory["in_critical"] = True
        if morreu:
            self.memory["drama_triggered"] = True
            return
        if avisou:
            self.memory["crisis_count"] = self.memory.get("crisis_count", 0) + 1
            self.memory["aviso_pendente"] = (
                f"⚠️ Estado crítico! ({self.memory['critical_hits']}/2) "
                f"{escape(self.name)} está por um fio..."
            )

    def is_alive(self):
        # O escudo de crises segura as duas primeiras quedas ao fundo; so
        # depois de drama_triggered o bichinho realmente morre.
        return regras.esta_vivo(self.satiety, self.happiness, self.energy,
                                self.memory.get("drama_triggered", False))

    def show_lifetime(self):
        lived = int(time.time() - self.birth)
        console.print(f"[bold]⏳ Seu tamagotchi está vivo há {lived} segundos![/bold]")

    def show_emotion_chart(self):
        caminho = emotion_chart(self.memory["emotions"], self.name)
        msg = (f"[green]📊 Gráfico salvo em {caminho}[/green]" if caminho
               else "[yellow]Sem emoções suficientes para o gráfico ainda.[/yellow]")
        TELA.perguntar(self, f"{msg}\n[dim]  [enter] para voltar[/dim]")

    def show_summary(self):
        summarize_emotions(self.name, self.memory)
