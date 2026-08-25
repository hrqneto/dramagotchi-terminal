# 🐰 dramagotchi-terminal

**Dramagotchi** is a Python-powered terminal pet with dynamic emotions and AI-powered conversations. 🐰💔

Care for, interact with, and even talk to your virtual pet directly in your terminal. But be careful: your pet decays in **real time**, so neglecting it could lead to dramatic emotional crises!

> 🎬 **Demo**
>
> _(GIF em breve)_
>
> <!-- ![Dramagotchi demo](assets/demo.gif) -->

## 🚀 Features

- **Real-Time Decay**: Satiety, happiness, and energy drop with the clock — your pet keeps living while you're away. Browsing the menu costs nothing.
- **Full-Screen UI**: A `rich` layout with the animated pet at center stage, status and mood history on the side panel, and a fixed menu at the bottom.
- **Play Is a Minigame**: Rock-paper-scissors against your pet — how much happiness you gain depends on the outcome.
- **AI Conversations**: Talk to your pet through any OpenAI-compatible endpoint.
- **Spontaneous Speech**: Your pet also talks on its own, reacting to state changes — no menu needed.
- **Works Without an API Key**: No key, no problem. The game runs normally with fallback lines.
- **Personality Types**: Randomly assigned traits (carente, brincalhão, resmungão) that affect interactions.
- **Persistent State**: Saves and loads your pet's state automatically.

## 🛠️ Tech Stack

- **Python 3.12**
- **Rich** (full-screen layout, animation, colored bars)
- **OpenAI SDK** (any compatible endpoint — OpenAI, Ollama, …)
- **Matplotlib** (emotion statistics visualization)
- **pytest** (80 tests over the pure game rules)

## 📦 Installation

### Clone the Repository
```bash
git clone https://github.com/hrqneto/dramagotchi-terminal.git
cd dramagotchi-terminal
```

### Create a venv and install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## ⚙️ Configuration

Dialogue is optional — **without any configuration the game runs fine**, falling back to canned lines. To enable AI conversations, create a `.env` file in the project root:

| Variable | Default | What it does |
|---|---|---|
| `OPENAI_API_KEY` | _(none)_ | API key. Without it, the pet uses fallback lines. |
| `OPENAI_BASE_URL` | OpenAI's API | Point this at any OpenAI-compatible endpoint. |
| `OPENAI_MODEL` | `gpt-3.5-turbo` | Model name to use. |

### Using OpenAI
```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-3.5-turbo
```

### Using Ollama (free, offline)
Run a local model and point `OPENAI_BASE_URL` at it — no API costs, no internet:

```bash
ollama serve
ollama pull llama3.2
```

```bash
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
OPENAI_MODEL=llama3.2
```

Requests time out after 8s and the pet falls back to a canned line, so a slow model never freezes the game.

## ▶️ Running the Game
Start the pet:
```bash
python main.py
```

Interact through the menu to feed, play, sleep, or chat with your pet. A terminal of at least **72x20** is required — the game warns you if the window is smaller.

## 🕹️ How It Works

- **Every 3 minutes of real time**, satiety, happiness, and energy each drop by 1. Only caring for your pet resets the clock; opening the chart or chatting is free.
- **All three bars read the same way**: full is good, and the color goes green → yellow → red as things get worse.
- **Feed** refills satiety. **Sleep** restores energy but makes your pet hungrier. **Play** costs energy and pays out happiness based on the minigame.
- Hit rock bottom and your pet enters a **critical state** — you get two warnings before the end.

## 📊 Emotion Charts
Check your pet's emotional stats anytime:
- A PNG image chart is generated at `assets/emocao_grafico.png`.
- A live sparkline of recent moods sits in the side panel.

## 🎮 Gameplay Preview

```
╭─────────────────────── Kiki ───────────────────────╮╭─────── Humor ────────╮
│                                                    ││ ██▄▅█▆█              │
│                                                    │╰──────────────────────╯
│                                                    │╭─────── Status ───────╮
│                                                    ││ Kiki                 │
│                       (\___/)                      ││ playful              │
│                      ( -.-  ) zZ                   ││                      │
│                     /|       |\                    ││ 🍔 Saciedade         │
│                    / |       | \                   ││ ███████░░░ 7/10      │
│                      |       |                     ││ 😄 Feliz             │
│                     /_|_____|_\                    ││ █████████░ 9/10      │
│                       ^^   ^^                      ││ 🛌 Energia           │
│                                                    ││ ████░░░░░░ 4/10      │
│                                                    ││                      │
│                                                    ││ 🙂 Tudo bem por      │
│                                                    ││ aqui! ✨             │
╰────────────────────────────────────────────────────╯╰──────────────────────╯
╭────────────────────────────────────────────────────────────────────────────╮
│ 1 Alimentar 🍗    2 Brincar 🎾    3 Dormir 🛌    4 Gráfico 📊   5 Sair ❌  │
│ 6 Conversar 💬                                                             │
│ Choose an option:                                                          │
╰────────────────────────────────────────────────────────────────────────────╯
```

## 🧪 Tests

The game rules (actions, decay, state transitions) live in `dramagotchi/regras.py` as pure functions, covered by pytest. The input/render layer is validated by playing.

```bash
pip install pytest
pytest tests/ -q
```

## 📜 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
