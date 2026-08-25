import random
import json
import threading
import time
from openai import OpenAI, OpenAIError
import os
from dotenv import load_dotenv
from rich.console import Console
from collections import Counter

from dramagotchi import regras
from dramagotchi.constants import (
    EMOJIS, FALLBACK_DIALOG, CUTSCENE_DORMIR, CUTSCENE_BRINCAR,
)
from rich.console import Group
from rich.align import Align
from rich.text import Text
from rich.markup import escape
from dramagotchi.utils import animate, render, minigame_jokenpo, mostrar_palco, limpar_stdin, TELA, emotion_chart, get_emotion_state, generate_prompt, get_fallback_phrase, summarize_emotions, cutscene

console = Console()
load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

SAVE_PATH = "data/save.json"


def _get_client():
    """Cria o client sob demanda, ou None se nao houver chave.

    Nao pode rodar no import: o construtor levanta OpenAIError sem
    OPENAI_API_KEY, e o jogo precisa abrir sem chave.
    """
    if _get_client.cached is None:
        try:
            # base_url aponta para um servidor local (Ollama) quando definida.
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

def _ask_async(prompt, espera):
    """Resposta do modelo dentro de `espera` segundos, ou None.

    A thread fica orfa se estourar o prazo: o jogo nao pode parar esperando
    um modelo local lento.
    """
    resultado = {}

    def alvo():
        resultado["r"] = _ask(prompt)

    t = threading.Thread(target=alvo, daemon=True)
    t.start()
    t.join(espera)
    return resultado.get("r")


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
            "in_critical": False,
            "ultima_acao": None,
        }
        self.ultima_fala = None
        self.ocioso_desde = time.time()
        self._foto = None
        if data:
            self.__dict__.update(data)
            for k in self.memory:
                self.memory.setdefault(k, self.memory[k])

    def serialize(self):
        return self.__dict__

    def save(self):
        os.makedirs("data", exist_ok=True)
        with open(SAVE_PATH, "w") as f:
            json.dump(self.serialize(), f)

    @staticmethod
    def arquivar_save():
        """Move o save atual para um nome datado. Devolve o caminho, ou None."""
        if not os.path.exists(SAVE_PATH):
            return None
        carimbo = time.strftime("%Y%m%d-%H%M%S")
        destino = f"{SAVE_PATH}.{carimbo}.morto"
        os.replace(SAVE_PATH, destino)
        return destino

    @staticmethod
    def load():
        with open(SAVE_PATH) as f:
            data = json.load(f)
        # Saves antigos guardam "hunger", a escala invertida de satiety.
        if "hunger" in data and "satiety" not in data:
            data["satiety"] = 10 - data.pop("hunger")
        return Dramagotchi(data['name'], data)

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
        if self.memory["conversations"] >= 3:
            animate(self, "idle", dim=True,
                    mensagem=f"{escape(self.name)}: Chega de papo, quero fazer outra coisa! 😅")
            return

        pergunta = TELA.perguntar(self, "[bold]💬 O que você quer dizer?[/bold]")
        if not pergunta:
            return

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

    def falar_sozinho(self, espera=2.5):
        """Fala espontanea, se houver motivo. Devolve a frase ou None."""
        agora = time.time()
        foto = regras.instantaneo(self.satiety, self.happiness, self.energy)
        eventos = regras.transicoes(self._foto, foto)
        self._foto = foto

        motivo = regras.deve_falar(agora, self.ultima_fala, eventos, self.ocioso_desde)
        if motivo is None:
            return None

        self.ultima_fala = agora
        prompt = regras.montar_prompt_fala(
            self.name, self.personality, self.satiety, self.happiness,
            self.energy, motivo, self.memory.get("ultima_acao"),
        )
        fala = _ask_async(prompt, espera) or get_fallback_phrase(self.personality)
        return fala.strip()

    def _final_drama(self):
        """Estado critico maximo: leva direto ao desfecho."""
        self.memory["drama_triggered"] = True
        animate(self, "drama",
                mensagem="[bold red]😭 Você me deixou chegar no estado crítico máximo...[/bold red]")
        self.satiety = 0
        self.happiness = 0
        self.energy = 0

    def _rodar_cutscene(self, quadros):
        """Roda uma cutscene com o nome ja interpolado. Devolve o progresso."""
        return cutscene(self, [(pose, legenda.format(nome=escape(self.name)))
                               for pose, legenda in quadros])

    def feed(self):
        self.satiety, comeu = regras.aplicar_feed(self.satiety)
        if comeu:
            self.memory["feed"] += 1
            self.memory["ultima_acao"] = "alimentar"
            msg = f"{escape(self.name)} foi alimentado. 🍖"
        else:
            msg = f"{escape(self.name)} já está satisfeito! 🙂"
        animate(self, "feed", mensagem=msg)

    def play(self):
        if self.energy <= 0:
            animate(self, "idle",
                    mensagem=f"{escape(self.name)} está muito cansado para brincar. 😓", dim=True)
            return

        progresso = self._rodar_cutscene(CUTSCENE_BRINCAR)
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

        self.happiness, self.energy, ganho = regras.aplicar_play(
            self.happiness, self.energy, self.personality, resultado, progresso
        )
        self.memory["play"] += 1
        self.memory["ultima_acao"] = "brincar"
        self.memory.setdefault("wins", 0)
        if resultado == "ganhou":
            self.memory["wins"] += 1

        msg = {
            "ganhou": f"{escape(self.name)} adorou perder pra você! +{ganho} 🎉",
            "empate": f"Empate justo! +{ganho} 🤝",
            "perdeu": f"{escape(self.name)} ganhou e tirou sarro. +{ganho} 😜",
        }[resultado]
        mostrar_palco(self, palco, mensagem=msg)
        animate(self, {"ganhou": "ganhou", "empate": "play", "perdeu": "perdeu"}[resultado])

    def sleep(self):
        progresso = self._rodar_cutscene(CUTSCENE_DORMIR)
        self.energy, self.satiety = regras.aplicar_sleep(
            self.energy, self.satiety, self.personality, progresso
        )
        self.memory["sleep"] += 1
        self.memory["ultima_acao"] = "dormir"
        msg = (f"{escape(self.name)} dormiu a noite toda e acordou renovado. 🛌"
               if progresso >= 1.0
               else f"{escape(self.name)} tirou um cochilo curto. 😪")
        animate(self, "sleep", mensagem=msg)

    def idle(self):
        animate(self, "idle", dim=True)

    MINUTOS_POR_TICK = regras.MINUTOS_POR_TICK

    def decay(self):
        """Aplica o decaimento acumulado desde a ultima interacao.

        Devolve quantos ticks passaram. O relogio e que decai, nao as
        escolhas de menu.
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
        self.last_seen = time.time()
        self.ocioso_desde = time.time()

    def _checar_crise(self):
        """Escudo de duas chances antes do fim.

        Roda junto do decaimento, nao no render: um tick que zere os status
        precisa gastar a chance antes de o loop testar is_alive().
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
