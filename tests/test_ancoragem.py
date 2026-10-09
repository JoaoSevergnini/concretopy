from dataclasses import FrozenInstanceError
from math import log

import pytest

from concretopy import Aco, Barra, Concreto, CondicoesAncoragem, ResultadoAncoragem, calcular_ancoragem
from concretopy.normas.nbr6118 import (
    coeficiente_aderencia_eta2, coeficiente_aderencia_eta3,
    comprimento_minimo_ancoragem_cm,
)


def calcular(**kwargs):
    dados = dict(concreto=Concreto(30), aco=Aco(500), bitola_mm=16,
                 as_calculada_cm2=6.20, as_efetiva_cm2=8.04,
                 condicoes=CondicoesAncoragem(boa_aderencia=True))
    dados.update(kwargs)
    return calcular_ancoragem(**dados)


def test_fbd_e_resistencias_em_mpa():
    r = calcular()
    assert r.fctd_mpa == pytest.approx(1.448234076908445)
    assert r.fyd_mpa == pytest.approx(434.7826086956522)
    assert (r.eta1, r.eta2, r.eta3) == (2.25, 1.0, 1.0)
    assert r.fbd_mpa == pytest.approx(3.258526673044)


@pytest.mark.parametrize('boa,fbd,lb', [
    (True, 4.580579728003904, 59.32417872206744),
    (False, 3.206405809602732, 84.74882674581065),
])
def test_referencia_planilha_com_piso_normativo(boa, fbd, lb):
    # VIGAS!R27:R28 e I22/I30. A planilha omite o piso 25 phi:
    # em boa aderencia para C50, 25 mm, o piso altera 59,324... para 62,5 cm.
    r = calcular(concreto=Concreto(50), bitola_mm=25,
                 as_calculada_cm2=8.04, condicoes=CondicoesAncoragem(boa))
    assert r.fbd_mpa == pytest.approx(fbd)
    assert 2.5 / 4 * r.fyd_mpa / r.fbd_mpa == pytest.approx(lb)
    assert r.lb_cm == pytest.approx(max(lb, 62.5))
    assert r.lb_nec_cm == pytest.approx(r.lb_cm)


def test_lb_conversao_mm_para_cm():
    r = calcular(bitola_mm=Barra(16).diametro_mm)
    assert r.lb_cm == pytest.approx(53.37168018815003)
    assert r.lb_cm >= 40


def test_lb_min_e_lb_nec_com_excesso_de_area():
    r = calcular()
    assert r.lb_min_cm == pytest.approx(0.3 * r.lb_cm)
    assert r.lb_nec_cm == pytest.approx(r.lb_cm * 6.20 / 8.04)
    sem_excesso = calcular(as_calculada_cm2=8.04)
    assert sem_excesso.lb_nec_cm == pytest.approx(sem_excesso.lb_cm)
    assert r.lb_nec_cm < sem_excesso.lb_nec_cm


@pytest.mark.parametrize('bitola,lb,minimo', [(8, 20, 10), (16, 40, 16), (16, 100, 30)])
def test_tres_limites_de_lb_min(bitola, lb, minimo):
    assert comprimento_minimo_ancoragem_cm(lb, bitola) == pytest.approx(minimo)


def test_reducao_por_area_respeita_minimo():
    r = calcular(as_calculada_cm2=0.01)
    assert r.lb_nec_cm == pytest.approx(r.lb_min_cm)


def test_ma_aderencia_aumenta_comprimento():
    boa = calcular()
    ma = calcular(condicoes=CondicoesAncoragem(False))
    assert ma.fbd_mpa == pytest.approx(0.7 * boa.fbd_mpa)
    assert ma.lb_cm == pytest.approx(boa.lb_cm / 0.7)
    assert ma.lb_nec_cm > boa.lb_nec_cm


@pytest.mark.parametrize('bitola,eta3', [(31.999, 1), (32, 1), (32.001, 0.99999), (40, 0.92)])
def test_eta3_no_limite_e_acima_de_32(bitola, eta3):
    r = calcular(bitola_mm=bitola)
    assert r.eta3 == pytest.approx(eta3)
    assert r.fbd_mpa == pytest.approx(2.25 * eta3 * r.fctd_mpa)
    assert r.lb_cm == pytest.approx(max(bitola / 40 * r.fyd_mpa / r.fbd_mpa, 2.5 * bitola))


