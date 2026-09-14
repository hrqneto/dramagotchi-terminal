"""Recuperacao de save morto: o jogo tem que sair do save morto sozinho.

O bug que estes testes existem para pegar: `_abrir_pet` tratava qualquer
resposta que nao fosse "s" como recusa, entao um enter vazio fechava o jogo
sem arquivar — e a proxima abertura caia no mesmo save morto, sem saida a
nao ser apagar o arquivo na mao.
"""
import json
from unittest.mock import patch

import pytest

import main
from dramagotchi.core import Dramagotchi


@pytest.fixture
def save_morto(tmp_path, monkeypatch):
    """Instala um save de bichinho morto num diretorio temporario."""
    caminho = tmp_path / "save.json"
    morto = {
        "name": "Falecido", "satiety": 0, "happiness": 0, "energy": 0,
        "personality": "carente", "birth": 1.0, "last_seen": 2.0,
        "memory": {"feed": 1, "play": 1, "sleep": 1, "emotions": ["triste"],
                   "conversations": 0, "crisis_count": 2, "critical_hits": 2,
                   "drama_triggered": True, "in_critical": True,
                   "ultima_acao": None},
        "ultima_fala": None, "ocioso_desde": 2.0, "_foto": None,
    }
    caminho.write_text(json.dumps(morto))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main, "SAVE_PATH", str(caminho))
    monkeypatch.setattr("dramagotchi.core.SAVE_PATH", str(caminho))
    return caminho


@pytest.fixture
def sem_tela():
    """Neutraliza desenho e espera de tecla: o teste e do fluxo, nao do render."""
    with patch.object(main, "mostrar_desfecho"), \
         patch.object(main, "mostrar_texto"), \
         patch.object(main, "_tem_entrada", return_value=True):
        yield


def _responder(*respostas):
    """TELA.perguntar devolve cada resposta na ordem; perguntar_livre da o nome."""
    it = iter(respostas)
    return patch.object(main.TELA, "perguntar", side_effect=lambda *a, **k: next(it))


def test_aceitar_arquiva_o_save_e_devolve_bichinho_novo(save_morto, sem_tela):
    with _responder("s"), patch.object(main.TELA, "perguntar_livre",
                                       return_value="Novo"):
        novo = main._abrir_pet()

    assert novo is not None and novo.name == "Novo"
    assert novo.is_alive()
    # O save morto saiu do caminho: abrir de novo nao cai na mesma tela.
    arquivados = list(save_morto.parent.glob("save.json.*.morto"))
    assert len(arquivados) == 1
    assert json.loads(arquivados[0].read_text())["name"] == "Falecido"


def test_enter_vazio_repergunta_em_vez_de_fechar(save_morto, sem_tela):
    """O bug do loop: vazio era lido como recusa e o jogo fechava sem arquivar."""
    with _responder("", "  ", "s"), patch.object(main.TELA, "perguntar_livre",
                                                 return_value="Novo"):
        novo = main._abrir_pet()

    assert novo is not None, "enter vazio nao pode encerrar o jogo"
    assert list(save_morto.parent.glob("save.json.*.morto"))


def test_esc_na_pergunta_nao_aborta_a_recuperacao(save_morto, sem_tela):
    """ESC respondido na pergunta s/n nao pode encerrar: so repergunta."""
    with _responder("\x1b", "s"), patch.object(main.TELA, "perguntar_livre",
                                               return_value="Novo"):
        novo = main._abrir_pet()

    assert novo is not None, "ESC nao pode encerrar o jogo"
    assert list(save_morto.parent.glob("save.json.*.morto"))


def test_esc_na_pergunta_apenas_repergunta(save_morto, sem_tela):
    """ESC nao e s nem n: repergunta, em vez de travar ou fechar."""
    respostas = []

    def responde(*a, **k):
        respostas.append(1)
        return "\x1b" if len(respostas) < 3 else "s"

    with patch.object(main.TELA, "perguntar", side_effect=responde), \
         patch.object(main.TELA, "perguntar_livre", return_value="Novo"):
        novo = main._abrir_pet()

    assert len(respostas) == 3, "cada ESC tem que gerar uma nova pergunta"
    assert novo is not None


def test_pergunta_de_recomeco_pede_tecla_unica(save_morto, sem_tela):
    """s/n tem que responder na primeira tecla — esperar enter engolia o ESC."""
    with patch.object(main.TELA, "perguntar", return_value="s") as perguntou, \
         patch.object(main.TELA, "perguntar_livre", return_value="Novo"):
        main._abrir_pet()

    assert perguntou.call_args.kwargs.get("tecla_unica") is True


def test_recusar_preserva_o_save_e_encerra(save_morto, sem_tela):
    with _responder("n"):
        assert main._abrir_pet() is None

    assert not list(save_morto.parent.glob("save.json.*.morto"))
    assert json.loads(save_morto.read_text())["name"] == "Falecido"


def test_sem_teclado_nao_entra_em_loop(save_morto):
    """Sem tty, reperguntar seria loop infinito: encerra em vez de insistir."""
    with patch.object(main, "mostrar_desfecho"), \
         patch.object(main, "_tem_entrada", return_value=False), \
         patch.object(main.TELA, "perguntar", return_value="") as perguntou:
        assert main._abrir_pet() is None
    assert perguntou.call_count == 0


