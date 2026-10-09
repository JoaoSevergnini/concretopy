from dataclasses import FrozenInstanceError, asdict
import json
import pytest
from concretopy import (Concreto, Aco, CondicoesAncoragem,
    verificar_ancoragem_positiva_apoio, calcular_ancoragem)


def verificar(**kwargs):
    dados = dict(concreto=Concreto(50), aco=Aco(500), bitola_mm=25,
        as_calculada_cm2=4, as_efetiva_cm2=5,
        condicoes=CondicoesAncoragem(boa_aderencia=True),
        comprimento_disponivel_cm=50, gancho_valido=False)
    dados.update(kwargs)
    return verificar_ancoragem_positiva_apoio(**dados)


@pytest.mark.parametrize('gancho,alpha,necessario', [(False,1,50),(True,.7,35)])
def test_comprimentos_manuais(gancho,alpha,necessario):
    # C50, phi25: piso 25phi=62.5 cm governa lb; lb_min=10phi=25cm.
    r = verificar(gancho_valido=gancho)
    assert r.lb_cm == pytest.approx(62.5)
    assert r.lb_min_cm == 25
    assert r.alpha == alpha
    assert r.lb_nec_sem_min_cm == pytest.approx(necessario)
    assert r.lb_nec_cm == pytest.approx(necessario)
    assert r.atende


@pytest.mark.parametrize('area,variavel', [(4,62.5),(5,50),(2,125)])
def test_area_e_comprimento_separados(area,variavel):
    r = verificar(as_efetiva_cm2=area, comprimento_disponivel_cm=200)
    assert r.lb_nec_sem_min_cm == pytest.approx(variavel)
    assert r.comprimento_suficiente
    assert r.area_suficiente == (area >= 4)
    assert r.atende == (area >= 4)


@pytest.mark.parametrize('comprimento,atende', [(51,True),(50,True),(49,False)])
def test_fronteira_comprimento(comprimento,atende):
    assert verificar(comprimento_disponivel_cm=comprimento).atende is atende


def test_inverso_manual():
    # 62.5*4/25=10 cm2; adicional=10-5=5 cm2.
    r = verificar(comprimento_disponivel_cm=25)
    assert r.as_corr_matematica_cm2 == 10
    assert r.as_corr_cm2 == 10
    assert r.as_adicional_cm2 == 5
    assert not r.comprimento_menor_lb_min


def test_minimo_impede_correcao_somente_por_area():
    r = verificar(comprimento_disponivel_cm=10)
    assert r.comprimento_menor_lb_min
    assert r.as_corr_matematica_cm2 == 25
    assert r.as_corr_cm2 == 25
    assert r.as_adicional_cm2 == 20
    assert r.avisos and not r.atende
    corrigido = verificar(comprimento_disponivel_cm=10, as_efetiva_cm2=r.as_corr_cm2)
    assert corrigido.area_suficiente
    assert not corrigido.comprimento_suficiente
    assert not corrigido.atende
    assert corrigido.lb_nec_cm == 25


def test_correcao_nunca_menor_demanda_adicional_nunca_negativo():
    r = verificar(comprimento_disponivel_cm=100)
    assert r.as_corr_matematica_cm2 == 2.5
    assert r.as_corr_cm2 == 4
    assert r.as_adicional_cm2 == 0
    insuficiente = verificar(as_efetiva_cm2=2, comprimento_disponivel_cm=200)
    assert insuficiente.as_corr_cm2 == 4
    assert insuficiente.as_adicional_cm2 == 2


def test_comprimento_igual_minimo_valido():
    r = verificar(as_efetiva_cm2=100, comprimento_disponivel_cm=25)
    assert r.lb_nec_cm == 25
    assert not r.comprimento_menor_lb_min
    assert r.atende


@pytest.mark.parametrize('bitola', [10,16,25,32,40])
@pytest.mark.parametrize('boa', [True,False])
def test_reutilizacao_primitiva_e_aderencia(bitola,boa):
    c = CondicoesAncoragem(boa_aderencia=boa)
    r = verificar(bitola_mm=bitola, condicoes=c)
    base = calcular_ancoragem(Concreto(50), Aco(500), bitola, 4, 5,
        condicoes=c, comprimento_disponivel_cm=50)
    for nome in ('fbd_mpa','lb_cm','lb_min_cm','lb_nec_cm','atende','eta3'):
        assert getattr(r,nome) == getattr(base,nome)
    assert r.eta2 == (1 if boa else .7)
    assert r.eta3 == pytest.approx(1 if bitola <32 else (132-bitola)/100)
    assert r.lb_cm >= 25*bitola/10


@pytest.mark.parametrize('campo', ['bitola_mm','as_calculada_cm2','as_efetiva_cm2',
    'comprimento_disponivel_cm','gamma_c','gamma_s'])
@pytest.mark.parametrize('valor', [0,-1,float('nan'),float('inf'),True,'10'])
def test_entradas_invalidas(campo,valor):
    with pytest.raises((ValueError,TypeError)):
        verificar(**{campo:valor})


@pytest.mark.parametrize('gancho', [0,1,None,'sim'])
def test_gancho_exige_booleano(gancho):
    with pytest.raises(TypeError):
        verificar(gancho_valido=gancho)


@pytest.mark.parametrize('dados', [dict(concreto=30),dict(aco=500),
    dict(condicoes=True),dict(bitola_mm=132),dict(concreto=Concreto(91))])
def test_dominios_existentes(dados):
    with pytest.raises((ValueError,TypeError)):
        verificar(**dados)


def test_primitiva_legada_preserva_contrato():
    with pytest.raises(ValueError):
        calcular_ancoragem(Concreto(50),Aco(500),25,4,2,
            condicoes=CondicoesAncoragem(boa_aderencia=True))
    assert not calcular_ancoragem(Concreto(50),Aco(500),25,4,5,
        condicoes=CondicoesAncoragem(boa_aderencia=True),
        comprimento_disponivel_cm=0).atende
    assert not verificar(as_efetiva_cm2=2).area_suficiente


def test_resultado_imutavel_serializavel_e_api():
    from concretopy import api, ResultadoVerificacaoAncoragemApoio
    from concretopy.verificacoes import verificar_ancoragem_positiva_apoio as exportada
    assert api.verificar_ancoragem_positiva_apoio is exportada is verificar_ancoragem_positiva_apoio
    r = verificar()
    assert isinstance(r,ResultadoVerificacaoAncoragemApoio)
    with pytest.raises(FrozenInstanceError):
        r.atende = False
    assert json.loads(json.dumps(asdict(r),allow_nan=False))['atende']
