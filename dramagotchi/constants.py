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

# Cada pose e um boneco inteiro, com a mesma altura de PET_ASCII (5 linhas).
# O render troca a pose no lugar, entao as alturas precisam bater: se uma
# pose tiver mais ou menos linhas, o resto da tela pula durante a animacao.
POSES = {
    'chorando': '     (\\___/)\n    ( T_T )  \n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^',
    'comendo': '     (\\___/)\n    ( >o_o< ) 🍔\n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^',
    'correndo': '     (\\___/)\n    ( >o_o )>  \n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^',
    'derrota': '     (\\___/)\n    ( ._.  )  \n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^',
    'dormindo': '     (\\___/)\n    ( -.-  ) zZ\n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^',
    'feliz': '     (\\___/)\n    ( \\^O^/ ) !\n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^',
    'ocioso': '     (\\___/)\n    ( ·  .  · )\n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^',
    'vitoria': '     (\\___/)\n    ( ^o^ )/ !!\n   /|       |\\\n  / |       | \\\n    |       |\n   /_|_____|_\\\n     ^^   ^^',
}

# Sequencias de poses: o render alterna entre elas no lugar do boneco.
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

# Pose exibida no estado parado, conforme o humor. O boneco reage ao estado
# do bichinho mesmo sem acao nenhuma.
POSE_POR_HUMOR = {
    "critico": "chorando",
    "faminto": "comendo",
    "cansado": "dormindo",
    "triste": "chorando",
    "feliz": "feliz",
    "neutro": None,   # None = PET_ASCII, a cara neutra
}

# Sequencia do minigame de brincar.
ANIMACOES["correr"] = ["ocioso", "correndo", "ocioso", "correndo", "ocioso",
                       "correndo", "ocioso", "correndo"]
ANIMACOES["ganhou"] = ["vitoria", "feliz", "vitoria", "feliz", "vitoria",
                       "feliz", "vitoria", "feliz"]
ANIMACOES["perdeu"] = ["derrota", "ocioso", "derrota", "ocioso", "derrota",
                       "ocioso", "derrota"]
