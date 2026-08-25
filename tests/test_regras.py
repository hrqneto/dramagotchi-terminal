"""Testes da logica pura: acao, decaimento, transicao de estado.

A camada de input/render nao e coberta aqui; valida-se jogando.
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
        # 5 min = 1 tick + 2 min de sobra, preservados no novo last_seen
        ticks, novo = r.ticks_decorridos(300, 0)
        assert ticks == 1 and novo == 180

    def test_relogio_para_tras_nao_quebra(self):
        assert r.ticks_decorridos(0, 999)[0] == 0

    def test_menu_nao_consome_tick(self):
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
        """Dois avisos precisam sair antes da morte."""
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
        """Cheio = bom, igual nas tres barras."""
        assert r.faixa_de_cor(valor) == cor


class TestBalanceamento:
    """Vencivel com atencao, fatal no abandono."""

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


class TestFalaEspontanea:
    def _foto(self, s=6, h=6, e=6):
        return r.instantaneo(s, h, e)

    def test_sem_foto_anterior_nao_ha_transicao(self):
        assert r.transicoes(None, self._foto()) == []

    def test_estado_estavel_nao_gera_evento(self):
        assert r.transicoes(self._foto(), self._foto()) == []

    @pytest.mark.parametrize("antes,depois,evento", [
        ((6, 6, 6), (6, 1, 6), "entrou_critico"),
        ((6, 1, 6), (6, 6, 6), "saiu_critico"),
        ((6, 6, 6), (2, 6, 6), "ficou_faminto"),
        ((6, 6, 3), (6, 6, 9), "acordou"),
        ((6, 5, 6), (6, 9, 6), "ficou_feliz"),
    ])
    def test_transicoes(self, antes, depois, evento):
        assert evento in r.transicoes(self._foto(*antes), self._foto(*depois))

    def test_so_dispara_em_transicao(self):
        """Estado ruim parado nao fala de novo a cada turno."""
        foto = self._foto(2, 2, 2)
        assert r.deve_falar(1000, None, r.transicoes(foto, foto)) is None

    def test_cooldown_bloqueia(self):
        assert r.deve_falar(1000, 990, ["ficou_faminto"], cooldown=90) is None

    def test_fala_depois_do_cooldown(self):
        assert r.deve_falar(1100, 1000, ["ficou_faminto"], cooldown=90) == "ficou_faminto"

    def test_primeira_fala_nao_espera_cooldown(self):
        assert r.deve_falar(10, None, ["ficou_faminto"]) == "ficou_faminto"

    def test_ocioso_dispara_sem_evento(self):
        assert r.deve_falar(1000, None, [], ocioso_desde=0, limite_ocioso=300) == "ocioso"

    def test_ocioso_curto_nao_dispara(self):
        assert r.deve_falar(100, None, [], ocioso_desde=0, limite_ocioso=300) is None

    def test_evento_tem_prioridade_sobre_ocioso(self):
        assert r.deve_falar(1000, None, ["entrou_critico"], ocioso_desde=0) == "entrou_critico"

    def test_critico_vem_antes_de_fome(self):
        eventos = r.transicoes(self._foto(6, 6, 6), self._foto(1, 1, 1))
        assert eventos[0] == "entrou_critico"

    def test_prompt_carrega_contexto(self):
        p = r.montar_prompt_fala("Kiki", "carente", 2, 9, 4, "ficou_faminto", "brincar")
        for esperado in ["Kiki", "carente", "2/10", "9/10", "4/10", "brincar"]:
            assert esperado in p

    def test_prompt_sem_ultima_acao(self):
        p = r.montar_prompt_fala("Kiki", "carente", 5, 5, 5, "ocioso")
        assert "ultima coisa" not in p

class TestProgressoDaCutscene:
    """Assistir a cutscene rende um bonus; pular mantem o ganho de sempre."""

    def test_sem_cutscene_e_o_padrao(self):
        """O default nao da bonus: acoes fora de cutscene rendem o de sempre."""
        assert r.aplicar_sleep(3, 8, "resmungão") == r.aplicar_sleep(3, 8, "resmungão", 0.0)

    def test_assistir_dormir_rende_mais(self):
        pulado = r.aplicar_sleep(0, 8, "resmungão", 0.0)[0]
        inteiro = r.aplicar_sleep(0, 8, "resmungão", 1.0)[0]
        assert inteiro == pulado + r.BONUS_CUTSCENE

    def test_pular_dormir_nao_perde_nada(self):
        """Pular rende exatamente o ganho ja balanceado, sem punicao."""
        base = 5  # bonus do resmungão em aplicar_sleep
        assert r.aplicar_sleep(0, 8, "resmungão", 0.0)[0] == base

    def test_custo_de_saciedade_independe_do_progresso(self):
        assert (r.aplicar_sleep(3, 8, "carente", 0.0)[1]
                == r.aplicar_sleep(3, 8, "carente", 1.0)[1])

    def test_assistir_brincar_rende_mais(self):
        _, _, pulado = r.aplicar_play(0, 5, "resmungão", "ganhou", 0.0)
        _, _, inteiro = r.aplicar_play(0, 5, "resmungão", "ganhou", 1.0)
        assert inteiro == pulado + r.BONUS_CUTSCENE

    def test_custo_de_energia_independe_do_progresso(self):
        assert (r.aplicar_play(5, 5, "resmungão", "ganhou", 0.0)[1]
                == r.aplicar_play(5, 5, "resmungão", "ganhou", 1.0)[1])

    def test_bonus_nunca_diminui_com_mais_progresso(self):
        ganhos = [r.aplicar_play(0, 5, "resmungão", "ganhou", p / 10)[2]
                  for p in range(11)]
        assert ganhos == sorted(ganhos) and ganhos[-1] > ganhos[0]

    @pytest.mark.parametrize("fora,limite", [(-5.0, 0.0), (7.0, 1.0)])
    def test_progresso_fora_da_faixa_e_preso(self, fora, limite):
        assert (r.aplicar_sleep(0, 8, "carente", fora)
                == r.aplicar_sleep(0, 8, "carente", limite))

    def test_bonus_nao_supera_o_teto(self):
        assert r.bonus_por_progresso(1.0) == r.BONUS_CUTSCENE

    @pytest.mark.parametrize("personality", ["carente", "brincalhão", "resmungão"])
    @pytest.mark.parametrize("progresso", [0.0, 0.5, 1.0])
    def test_sustentavel_em_qualquer_progresso(self, personality, progresso):
        """Pular ou assistir, cuidar do pior status sustenta o pet."""
        s = h = e = 5
        for _ in range(100):
            pior = min(s, h, e)
            if s == pior:
                s, _ = r.aplicar_feed(s)
            elif e == pior:
                e, s = r.aplicar_sleep(e, s, personality, progresso)
            else:
                h, e, _ = r.aplicar_play(h, e, personality, "perdeu", progresso)
            s, h, e = r.aplicar_tick(s, h, e)
            assert r.esta_vivo(s, h, e), "o ritmo escolhido nao pode matar o pet"