@pytest.mark.parametrize('delta,atende', [(0, True), (1, True), (-0.000001, False)])
def test_verificacao_comprimento(delta, atende):
    necessario = calcular().lb_nec_cm
    r = calcular(comprimento_disponivel_cm=necessario + delta)
    assert r.atende is atende
    assert r.comprimento_disponivel_cm == necessario + delta


def test_comprimento_zero_e_omissao():
    assert calcular(comprimento_disponivel_cm=0).atende is False
    assert calcular().atende is None
    assert calcular().comprimento_disponivel_cm is None


@pytest.mark.parametrize('campo', ['bitola_mm', 'as_calculada_cm2', 'as_efetiva_cm2', 'gamma_c', 'gamma_s'])
@pytest.mark.parametrize('valor', [0, -1, float('nan'), float('inf'), -float('inf')])
def test_entradas_numericas_invalidas(campo, valor):
    with pytest.raises(ValueError):
        calcular(**{campo: valor})


@pytest.mark.parametrize('campo', ['bitola_mm', 'as_calculada_cm2', 'as_efetiva_cm2', 'gamma_c', 'gamma_s', 'comprimento_disponivel_cm'])
@pytest.mark.parametrize('valor', [True, '16'])
def test_tipos_numericos_invalidos(campo, valor):
    with pytest.raises(TypeError):
        calcular(**{campo: valor})


@pytest.mark.parametrize('valor', [-1, float('nan'), float('inf')])
def test_comprimento_disponivel_invalido(valor):
    with pytest.raises(ValueError):
        calcular(comprimento_disponivel_cm=valor)


@pytest.mark.parametrize('valor', [132, 150])
def test_bitola_que_produz_eta3_nao_positivo(valor):
    with pytest.raises(ValueError, match='eta3'):
        calcular(bitola_mm=valor)


def test_area_insuficiente_nao_se_resolve_com_mais_ancoragem():
    with pytest.raises(ValueError, match='as_efetiva'):
        calcular(as_calculada_cm2=9, as_efetiva_cm2=8.04)


@pytest.mark.parametrize('valor', [1, None, 'boa'])
def test_condicao_exige_booleano(valor):
    with pytest.raises(TypeError):
        CondicoesAncoragem(valor)


def test_aderencia_obrigatoria():
    with pytest.raises(TypeError):
        CondicoesAncoragem()
    with pytest.raises(TypeError):
        calcular_ancoragem(Concreto(30), Aco(500), 16, 6.2, 8.04)


@pytest.mark.parametrize('campo,valor', [('concreto', 30), ('aco', 500), ('condicoes', True)])
def test_tipos_de_objetos(campo, valor):
    with pytest.raises(TypeError):
        calcular(**{campo: valor})


@pytest.mark.parametrize('aco', [Aco(0), Aco(-500), Aco(float('nan')), Aco(float('inf'))])
def test_aco_invalido(aco):
    with pytest.raises(ValueError):
        calcular(aco=aco)


@pytest.mark.parametrize('concreto', [Concreto(float('nan')), Concreto(float('inf')), Concreto(91)])
def test_concreto_fora_do_dominio(concreto):
    with pytest.raises(ValueError):
        calcular(concreto=concreto)


def test_reutiliza_concreto_acima_de_50_e_coeficientes_explicitos():
    r = calcular(concreto=Concreto(60), gamma_c=1.5, gamma_s=1.2)
    assert r.fctd_mpa == pytest.approx(0.7 * 2.12 * log(1 + 0.11 * 60) / 1.5)
    assert r.fyd_mpa == pytest.approx(500 / 1.2)


def test_objetos_imutaveis_e_api_publica():
    from concretopy import api
    from concretopy.verificacoes import calcular_ancoragem as funcao
    assert api.calcular_ancoragem is funcao is calcular_ancoragem
    assert api.ResultadoAncoragem is ResultadoAncoragem
    assert {'CondicoesAncoragem', 'ResultadoAncoragem', 'calcular_ancoragem'} <= set(api.__all__)
    with pytest.raises(FrozenInstanceError):
        CondicoesAncoragem(True).boa_aderencia = False
    with pytest.raises(FrozenInstanceError):
        calcular().lb_cm = 0


def test_regras_elementares_rejeitam_entradas_invalidas():
    with pytest.raises(TypeError):
        coeficiente_aderencia_eta2(1)
    with pytest.raises(TypeError):
        coeficiente_aderencia_eta3(True)
    with pytest.raises(ValueError):
        comprimento_minimo_ancoragem_cm(39, 16)
    with pytest.raises(TypeError):
        comprimento_minimo_ancoragem_cm('40', 16)
