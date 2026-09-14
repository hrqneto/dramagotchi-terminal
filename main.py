from dramagotchi.core import Dramagotchi, SAVE_PATH, aquecer_modelo
from dramagotchi.utils import TELA, checar_terminal, mostrar_desfecho, mostrar_texto
from rich.markup import escape
import os
import sys


def _tem_entrada():
    """Se nao ha teclado, repetir a pergunta so viraria loop infinito."""
    return sys.stdin.isatty()


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
    # Responde na primeira tecla, e so s/n valem: qualquer outra repergunta.
    # Tratar tecla desconhecida (ESC, enter) como "nao" fechava o jogo sem
    # arquivar, e a proxima abertura caia no mesmo save morto — sem saida a
    # nao ser apagar o arquivo na mao.
    resposta = ""
    while resposta not in ("s", "n"):
        if not _tem_entrada():
            return None   # sem teclado, insistir so viraria loop infinito
        resposta = TELA.perguntar(
            pet,
            f"[bold]{escape(pet.name)} não resistiu.[/bold] "
            "Criar um bichinho novo? [bold]s[/bold]/[bold]n[/bold]",
            so_palco=True,
            tecla_unica=True,
        ).lower()[:1]

    if resposta == "n":
        return None

    destino = Dramagotchi.arquivar_save()
    novo = _novo_pet()
    if destino:
        mostrar_texto(novo, f"[dim]Save antigo arquivado em {escape(destino)}[/dim]")
    return novo


def _recomecar(pet):
    """Troca o bichinho por um novo, arquivando o save. None se desistir."""
    resposta = TELA.perguntar(
        pet,
        f"[bold]Recomeçar?[/bold] {escape(pet.name)} será arquivado e você "
        "começa do zero. [bold]s[/bold]/[bold]n[/bold]",
        tecla_unica=True,
    ).lower()[:1]
    if resposta != "s":
        return None   # qualquer tecla que nao seja "s" cancela: o jogo continua

    pet.save()   # arquiva o estado atual, nao o do ultimo save
    destino = Dramagotchi.arquivar_save("trocado")
    novo = _novo_pet()
    if destino:
        mostrar_texto(novo, f"[dim]Save antigo arquivado em {escape(destino)}[/dim]")
    return novo


def _jogar(pet):
    """Loop de jogo. Devolve (pet_atual, interrompido).

    O pet pode trocar no meio: a opcao de recomecar cria outro.
    """
    aviso = None
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

        try:
            choice = TELA.perguntar(pet, "[bold]Escolha uma opção:[/bold]", aviso)
        except KeyboardInterrupt:
            # Ctrl+C chega como excecao do os.read: sai igual a opcao [5].
            return pet, True
        aviso = None

        acoes = {"1": pet.feed, "2": pet.play, "3": pet.sleep, "6": pet.talk}

        if choice == "5":
            break
        elif choice == "7":
            novo = _recomecar(pet)
            if novo is not None:
                pet = novo
            continue
        elif choice == "4":
            pet.show_emotion_chart()
            continue
        elif choice in acoes:
            acoes[choice]()
            pet.tocar()
            pet.save()
        else:
            aviso = "[yellow]Opção inválida.[/yellow]"
    return pet, False


def main():
    if not checar_terminal():
        input("\n[enter] para continuar mesmo assim, ctrl-c para sair")

    # A primeira chamada a um modelo local so carrega a RAM (~15s, acima do
    # timeout): aquece no boot para a primeira fala nao cair no fallback.
    aquecer_modelo()

    pet = None
    interrompido = False
    with TELA:
        try:
            pet = _abrir_pet()
            if pet is not None:
                pet, interrompido = _jogar(pet)
        except KeyboardInterrupt:
            # Ctrl+C fora do menu (nome, cutscene, pausa de texto).
            interrompido = True

        if pet is not None:
            pet.save()
            if not interrompido and not pet.is_alive():
                mostrar_desfecho(pet)

    if interrompido:
        print("Até logo! 👋")


if __name__ == "__main__":
    main()
