from dramagotchi.core import Dramagotchi
from dramagotchi.utils import TELA, checar_terminal
import os


def main():
    if not checar_terminal():
        input("\n[enter] para continuar mesmo assim, ctrl-c para sair")

    # Tenta carregar ou criar novo Dramagotchi
    if os.path.exists("data/save.json"):
        pet = Dramagotchi.load()
    else:
        nome = input("Dê um nome ao seu Dramagotchi: ")
        pet = Dramagotchi(nome)

    aviso = None
    # Uma unica sessao Live no buffer alternativo: o layout ocupa a janela
    # inteira e nada e impresso por fora dele.
    with TELA:
        while pet.is_alive():
            # O decaimento vem do relogio, nao das escolhas.
            pet.decay()
            if not pet.is_alive():
                break

            pendente = pet.memory.pop("aviso_pendente", None)
            if pendente:
                aviso = f"[bold red]{pendente}[/bold red]"

            choice = TELA.perguntar(pet, "[bold]Escolha uma opção:[/bold]", aviso)
            aviso = None

            acoes = {"1": pet.feed, "2": pet.play, "3": pet.sleep, "6": pet.talk}

            if choice == "5":
                break
            elif choice == "4":
                pet.show_emotion_chart()
                continue
            elif choice in acoes:
                acoes[choice]()
                # Cuidar do bichinho conta como interacao: reinicia o relogio.
                pet.tocar()
                pet.save()
            else:
                aviso = "[yellow]Opção inválida.[/yellow]"

    if not pet.is_alive():
        pet.show_summary()


if __name__ == "__main__":
    main()
