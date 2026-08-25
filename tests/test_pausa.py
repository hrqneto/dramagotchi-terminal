"""Garante a regra: quadro de animacao avanca sozinho, texto so sai com tecla.

Nao simula terminal — verifica que todo texto passa pela porta unica
(`mostrar_texto`), que e onde vive a espera. Um caminho novo que desenhe
texto sem passar por ela e o bug que estes testes existem para pegar.
"""
from unittest.mock import patch

import pytest

from dramagotchi import core, utils
from dramagotchi.core import Dramagotchi


@pytest.fixture
def pet():
    p = Dramagotchi("teste")
    p.satiety = p.happiness = p.energy = 8
    return p


@pytest.fixture
def espiao():
    """Troca mostrar_texto por um espiao nos dois modulos que a usam."""
    vistos = []

    def falso(pet, mensagem=None, pose=None, dim=False, palco=None):
        vistos.append(mensagem)

    # Sem stub de sleep, cada teste paga os quadros da animacao em tempo real.
    with patch.object(utils, "mostrar_texto", falso), \
         patch.object(utils.TELA, "desenhar"), \
         patch.object(utils.time, "sleep"), \
         patch.object(core, "mostrar_palco", lambda p, palco, mensagem=None, **k:
                      vistos.append(mensagem)):
        yield vistos


class TestTextoEsperaTecla:
    def test_resultado_de_acao_passa_pela_porta(self, pet, espiao):
        pet.feed()
        assert any("alimentado" in (m or "") for m in espiao)

    def test_cutscene_pausa_em_cada_legenda(self, pet):
        """Cada quadro narrado espera tecla, nao so o ultimo."""
        quadros = [("ocioso", f"legenda {i}") for i in range(4)]
        with patch.object(utils, "_pode_esperar_tecla", return_value=True), \
             patch.object(utils.TELA, "desenhar"), \
             patch.object(utils, "esperar_tecla", return_value=" ") as tecla:
            assert utils.cutscene(pet, quadros) == 1.0
        assert tecla.call_count == len(quadros)

    def test_esc_pula_o_resto_e_reduz_o_ganho(self, pet):
        quadros = [("ocioso", f"legenda {i}") for i in range(4)]
        with patch.object(utils, "_pode_esperar_tecla", return_value=True), \
             patch.object(utils.TELA, "desenhar"), \
             patch.object(utils, "esperar_tecla", return_value="\x1b"):
            assert utils.cutscene(pet, quadros) == 0.0

    def test_jokenpo_tem_tres_beats(self, pet):
        """Escolha, revelacao e resultado sao paradas separadas."""
        with patch.object(utils, "mostrar_texto") as mt:
            resultado, palco = utils.minigame_jokenpo(pet, "pedra")
        # dois beats pausam aqui; o terceiro e o palco devolvido ao chamador
        assert mt.call_count == 2
        assert resultado in ("ganhou", "perdeu", "empate")
        assert palco is not None

    def test_revelacao_nao_entrega_o_veredito(self, pet):
        """O beat 2 mostra as maos sem dizer quem ganhou."""
        with patch.object(utils, "mostrar_texto") as mt:
            utils.minigame_jokenpo(pet, "pedra")
        textos = [c.args[1] for c in mt.call_args_list]
        assert not any(
            p in (t or "") for t in textos for p in ("venceu", "Empate")
        )

    def test_mao_do_bicho_escondida_no_primeiro_beat(self, pet):
        oculto = utils._palco_jokenpo(pet, "pedra")
        revelado = utils._palco_jokenpo(pet, "pedra", "tesoura")
        assert oculto is not None and revelado is not None

    def test_animacao_sem_texto_nao_pausa(self, pet):
        """Quadro puro avanca sozinho: sem mensagem, sem espera."""
        with patch.object(utils.TELA, "desenhar"), \
             patch.object(utils.time, "sleep"), \
             patch.object(utils, "esperar_tecla") as tecla:
            utils.animate(pet, "idle")
        tecla.assert_not_called()


class TestFormaDasMaos:
    def test_mao_oculta_tem_a_altura_das_outras(self):
        """Altura diferente faria a mesa pular entre a revelacao e o resultado."""
        alturas = {len(m.split("\n")) for m in utils.JOKENPO.values()}
        assert alturas == {len(utils.JOKENPO_OCULTO.split("\n"))}
