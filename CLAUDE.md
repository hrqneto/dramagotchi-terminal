# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pip install -r requirements.txt   # deps (Python 3.12 here; no venv is checked in)
python main.py                    # run the game — it is the only entry point
```

There is no test suite, linter, formatter, or build step in this repo. `requirements.txt` is a
`pip freeze` dump with `matplotlib`, `openai`, `rich` appended loosely at the end.

An `OPENAI_API_KEY` in a `.env` at the repo root enables AI dialogue; without it the game still
runs and falls back to canned phrases.

## Architecture

A single-process terminal Tamagotchi. `main.py` owns the game loop; all state and behavior live in
one `Dramagotchi` class.

- `main.py` — loads `data/save.json` if present (else prompts for a name), then loops:
  `status()` → numbered-menu action → `decay()` → `save()`, until `is_alive()` is false.
  Every menu choice therefore costs one tick of hunger/happiness/energy.
- `dramagotchi/core.py` — the `Dramagotchi` class: three 0–10 stats, a randomly assigned
  `personality` (`carente` / `brincalhão` / `resmungão`) that modifies action outcomes, and a
  `memory` dict counting actions, emotions, and crisis flags.
- `dramagotchi/utils.py` — pure-ish helpers: bar rendering, frame animation, the
  hunger/happiness/energy → emotion-label mapping, prompt construction, matplotlib chart.
- `dramagotchi/constants.py` — reaction/emoji/fallback-dialogue tables and the ASCII pet.

### Things that constrain how you change this

**Persistence is `self.__dict__` round-tripped through JSON.** `save()` dumps `serialize()`
(literally `self.__dict__`) and `load()` calls `Dramagotchi(name, data)`, whose constructor sets
defaults then does `self.__dict__.update(data)`. Any new attribute must be JSON-serializable, and
old saves simply won't carry it — the constructor's `memory` key backfill loop is a no-op
(`self.memory.setdefault(k, self.memory[k])` reads the same dict it writes), so a save file
predating a new `memory` key will `KeyError` at first access.

**Emotion state is a composite string.** `get_emotion_state()` joins active labels with `+`
(e.g. `"faminto+triste"`), so `REACTIONS.get(estado)` misses on any multi-emotion state and the
status line silently renders empty. The emoji comes from the first label only.

**The crisis path is a state machine over two `memory` flags.** `status()` uses `in_critical` as an
edge detector so `critical_hits` increments once per entry into critical, and at 2 hits fires
`_final_drama()` once (`drama_triggered`). Accepting the flower resets stats and both counters;
refusing zeroes the stats, which makes `is_alive()` false on the next check and ends the run.

**User-facing text is Portuguese; the README is English.** Menu labels, emotion keys, personality
names, and prompts are all Portuguese string literals — the emotion and personality keys double as
dict keys in `constants.py`, so translating them means changing both sides.

### AI dialogue path

`core.py` talks to OpenAI through two module-level helpers, not inline calls:

- `_get_client()` builds the `OpenAI` client **lazily and caches it on the function object**. This is
  deliberate: the v1 constructor raises `OpenAIError` when `OPENAI_API_KEY` is unset, so constructing
  at import time would make the game unlaunchable without a key. It returns `None` instead.
- `_ask(prompt)` returns the reply string, or `None` for any unavailability (no key, `OpenAIError`
  from the request). Callers branch on `None` to pick a fallback line.

So `speak()` and `talk()` never see an exception, and the game is fully playable with no API key —
it just uses `FALLBACK_DIALOG` phrases. Route any new AI call through `_ask()` rather than building
a second client. The model is the module constant `MODEL` (`gpt-3.5-turbo`).

Note `_ask()` catches `OpenAIError` — the base class for every SDK error including
`APIConnectionError` and `RateLimitError` — but not arbitrary non-SDK exceptions.

### Still-latent issues (not yet fixed)

- `speak()` is never reached from the menu — only `talk()` is wired up.
- The `memory` backfill loop in `Dramagotchi.__init__` is a no-op (`setdefault` reads the dict it
  writes), so a save file predating a new `memory` key still `KeyError`s at first access.
- Multi-emotion states (`"faminto+triste"`) miss `REACTIONS.get()` and render an empty status line.
