from dataclasses import FrozenInstanceError, asdict
from math import pi, sqrt
import json

import pytest

from concretopy import (
    Aco, Barra, CamadaArmaduraLongitudinal, Concreto, SecaoRetangular,
    ResultadoArmaduraApoio, calcular_armadura_positiva_apoio,
    verificar_flexao_viga_retangular,
)
from concretopy.verificacoes.flexao import dimensionar_flexao_viga_retangular


# Referencia manual: C20, gammas=1, b=20, d=45, As=2.72 cm2.
# fcd=20 MPa, fyd=500 MPa=50 kN/cm2; bloco: 0.85*2*20=34 kN/cm.
# T=136 kN, y=4 cm, x=5 cm; z de engenharia=42.5 cm.
# M de dimensionamento para As=2.72: 136*(45-2)=5848 kN.cm.
# Bitola nao comercial intencional para criar um equilibrio manual exato.
PHI = sqrt(1088 / pi)


def calcular(**kwargs):
    dados = dict(secao=SecaoRetangular(20, 50, 3), concreto=Concreto(20),
                 aco=Aco(500), camadas_apoio=(CamadaArmaduraLongitudinal(1, Barra(PHI), 45),),
                 tipo_apoio='extremo', mk_apoio_kncm=0,
                 vk_apoio_kn=10,
                 mk_positivo_max_vao_kncm=5848, mk_negativo_apoio_kncm=0,
                 d_vao_cm=45, gamma_f=1, gamma_c=1, gamma_s=1)
    dados.update(kwargs)
    return calcular_armadura_positiva_apoio(**dados)


def test_referencia_manual_geometria_e_condicao_c():
    r = calcular()
    assert r.d_cm == 45
    assert r.x_cm == pytest.approx(5, abs=1e-12)
    assert r.z_cm == pytest.approx(42.5, abs=1e-12)
    assert r.condicao_c.as_vao_cm2 == pytest.approx(2.72)
    assert r.condicao_c.as_cm2 == pytest.approx(2.72 / 3)
    assert r.condicoes_governantes == ('C',)


def test_a_inaplicavel_e_b_manual():
    r = calcular(nd_tracao_kn=40)
    assert not r.condicao_a.aplicavel
    assert r.condicao_a.as_cm2 is None
    assert r.md_apoio_kncm == 0
    assert r.condicao_b.decalagem.vk_abs_kn == 10
    assert r.condicao_b.fsd_kn == pytest.approx(50)
    assert r.condicao_b.as_cm2 == pytest.approx(1)
    assert r.condicoes_governantes == ('B',)


def test_par_momento_cortante_manual():
    r = calcular(mk_apoio_kncm=4250, vk_apoio_kn=10)
    assert r.condicao_a.aplicavel
    assert r.mk_apoio_kncm == r.md_apoio_kncm == 4250
    assert r.vk_apoio_kn == r.vd_apoio_kn == 10
    assert r.condicao_b.decalagem.vk_abs_kn == 10
    assert r.condicao_b.fsd_kn == pytest.approx(110)
    assert r.condicao_b.as_cm2 == pytest.approx(2.2)
    assert r.condicoes_governantes == ('B',)




def test_chamadas_independentes_com_cortantes_distintos():
    vc0 = calcular().condicao_b.decalagem.vc0_kn
    maior = calcular(mk_apoio_kncm=4250, vk_apoio_kn=3*vc0)
    menor = calcular(mk_apoio_kncm=4250, vk_apoio_kn=vc0/2)
    assert maior.condicao_b.decalagem.al_cm == pytest.approx(33.75)
    assert menor.condicao_b.decalagem.al_cm == 45
    assert maior.condicao_b.decalagem is not menor.condicao_b.decalagem


