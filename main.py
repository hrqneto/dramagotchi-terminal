from dramagotchi.core import Dramagotchi, SAVE_PATH
from dramagotchi.utils import TELA, checar_terminal, mostrar_desfecho, mostrar_texto
from rich.markup import escape
import os


def _novo_pet():
    nome = TELA.perguntar_livre("Dê um nome ao seu Dramagotchi:")
    pet = Dramagotchi(nome or "Sem-nome")
    # Grava ja no nascimento: sair antes da primeira acao nao pode perder o pet.
    pet.save()
    return pet


def _abrir_pet():
    """Carrega o save, ou cria um pet novo. None se o jogador desistir.

    Um save morto nao vira jogo: mostra o desfecho, arquiva e oferece
    recomecar.
    """
    if not os.path.exists(SAVE_PATH):
        return _novo_pet()

    pet = Dramagotchi.load()
    if pet.is_alive():
        return pet

    mostrar_desfecho(pet)
    resposta = TELA.perguntar(
        pet,
        f"[bold]{escape(pet.name)} não resistiu.[/bold] "
        "Criar um bichinho novo? [bold]s[/bold]/[bold]n[/bold]",
    ).lower()[:1]
    if resposta != "s":
        return None

    destino = Dramagotchi.arquivar_save()
    novo = _novo_pet()
    if destino:
        mostrar_texto(novo, f"[dim]Save antigo arquivado em {escape(destino)}[/dim]")
    return novo


def main():
    if not checar_terminal():
        input("\n[enter] para continuar mesmo assim, ctrl-c para sair")

    aviso = None
    with TELA:
        pet = _abrir_pet()
        if pet is None:
            return

        while pet.is_alive():
            pet.decay()
            if not pet.is_alive():
                break

            pendente = pet.memory.pop("aviso_pendente", None)
            if pendente:
                # Aviso de crise e fala espontanea sao texto: param o jogo
                # para serem lidos, em vez de dividir a tela com o menu.
                mostrar_texto(pet, f"[bold red]{escape(pendente)}[/bold red]")
            else:
                fala = pet.falar_sozinho()
                if fala:
                    mostrar_texto(
                        pet, f"[green]{escape(pet.name)}:[/green] 💬 {escape(fala)}")

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
                pet.tocar()
                pet.save()
            else:
                aviso = "[yellow]Opção inválida.[/yellow]"

        if not pet.is_alive():
            pet.save()
            mostrar_desfecho(pet)


if __name__ == "__main__":
    main()
