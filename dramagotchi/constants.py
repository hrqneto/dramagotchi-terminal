REACTIONS = {
    "faminto": "Tô morrendo de fome... 😩",
    "triste": "😢 Me sinto abandonado...",
    "cansado": "Só queria dormir um pouquinho 💤",
    "neutro": "Tudo bem por aqui! ✨"
}

EMOJIS = {
    "faminto": "😩",
    "triste": "😢",
    "cansado": "🪱",
    "neutro": "🙂"
}

FALLBACK_DIALOG = {
    "carente": ["Só queria um carinho...", "Não me abandona 😭", "Você ainda gosta de mim?"],
    "brincalhão": ["Vamos brincar até cansar!", "Ei! Me dá atenção! 🙃", "Tô entediado!"],
    "resmungão": ["De novo essa comida?!", "Ninguém me entende...", "Você tá me deixando de lado 😠"]
}

PET_ASCII = '     (\\___/)\n    ( o^_^o )\n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^'

# Toda pose precisa ter a mesma altura de PET_ASCII: o render troca a pose
# no lugar, e alturas diferentes deslocam o resto da tela.
POSES = {
    'faminto': '     (\\___/)\n    ( o.o )  ~🍽\n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^',
    'chorando': '     (\\___/)\n    ( T_T )  \n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^',
    'comendo': '     (\\___/)\n    ( >o_o< ) 🍔\n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^',
    'correndo': '     (\\___/)\n    ( >o_o )>  \n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^',
    'derrota': '     (\\___/)\n    ( ._.  )  \n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^',
    'dormindo': '     (\\___/)\n    ( -.-  ) zZ\n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^',
    'feliz': '     (\\___/)\n    ( \\^O^/ ) !\n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^',
    'ocioso': '     (\\___/)\n    ( ·  .  · )\n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^',
    'vitoria': '     (\\___/)\n    ( ^o^ )/ !!\n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^',
    'bocejando': '     (\\___/)\n    ( o○o  ) ~\n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^',
    'sonhando': '     (\\___/)  💭\n    ( -.-  ) zZ\n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^',
    'acordando': '     (\\___/)\n    ( o.O  ) !\n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^',
    'alongando': '     (\\___/)\n   \\( ^-^  )/\n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^',
    'pulando': '     (\\___/)  *\n    ( >o<  ) /\n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^',
    'provocando': '     (\\___/)\n    ( ^_~  ) ~\n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^',
}

ANIMACOES = {
    "feed": ["ocioso", "comendo", "ocioso", "comendo", "feliz", "comendo",
             "ocioso", "comendo", "feliz", "feliz"],
    "play": ["ocioso", "correndo", "feliz", "correndo", "ocioso", "correndo",
             "feliz", "correndo", "feliz", "feliz"],
    "sleep": ["ocioso", "dormindo", "ocioso", "dormindo", "dormindo", "ocioso",
              "dormindo", "dormindo", "ocioso", "dormindo"],
    "drama": ["chorando", "ocioso", "chorando", "ocioso", "chorando", "ocioso",
              "chorando", "ocioso", "chorando"],
    "idle": ["ocioso", "feliz", "ocioso", "feliz", "ocioso", "feliz", "ocioso"],
}

POSE_POR_HUMOR = {
    "critico": "chorando",
    "faminto": "faminto",
    "cansado": "dormindo",
    "triste": "chorando",
    "feliz": "feliz",
    "neutro": None,   # None = PET_ASCII
}

ANIMACOES["correr"] = ["ocioso", "correndo", "ocioso", "correndo", "ocioso",
                       "correndo", "ocioso", "correndo"]
ANIMACOES["ganhou"] = ["vitoria", "feliz", "vitoria", "feliz", "vitoria",
                       "feliz", "vitoria", "feliz"]
ANIMACOES["perdeu"] = ["derrota", "ocioso", "derrota", "ocioso", "derrota",
                       "ocioso", "derrota"]

# Roteiros das cutscenes: (pose, legenda) por quadro. A legenda ja vem com
# markup do rich; o nome do pet entra por format() no core.
CUTSCENE_DORMIR = [
    ("bocejando", "[dim]{nome} boceja... 🥱[/dim]"),
    ("dormindo", "[blue]as luzes se apagam[/blue]  ✦   .    ✦"),
    ("sonhando", "[magenta]💭 sonhando com montanhas de petisco...[/magenta]"),
    ("acordando", "[yellow]☀️ o sol bate na cara de {nome}[/yellow]"),
    ("alongando", "[green]{nome} se espreguiça, renovado. 🛌[/green]"),
]

CUTSCENE_BRINCAR = [
    ("ocioso", "[dim]{nome} percebe que você quer brincar...[/dim]"),
    ("pulando", "[yellow]✦ pula de empolgação ✦[/yellow]"),
    ("correndo", "[cyan]dá uma volta correndo pela tela 💨[/cyan]"),
    ("provocando", "[magenta]{nome} te encara: 'preparado?' 😏[/magenta]"),
]