@pytest.mark.parametrize('negativo,fracao,criterio', [
    (0, 1/3, 'C1'), (-1000, 1/3, 'C1'), (-2924, 1/3, 'C1'),
    (-2924.000001, 1/4, 'C2'), (-5848, 1/4, 'C2'),
])
def test_condicao_c_fronteira_e_momento_nulo(negativo, fracao, criterio):
    r = calcular(mk_negativo_apoio_kncm=negativo)
    c = r.condicao_c
    assert c.fracao == fracao
    assert c.criterio == criterio
    assert c.razao_momentos == pytest.approx(abs(negativo) / 5848)
    assert c.as_cm2 == pytest.approx(2.72 * fracao)


def test_c_negativa_coexiste_com_a_positiva():
    r = calcular(mk_apoio_kncm=100, mk_negativo_apoio_kncm=-5848)
    assert r.condicao_a.aplicavel
    assert r.condicao_c.criterio == 'C2'
    assert r.condicao_c.as_cm2 == pytest.approx(0.68)


def test_a_governa_e_preserva_minimo_do_dimensionador():
    r = calcular(mk_apoio_kncm=100, vk_apoio_kn=0)
    assert r.condicao_a.as_cm2 == pytest.approx(1.5)  # 0.15% * 20*50
    assert r.condicoes_governantes == ('A',)
    assert r.as_necessaria_cm2 == pytest.approx(1.5)


def test_a_dimensionamento_manual_e_apoio_intermediario():
    r = calcular(tipo_apoio='intermediario', mk_apoio_kncm=5848)
    assert r.condicao_a.as_cm2 == pytest.approx(2.72)
    assert not r.condicao_b.aplicavel
    assert r.condicao_b.decalagem is None
    assert r.condicao_b.fsd_kn is None
    assert r.condicao_b.as_cm2 is None
    assert r.condicoes_governantes == ('A',)


def test_intermediario_sem_momento_positivo_governa_c():
    r = calcular(tipo_apoio='intermediario')
    assert r.condicoes_governantes == ('C',)
    assert r.as_necessaria_cm2 == r.condicao_c.as_cm2


def test_multiplas_camadas_centroides_e_x_reutilizados():
    # Mesma bitola: pesos 3 e 1; (3*45 + 1*40)/4 = 43.75 cm.
    camadas = [CamadaArmaduraLongitudinal(3, Barra(10), 45),
               CamadaArmaduraLongitudinal(1, Barra(10), 40)]
    r = calcular(camadas_apoio=camadas)
    original = verificar_flexao_viga_retangular(SecaoRetangular(20,50,3),
                Concreto(20), Aco(500), camadas, gamma_c=1, gamma_s=1)
    assert r.d_cm == pytest.approx(43.75)
    assert r.d_por_camada_cm == (45, 40)
    assert r.x_cm == original.linha_neutra_cm
    assert r.as_por_camada_cm2 == original.as_por_camada_cm2
    assert r.z_cm == pytest.approx(43.75 - original.linha_neutra_cm/2)
    assert r.condicao_b.decalagem.d_cm == r.d_cm


def test_camadas_com_d_omitido_usam_rotina_existente():
    cs = [CamadaArmaduraLongitudinal(2, Barra(10)), CamadaArmaduraLongitudinal(1, Barra(10))]
    r = calcular(camadas_apoio=cs)
    assert r.d_por_camada_cm == (46, 43)
    assert r.d_cm == 45
    assert any('omitidas' in aviso for aviso in r.avisos)


def test_secao_e_d_do_vao_independentes_do_apoio():
    # C20, b=30,d=55, x=5 -> T=204kN, M=204*(55-2)=10812, As=4.08.
    r = calcular(secao_vao=SecaoRetangular(30,60,3), d_vao_cm=55,
                 mk_positivo_max_vao_kncm=10812)
    assert r.d_cm == 45
    assert r.condicao_c.d_vao_cm == 55
    assert r.condicao_c.as_vao_cm2 == pytest.approx(4.08)
    assert r.condicao_c.as_cm2 == pytest.approx(1.36)


def test_nd_ja_de_calculo_sem_majoracao_repetida():
    r = calcular(vk_apoio_kn=0, gamma_f=1.4, nd_tracao_kn=50)
    b = r.condicao_b
    assert b.fsd_kn == 50
    assert b.as_cm2 == 1


