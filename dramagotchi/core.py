# tamagotchi/core.py

import random
import json
import time
from openai import OpenAI, OpenAIError
import os
from dotenv import load_dotenv
from rich.console import Console
from collections import Counter

from dramagotchi.constants import REACTIONS, EMOJIS, FALLBACK_DIALOG, PET_ASCII
from dramagotchi.utils import bar, animate, emotion_chart, get_emotion_state, generate_prompt, get_fallback_phrase, summarize_emotions

console = Console()
load_dotenv()

MODEL = "gpt-3.5-turbo"


def _get_client():
    """Cria o client da OpenAI sob demanda.

    O construtor levanta OpenAIError quando OPENAI_API_KEY não está definida,
    entao ele nao pode rodar no import: o jogo precisa funcionar sem chave,
    caindo nas falas de fallback.
    """
    if _get_client.cached is None:
        try:
            _get_client.cached = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
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
    except OpenAIError:
        return None

class Dramagotchi:
    def __init__(self, name, data=None):
        self.name = name
        self.hunger = 5
        self.happiness = 5
        self.energy = 5
        self.personality = random.choice(["carente", "brincalhão", "resmungão"])
        self.birth = time.time()
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
        return Dramagotchi(data['name'], data)

    def status(self):
        console.clear()
        console.print(f"[bold magenta]{PET_ASCII}[/bold magenta]", highlight=False)
        console.print(f"\n[bold blue]🌾 Nome:[/bold blue] {self.name} ({self.personality})")
        console.print(f"🍔 Fome: {bar(self.hunger)} {self.hunger}/10")
        console.print(f"😄 Felicidade: {bar(self.happiness)} {self.happiness}/10")
        console.print(f"🛌 Energia: {bar(self.energy)} {self.energy}/10")
        estado, emoji = get_emotion_state(self.hunger, self.happiness, self.energy)
        console.print(f"[italic]{emoji} {REACTIONS.get(estado, '')}[/italic]")

        is_critical = self.hunger >= 9 or self.happiness <= 2 or self.energy <= 2

        if is_critical and not self.memory.get("in_critical", False):
            self.memory["critical_hits"] += 1
            self.memory["in_critical"] = True
            console.print(f"[bold red]⚠️ Seu bichinho está em estado crítico! ({self.memory['critical_hits']}/2)[/bold red]")

            if self.memory["critical_hits"] >= 2 and not self.memory.get("drama_triggered", False):
                self._final_drama()

        elif not is_critical:
            self.memory["in_critical"] = False

    def emotion(self):
        return get_emotion_state(self.hunger, self.happiness, self.energy)

    def speak(self):
        estado, emoji = self.emotion()
        self.memory["emotions"].append(estado)
        context = generate_prompt(self.name, self.personality, estado, self.memory["emotions"])
        fala = _ask(context)
        if fala is None:
            fala = get_fallback_phrase(self.personality)
        console.print(f"[bold green]{self.name} diz:[/bold green] {emoji} {fala}")

    def talk(self):
        if self.memory["conversations"] >= 3:
            console.print(f"[bold yellow]{self.name} diz:[/bold yellow] Chega de papo, quero fazer outra coisa! 😅")
            return
        pergunta = input("Você: ")
        estado, _ = self.emotion()
        prompt = f"Seu dono disse: '{pergunta}'. Você está {estado} e é um tamagotchi {self.personality}. Responda de acordo com seu humor:"
        resposta = _ask(prompt)
        if resposta is None:
            resposta = "Vamos conversar mais tarde? 🛌"
        console.print(f"[bold green]{self.name} diz:[/bold green] 💬 {resposta}")
        self.memory["conversations"] += 1

    def _final_drama(self):
        self.memory["drama_triggered"] = True
        animate([r"(\__/)", r"(>.<) 🌸", r"/    \\"], delay=0.5)
        console.print("\n[bold red]😭 Você me deixou chegar no estado crítico máximo...[/bold red]")
        console.print("🌸 [magenta]Só uma coisa pode me salvar... Pegue essa flor...[/magenta]")
        time.sleep(1.5)
        choice = input("🌼 Aceitar a flor para salvar seu bichinho? (s/n): ").strip().lower()
        if choice == 's':
            animate([r"(\__/)", r"(♥‿♥) Lele", r"/ 💞 "], delay=0.3)
            console.print("❤️ Você chamou o meu amorzinho... Só ela pra me confortar.")
            console.print("💞 Lele aparece e diz: Te amo! e tudo volta ao normal")
            self.hunger = 5
            self.happiness = 10
            self.energy = 10
            self.memory["crisis_count"] = 0
            self.memory["critical_hits"] = 0
        else:
            console.print("💔 Nem uma flor do mundo poderia me salvar... 😔")
            self.hunger = 10
            self.happiness = 0
            self.energy = 0

    def feed(self):
        animate([r"(\__/)", r"(>.<)  🍔", r"/    \\"], delay=0.3)
        if self.hunger > 0:
            self.hunger -= 1
            self.memory["feed"] += 1
            console.print(f"{self.name} foi alimentado. 🍖")
        else:
            console.print(f"{self.name} já está satisfeito! 🙂")

    def play(self):
        animate([r"(\__/)", r"(\^O\^) YAY!", r"/    \\"], delay=0.3)
        if self.energy > 0:
            self.happiness = min(10, self.happiness + (2 if self.personality == "brincalhão" else 1))
            self.energy -= 1
            self.memory["play"] += 1
            console.print(f"{self.name} brincou e ficou mais feliz! 🎉")
        else:
            console.print(f"{self.name} está muito cansado para brincar. 😓")

    def sleep(self):
        animate([r"(\__/)", r"(-.-) Zz", r"/    \\"], delay=0.3)
        bonus = 4 if self.personality == "carente" else 3
        self.energy = min(10, self.energy + bonus)
        self.memory["sleep"] += 1
        console.print(f"{self.name} tirou um cochilo. 🛌")

    def idle(self):
        animate([r"(\__/)", r"(.•.•)", r"/    \\"], delay=0.3, dim=True)

    def decay(self):
        self.hunger = min(10, self.hunger + 1)
        self.happiness = max(0, self.happiness - 1)
        self.energy = max(0, self.energy - 1)

    def is_alive(self):
        return self.hunger < 10 and self.happiness > 0 and self.energy > 0

    def show_lifetime(self):
        lived = int(time.time() - self.birth)
        console.print(f"[bold]⏳ Seu tamagotchi está vivo há {lived} segundos![/bold]")

    def show_emotion_chart(self):
        emotion_chart(self.memory["emotions"], self.name)

    def show_summary(self):
        summarize_emotions(self.name, self.memory)