def test_save_vivo_nao_passa_pela_recuperacao(save_morto, sem_tela):
    vivo = json.loads(save_morto.read_text())
    vivo.update(name="Vivo", satiety=5, happiness=5, energy=5)
    vivo["memory"]["drama_triggered"] = False
    save_morto.write_text(json.dumps(vivo))

    with patch.object(main.TELA, "perguntar") as perguntou:
        pet = main._abrir_pet()

    assert pet.name == "Vivo"
    assert perguntou.call_count == 0


class _StdinFalso:
    """stdin de mentira: so precisa de fileno() e isatty() para o leitor."""

    def fileno(self):
        return 0

    def isatty(self):
        return True


class TestTeclado:
    """Testes na camada de teclado, onde o bug do ESC realmente morava.

    Os testes acima trocam `TELA.perguntar` por um mock — util para o fluxo,
    mas cego para o leitor de teclas. Aqui a tecla entra como byte.
    """

    def _le(self, monkeypatch, bytes_teclado):
        """Roda _ler_uma_tecla com o teclado simulado byte a byte."""
        from dramagotchi import utils

        import termios, tty

        it = iter(bytes_teclado)
        monkeypatch.setattr(utils, "_pode_esperar_tecla", lambda: True)
        monkeypatch.setattr(utils.os, "read", lambda fd, n: next(it))
        # pytest captura o stdin: fileno() nao existe, e o codigo pede um fd.
        monkeypatch.setattr(utils.sys, "stdin", _StdinFalso())
        # termios/tty so mexem no terminal real: neutralizados no teste.
        monkeypatch.setattr(termios, "tcgetattr", lambda fd: None)
        monkeypatch.setattr(termios, "tcsetattr", lambda *a: None)
        monkeypatch.setattr(termios, "tcflush", lambda *a: None)
        monkeypatch.setattr(tty, "setcbreak", lambda fd: None)
        monkeypatch.setattr(utils.TELA, "desenhar", lambda r: None)

        pet = Dramagotchi("teste")
        return utils.TELA._ler_uma_tecla(pet, "s/n", None)

    def test_esc_e_devolvido_como_tecla_comum(self, monkeypatch):
        """ESC nao pode ser engolido: quem pergunta e que decide o que fazer."""
        assert self._le(monkeypatch, [b"\x1b"]) == "\x1b"

    def test_tecla_normal_passa(self, monkeypatch):
        assert self._le(monkeypatch, [b"s"]) == "s"

    def test_nao_espera_enter(self, monkeypatch):
        """Um unico byte basta: se pedisse enter, o proximo read estouraria."""
        assert self._le(monkeypatch, [b"n"]) == "n"


class TestPausaDeTexto:
    """A pausa "▸ tecla para continuar" tem que aceitar QUALQUER tecla.

    Os testes de fluxo acima trocam `mostrar_desfecho` por um mock, entao
    nunca chegam a executar a pausa — foi assim que um teste chamado "ESC no
    desfecho" passou sem nunca mandar ESC para a pausa. Aqui a pausa roda de
    verdade, com a tecla entrando como valor.
    """

    @pytest.fixture
    def pausa_real(self, monkeypatch):
        """Deixa mostrar_texto rodar de verdade, so trocando tela e teclado."""
        from dramagotchi import utils

        monkeypatch.setattr(utils.TELA, "desenhar", lambda r: None)
        monkeypatch.setattr(utils.TELA, "live", object())  # finge Live no ar
        return utils

    @pytest.mark.parametrize("tecla", ["\x1b", "q", "Q", " ", "\n", "z"])
    def test_qualquer_tecla_dispensa_a_pausa(self, pausa_real, monkeypatch, tecla):
        """Nenhuma tecla pode ter efeito especial numa pausa de texto."""
        chamadas = []
        monkeypatch.setattr(pausa_real, "esperar_tecla",
                            lambda: chamadas.append(tecla) or tecla)
        monkeypatch.setitem(pausa_real.mostrar_texto.__globals__,
                            "esperar_tecla", lambda: chamadas.append(tecla) or tecla)

        pet = Dramagotchi("teste")
        pausa_real.mostrar_texto(pet, "um texto qualquer")

        assert len(chamadas) == 1, "a pausa tem que esperar exatamente uma tecla"

    def test_desfecho_com_esc_chega_na_pergunta(self, save_morto, monkeypatch):
        """Fluxo real: ESC na pausa do desfecho nao pode pular a pergunta.

        Sem mockar mostrar_desfecho — e justamente o passo que os outros
        testes escondiam.
        """
        from dramagotchi import utils

        monkeypatch.setattr(utils.TELA, "desenhar", lambda r: None)
        monkeypatch.setattr(utils.TELA, "live", object())
        monkeypatch.setattr(utils, "esperar_tecla", lambda: "\x1b")
        monkeypatch.setitem(utils.mostrar_texto.__globals__,
                            "esperar_tecla", lambda: "\x1b")
        monkeypatch.setattr(main, "mostrar_texto", utils.mostrar_texto)
        monkeypatch.setattr(main, "_tem_entrada", lambda: True)

        perguntas = []

        def perguntar(*a, **k):
            perguntas.append(1)
            return "s"

        monkeypatch.setattr(main.TELA, "perguntar", perguntar)
        monkeypatch.setattr(main.TELA, "perguntar_livre", lambda p: "Novo")

        novo = main._abrir_pet()

        assert perguntas, "ESC na pausa do desfecho engoliu a pergunta s/n"
        assert novo is not None and novo.name == "Novo"
        assert list(save_morto.parent.glob("save.json.*.morto"))