def test_coeficientes_customizados_e_resistencias():
    r = calcular(gamma_f=1.5, gamma_c=1.4, gamma_s=1.15)
    b = r.condicao_b
    assert b.decalagem.vsd_kn == 15
    assert b.decalagem.gamma_c == 1.4
    assert b.as_cm2 == pytest.approx(15 / (500/1.15*0.1))
    assert r.fyd_mpa == pytest.approx(500/1.15)


@pytest.mark.parametrize('campo', ['mk_apoio_kncm', 'vk_apoio_kn',
    'nd_tracao_kn', 'mk_positivo_max_vao_kncm', 'd_vao_cm',
    'gamma_f', 'gamma_c', 'gamma_s'])
@pytest.mark.parametrize('valor', [-1, float('nan'), float('inf'), True, '10'])
def test_entradas_invalidas(campo, valor):
    with pytest.raises((TypeError, ValueError)):
        calcular(**{campo: valor})


@pytest.mark.parametrize('campo', ['mk_positivo_max_vao_kncm', 'd_vao_cm', 'gamma_f', 'gamma_c', 'gamma_s'])
def test_zero_invalido(campo):
    with pytest.raises(ValueError):
        calcular(**{campo: 0})


def test_momento_negativo_com_sinal_errado():
    with pytest.raises(ValueError, match='<= 0'):
        calcular(mk_negativo_apoio_kncm=1)


@pytest.mark.parametrize('valor', ['interno', '', None, True])
def test_tipo_apoio_invalido(valor):
    with pytest.raises((TypeError, ValueError)):
        calcular(tipo_apoio=valor)


@pytest.mark.parametrize('campo,valor', [('concreto', 30), ('aco', 500), ('secao', 20),
    ('secao_vao', 30), ('concreto', Concreto(91)), ('concreto', Concreto(float('nan'))),
    ('aco', Aco(-1)), ('aco', Aco(es=0)), ('secao_vao', SecaoRetangular(float('nan'),60,3))])
def test_materiais_e_secoes_invalidos(campo, valor):
    with pytest.raises((TypeError, ValueError)):
        calcular(**{campo: valor})


@pytest.mark.parametrize('camadas', [[], [CamadaArmaduraLongitudinal(1,Barra(16),49)],
    [CamadaArmaduraLongitudinal(1,Barra(16),1)],
    [CamadaArmaduraLongitudinal(2,Barra(16),45),CamadaArmaduraLongitudinal(1,Barra(16),45)]])
def test_geometria_invalida(camadas):
    with pytest.raises(ValueError):
        calcular(camadas_apoio=camadas)


def test_x_candidato_nao_pode_ser_usado_quando_hipoteses_invalidas():
    cs = [CamadaArmaduraLongitudinal(4, Barra(20), 45),
          CamadaArmaduraLongitudinal(2, Barra(12.5), 8)]
    with pytest.raises(ValueError, match='Hipoteses'):
        calcular(camadas_apoio=cs)


def test_geometria_com_z_nao_positivo_e_rejeitada_antes_do_calculo():
    # Aco excessivo torna x > 2d; a analise existente rejeita o estado fisico.
    cs = [CamadaArmaduraLongitudinal(8, Barra(32), 30)]
    with pytest.raises(ValueError, match='Hipoteses'):
        calcular(secao=SecaoRetangular(40,50,3), camadas_apoio=cs)


def test_compressao_exige_posicao_e_preserva_resultado():
    with pytest.raises(ValueError, match='d_linha_vao_cm'):
        calcular(mk_positivo_max_vao_kncm=30000)
    r = calcular(mk_positivo_max_vao_kncm=30000, d_linha_vao_cm=5)
    assert r.condicao_c.dimensionamento_vao.as_compressao > 0
    assert any('comprimida' in s for s in r.avisos)


def test_compressao_no_apoio_exige_posicao():
    with pytest.raises(ValueError, match='d_linha_apoio_cm'):
        calcular(mk_apoio_kncm=30000)
    r = calcular(mk_apoio_kncm=30000, d_linha_apoio_cm=5)
    assert r.condicao_a.dimensionamento.as_compressao > 0


