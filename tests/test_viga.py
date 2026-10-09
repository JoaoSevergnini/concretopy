
import pytest

from concretopy import Aco, Concreto, VigaRetangular, calcular_al

def test_dimensionamento_basico_viga():
    viga = VigaRetangular(20, 60, 3, Concreto(30), Aco(500))
    res_flex = viga.dimensionar_flexao(mk=1800)
    res_cort = viga.dimensionar_cortante(vk=120)
    assert res_flex.as_tracao > 0
    assert res_flex.dominio in (2, 3, 4)
    assert res_cort.asw_por_s > 0
    assert res_cort.vrd2 > res_cort.vc



@pytest.mark.parametrize('vk,gamma_f,gamma_c', [(0, 1.4, 1.4), (56.4, 1.4, 1.4), (400, 1.5, 1.6)])
def test_decalagem_viga_equivale_a_primitiva(vk, gamma_f, gamma_c):
    viga = VigaRetangular(19, 72, 2.5, Concreto(40), Aco(500))
    r = viga.calcular_decalagem(vk_abs_kn=vk, d_cm=67.5625,
                               gamma_f=gamma_f, gamma_c=gamma_c)
    esperado = calcular_al(concreto=viga.concreto, b_cm=19, d_cm=67.5625,
                           vk_abs_kn=vk, gamma_f=gamma_f, gamma_c=gamma_c)
    assert r == esperado
    assert r.d_cm != viga.secao.d()  # Preserva d explicito, sem bitola padrao.


def test_decalagem_viga_regressao_documental():
    viga = VigaRetangular(19, 72, 2.5, Concreto(40), Aco(500))
    r = viga.calcular_decalagem(vk_abs_kn=56.4, d_cm=67.5625)
    assert r.al_base_cm == r.al_cm == 67.5625
    assert r.vc0_kn == pytest.approx(135.12690073160)


def test_decalagem_viga_exige_d():
    viga = VigaRetangular(19, 72, 2.5, Concreto(40), Aco(500))
    with pytest.raises(TypeError):
        viga.calcular_decalagem(vk_abs_kn=56.4)


@pytest.mark.parametrize('kwargs,erro', [
    ({'vk_abs_kn': -1, 'd_cm': 60}, ValueError),
    ({'vk_abs_kn': 0, 'd_cm': 0}, ValueError),
    ({'vk_abs_kn': True, 'd_cm': 60}, TypeError),
    ({'vk_abs_kn': 0, 'd_cm': 60, 'gamma_c': 0}, ValueError),
])
def test_decalagem_viga_preserva_validacoes(kwargs, erro):
    viga = VigaRetangular(19, 72, 2.5, Concreto(40), Aco(500))
    with pytest.raises(erro):
        viga.calcular_decalagem(**kwargs)
