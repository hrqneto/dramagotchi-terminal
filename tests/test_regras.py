"""Testes da logica pura do jogo.

Cobre regras: acao, decaimento, transicao de estado. A camada de
input/render (rich, leitura de tecla crua) nao e testada aqui — jogo de
terminal se valida jogando.
"""
import pytest

from dramagotchi import regras as r


class TestAcoes:
    def test_alimentar_aumenta_saciedade(self):
        assert r.aplicar_feed(3) == (7, True)

    def test_alimentar_nao_passa_do_maximo(self):
        assert r.aplicar_feed(8) == (10, True)

    def test_alimentar_cheio_nao_faz_nada(self):
        assert r.aplicar_feed(10) == (10, False)

    @pytest.mark.parametrize("resultado,esperado", [
        ("ganhou", 7), ("empate", 5), ("perdeu", 4),
    ])
    def test_ganho_por_resultado(self, resultado, esperado):
        h, _, ganho = r.aplicar_play(0, 5, "resmungão", resultado)
        assert ganho == esperado and h == esperado

    def test_vencer_da_mais_que_perder(self):
        assert r.GANHO_MINIGAME["ganhou"] > r.GANHO_MINIGAME["empate"] > r.GANHO_MINIGAME["perdeu"]

    def test_brincalhao_ganha_bonus(self):
        _, _, normal = r.aplicar_play(0, 5, "resmungão", "ganhou")
        _, _, bonus = r.aplicar_play(0, 5, "brincalhão", "ganhou")
        assert bonus == normal + 1

    def test_brincar_custa_energia(self):
        _, energia, _ = r.aplicar_play(5, 5, "resmungão", "ganhou")
        assert energia == 3

    def test_brincar_sem_energia_nao_muda_nada(self):
        assert r.aplicar_play(5, 0, "resmungão", "ganhou") == (5, 0, 0)

    def test_dormir_recupera_energia_e_da_fome(self):
        energia, saciedade = r.aplicar_sleep(3, 8, "resmungão")
        assert energia == 8 and saciedade == 6

    def test_carente_dorme_melhor(self):
        assert r.aplicar_sleep(3, 8, "carente")[0] > r.aplicar_sleep(3, 8, "resmungão")[0]


class TestDecaimento:
    def test_tick_reduz_tudo(self):
        assert r.aplicar_tick(5, 5, 5) == (4, 4, 4)

    def test_tick_nao_passa_de_zero(self):
        assert r.aplicar_tick(0, 0, 0) == (0, 0, 0)

    @pytest.mark.parametrize("minutos,ticks", [(0, 0), (2, 0), (3, 1), (9, 3), (61, 20)])
    def test_ticks_por_tempo(self, minutos, ticks):
        assert r.ticks_decorridos(minutos * 60, 0)[0] == ticks

    def test_resto_do_periodo_nao_se_perde(self):
        # 5 min = 1 tick + 2 min de sobra; o last_seen recua para guardar a sobra
        ticks, novo = r.ticks_decorridos(300, 0)
        assert ticks == 1 and novo == 180

    def test_relogio_para_tras_nao_quebra(self):
        assert r.ticks_decorridos(0, 999)[0] == 0

    def test_menu_nao_consome_tick(self):
        # mesma marca de tempo: abrir menu nao decai
        assert r.ticks_decorridos(500, 500)[0] == 0