def test_d_linha_incompativel_rejeitado():
    with pytest.raises(ValueError):
        calcular(d_linha_vao_cm=46)
    with pytest.raises(ValueError, match='comprimida'):
        calcular(mk_positivo_max_vao_kncm=30000, d_linha_vao_cm=30)


def test_d_vao_fora_da_secao():
    with pytest.raises(ValueError):
        calcular(d_vao_cm=51)


def test_dimensionador_legado_preservado_e_d_explicito():
    s = SecaoRetangular(20,50,3)
    a = dimensionar_flexao_viga_retangular(s,Concreto(20),Aco(500),5000)
    b = dimensionar_flexao_viga_retangular(s,Concreto(20),Aco(500),5000,
                                          d_cm=s.d(), d_linha_cm=s.d_linha())
    assert a == b
    manual = dimensionar_flexao_viga_retangular(s,Concreto(20),Aco(500),5848,
                                               gamma_f=1,gamma_c=1,gamma_s=1,d_cm=45)
    assert manual.as_tracao == pytest.approx(2.72)
    assert manual.linha_neutra == pytest.approx(5)


def test_api_serializacao_imutabilidade_sem_aprovacao():
    from concretopy import api
    from concretopy.verificacoes import calcular_armadura_positiva_apoio as exportada
    r = calcular()
    assert api.calcular_armadura_positiva_apoio is exportada is calcular_armadura_positiva_apoio
    assert isinstance(r, ResultadoArmaduraApoio)
    assert r == calcular()
    with pytest.raises(FrozenInstanceError):
        r.as_necessaria_cm2 = 0
    with pytest.raises(FrozenInstanceError):
        r.condicao_b.as_cm2 = 0
    data = json.loads(json.dumps(asdict(r), allow_nan=False))
    assert data['condicoes_governantes'] == ['C']
    assert not hasattr(r, 'atende')
    assert not hasattr(r, 'comprimento_disponivel_cm')


def test_nao_compara_armadura_detalhada_com_demanda():
    r = calcular(vk_apoio_kn=1000)
    assert r.as_necessaria_cm2 > sum(r.as_por_camada_cm2)
    assert not hasattr(r, 'atende')





def test_empate_global_a_b_sem_escolha_arbitraria():
    # A minimo=1.5; Fsd=425/42.5+65=75 kN; As_b=1.5.
    r = calcular(mk_apoio_kncm=425, vk_apoio_kn=65)
    assert r.condicoes_governantes == ('A', 'B')


@pytest.mark.parametrize('campo', ['mk_apoio_kncm', 'mk_positivo_max_vao_kncm'])
def test_momento_majorado_nao_finito_rejeitado(campo):
    with pytest.raises(ValueError):
        calcular(**{campo: 1e308}, gamma_f=10)


@pytest.mark.parametrize('valor', [0, -1, float('nan'), True])
def test_altura_explicita_invalida_no_dimensionador(valor):
    with pytest.raises((TypeError, ValueError)):
        dimensionar_flexao_viga_retangular(SecaoRetangular(20,50,3), Concreto(20),
                                         Aco(500), 5848, d_cm=valor)


def test_api_tem_um_unico_par_sem_selecao_interna():
    from inspect import signature
    nomes = signature(calcular_armadura_positiva_apoio).parameters
    assert 'mk_apoio_kncm' in nomes and 'vk_apoio_kn' in nomes
    assert 'vk_max_abs_apoio_kn' not in nomes
    assert 'vk_min_abs_apoio_kn' not in nomes
    assert not hasattr(calcular().condicao_b, 'estados')
    with pytest.raises(TypeError):
        calcular(vk_max_abs_apoio_kn=10)


def test_c_incorpora_armadura_minima():
    r = calcular(mk_positivo_max_vao_kncm=100)
    assert r.condicao_c.as_vao_cm2 == pytest.approx(1.5)
    assert r.condicao_c.as_cm2 == pytest.approx(0.5)