class TestVidaECrise:
    @pytest.mark.parametrize("s,h,e,vivo", [
        (5, 5, 5, True), (1, 1, 1, True),
        (0, 5, 5, False), (5, 0, 5, False), (5, 5, 0, False),
    ])
    def test_esta_vivo(self, s, h, e, vivo):
        assert r.esta_vivo(s, h, e) is vivo

    def test_drama_encerra_mesmo_com_status_bons(self):
        assert r.esta_vivo(9, 9, 9, drama_triggered=True) is False

    def test_primeira_crise_da_folga_e_avisa(self):
        s, h, e, hits, morreu, avisou = r.resolver_crise(0, 5, 5, 0)
        assert (s, hits, morreu, avisou) == (1, 1, False, True)

    def test_segunda_crise_ainda_segura(self):
        _, _, _, hits, morreu, avisou = r.resolver_crise(0, 5, 5, 1)
        assert (hits, morreu, avisou) == (2, False, True)

    def test_terceira_crise_mata(self):
        _, _, _, hits, morreu, avisou = r.resolver_crise(0, 5, 5, 2)
        assert (hits, morreu, avisou) == (3, True, False)

    def test_duas_chances_antes_do_fim(self):
        """O bug: morria sem nunca passar pelos avisos."""
        s = h = e = 5
        hits, avisos, morreu = 0, 0, False
        for _ in range(40):
            s, h, e = r.aplicar_tick(s, h, e)
            s, h, e, hits, morreu, avisou = r.resolver_crise(s, h, e, hits)
            avisos += avisou
            if morreu:
                break
        assert avisos == 2 and morreu

    def test_sem_crise_nao_mexe_nos_status(self):
        assert r.resolver_crise(5, 5, 5, 0) == (5, 5, 5, 0, False, False)


class TestMinigame:
    @pytest.mark.parametrize("jogador,pet,esperado", [
        ("pedra", "tesoura", "ganhou"), ("papel", "pedra", "ganhou"),
        ("tesoura", "papel", "ganhou"), ("pedra", "papel", "perdeu"),
        ("papel", "tesoura", "perdeu"), ("tesoura", "pedra", "perdeu"),
        ("pedra", "pedra", "empate"),
    ])
    def test_jokenpo(self, jogador, pet, esperado):
        assert r.jogar_jokenpo(jogador, pet) == esperado

    def test_toda_jogada_tem_resultado(self):
        opcoes = ["pedra", "papel", "tesoura"]
        for a in opcoes:
            for b in opcoes:
                assert r.jogar_jokenpo(a, b) in ("ganhou", "perdeu", "empate")


class TestEstado:
    def test_saciedade_baixa_e_faminto(self):
        assert r.estado_emocional(1, 5, 5) == "faminto"

    def test_saciedade_alta_e_neutro(self):
        assert r.estado_emocional(9, 5, 5) == "neutro"

    def test_estado_composto(self):
        assert r.estado_emocional(1, 1, 1) == "faminto+triste+cansado"

    @pytest.mark.parametrize("s,h,e,pose", [
        (0, 5, 5, "critico"), (3, 5, 5, "faminto"), (6, 6, 3, "cansado"),
        (6, 4, 6, "triste"), (6, 9, 6, "feliz"), (6, 6, 6, "neutro"),
    ])
    def test_pose_por_humor(self, s, h, e, pose):
        assert r.humor_para_pose(s, h, e) == pose

    @pytest.mark.parametrize("valor,cor", [
        (10, "green"), (7, "green"), (6, "yellow"), (4, "yellow"), (3, "red"), (0, "red"),
    ])
    def test_cor_cheio_e_bom(self, valor, cor):
        """As tres barras seguem a mesma logica: cheio = bom."""
        assert r.faixa_de_cor(valor) == cor


class TestBalanceamento:
    """O jogo tem que ser vencivel com atencao e punir abandono."""

    def _jogar(self, personality, resultados):
        s = h = e = 5
        for turno in range(100):
            if s <= 4:
                s, _ = r.aplicar_feed(s)
            elif e <= 4:
                e, s = r.aplicar_sleep(e, s, personality)
            else:
                h, e, _ = r.aplicar_play(h, e, personality, resultados[turno % len(resultados)])
            s, h, e = r.aplicar_tick(s, h, e)
            if not r.esta_vivo(s, h, e):
                return turno
        return None

    @pytest.mark.parametrize("personality", ["carente", "brincalhão", "resmungão"])
    def test_vencivel_com_atencao(self, personality):
        assert self._jogar(personality, ["ganhou", "empate", "perdeu"]) is None

    @pytest.mark.parametrize("personality", ["carente", "brincalhão", "resmungão"])
    def test_vencivel_mesmo_perdendo_sempre(self, personality):
        assert self._jogar(personality, ["perdeu"]) is None

    def test_abandono_mata(self):
        s = h = e = 5
        for turno in range(60):
            s, h, e = r.aplicar_tick(s, h, e)
            if not r.esta_vivo(s, h, e):
                assert turno < 20, "abandono deveria matar rapido"
                return
        pytest.fail("abandono nao matou")
