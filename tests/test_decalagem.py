from dataclasses import FrozenInstanceError, asdict
from math import isfinite, nextafter, inf

import pytest

from concretopy import Concreto, ResultadoDecalagemAl, calcular_al


def calcular(**kwargs):
    dados = dict(concreto=Concreto(40), b_cm=19, d_cm=67.5625,
                 vk_abs_kn=56.4, gamma_f=1.4)
    dados.update(kwargs)
    return calcular_al(**dados)


def caso_razao(razao):
    vc0 = calcular().vc0_kn
    return calcular(vk_abs_kn=razao * vc0, gamma_f=1.0)


@pytest.mark.parametrize('razao,base_relativa,final_relativo,branch', [
    (0, 1, 1, 'vsd_le_vc0'),
    (0.5, 1, 1, 'vsd_le_vc0'),
    (1, 1, 1, 'vsd_le_vc0'),
    (1.5, 1.5, 1, 'vsd_gt_vc0'),
    (2, 1, 1, 'vsd_gt_vc0'),
    (2.5, 5/6, 5/6, 'vsd_gt_vc0'),
    (3, 0.75, 0.75, 'vsd_gt_vc0'),
])
def test_ramos_e_limites_matematicos(razao, base_relativa, final_relativo, branch):
    r = caso_razao(razao)
    assert r.branch == branch
    assert r.al_base_cm == pytest.approx(base_relativa * r.d_cm)
    assert r.al_cm == pytest.approx(final_relativo * r.d_cm)
    assert r.al_min_cm == 0.5 * r.d_cm
    assert r.al_max_cm == r.d_cm
    assert r.al_min_cm <= r.al_cm <= r.al_max_cm


def test_igualdade_nao_divide_por_zero():
    vc0 = calcular().vc0_kn
    r = calcular(vk_abs_kn=vc0, gamma_f=1)
    assert r.vsd_kn == r.vc0_kn
    assert r.al_base_cm == r.al_cm == r.d_cm


def test_imediatamente_acima_do_limite_preserva_base():
    vc0 = calcular().vc0_kn
    r = calcular(vk_abs_kn=nextafter(vc0, inf), gamma_f=1)
    assert r.branch == 'vsd_gt_vc0'
    assert isfinite(r.al_base_cm)
    assert r.al_base_cm > 1e12 * r.d_cm
    assert r.al_cm == r.d_cm


def test_cortante_elevado_tende_ao_piso_por_cima():
    r = caso_razao(1e8)
    assert r.al_cm > 0.5 * r.d_cm
    assert r.al_cm == pytest.approx(0.5 * r.d_cm, rel=2e-8)
    assert r.al_cm == r.al_base_cm


@pytest.mark.parametrize('razao', [0, 0.1, 1, 1.001, 1.9, 2, 3, 10, 1e6, 1e16, 1e100])
def test_invariante_limites(razao):
    r = caso_razao(razao)
    assert 0.5 * r.d_cm <= r.al_cm <= r.d_cm


def test_vsd_grande_sem_overflow_no_produto_intermediario():
    r = calcular(vk_abs_kn=1e307, gamma_f=1)
    assert isfinite(r.al_base_cm)
    assert r.al_cm == pytest.approx(0.5 * r.d_cm)


def test_regressao_documental_excel():
    # Exclusivamente neste golden: aproximacao documental 1 tf = 10 kN.
    r = calcular(vk_abs_kn=5.64 * 10)
    assert r.vsd_kn == pytest.approx(7.896 * 10, abs=1e-12)
    assert r.vc0_kn == pytest.approx(13.512690073160 * 10, abs=1e-10)
    assert r.al_base_cm == r.al_cm == 67.5625
    assert r.branch == 'vsd_le_vc0'


def test_conversao_dimensional_mpa_para_kn_cm2():
    r = calcular(concreto=Concreto(40), b_cm=20, d_cm=50, gamma_c=1.5)
    fctd = 0.7 * 0.3 * 40 ** (2/3) / 1.5
    assert r.fctd_mpa == pytest.approx(fctd)
    assert r.vc0_kn == pytest.approx(0.6 * fctd * 0.1 * 20 * 50)
    assert r.gamma_c == 1.5


def test_d_explicito_altera_vc0_e_limites_juntos():
    a = calcular(d_cm=30, vk_abs_kn=0)
    b = calcular(d_cm=60, vk_abs_kn=0)
    assert b.vc0_kn == pytest.approx(2 * a.vc0_kn)
    assert b.al_cm == 2 * a.al_cm
    with pytest.raises(TypeError):
        calcular_al(concreto=Concreto(40), b_cm=19, vk_abs_kn=0)


def test_concreto_alta_resistencia_reutilizado():
    c = Concreto(60)
    r = calcular(concreto=c, gamma_c=1.5)
    assert r.fctd_mpa == c.fctd(1.5)


@pytest.mark.parametrize('campo', ['b_cm', 'd_cm', 'gamma_f', 'gamma_c'])
@pytest.mark.parametrize('valor', [0, -1, float('nan'), float('inf'), -float('inf')])
def test_positivos_invalidos(campo, valor):
    with pytest.raises(ValueError):
        calcular(**{campo: valor})


@pytest.mark.parametrize('valor', [-1, float('nan'), float('inf'), -float('inf')])
def test_vk_invalido_inclusive_negativo(valor):
    with pytest.raises(ValueError, match='vk_abs_kn'):
        calcular(vk_abs_kn=valor)


@pytest.mark.parametrize('campo', ['b_cm', 'd_cm', 'gamma_f', 'gamma_c', 'vk_abs_kn'])
@pytest.mark.parametrize('valor', [True, '10', None])
def test_tipos_invalidos(campo, valor):
    with pytest.raises(TypeError):
        calcular(**{campo: valor})


@pytest.mark.parametrize('concreto', [Concreto(91), Concreto(float('nan')), Concreto(float('inf'))])
def test_material_fora_do_dominio(concreto):
    with pytest.raises(ValueError):
        calcular(concreto=concreto)


def test_material_tipo_invalido():
    with pytest.raises(TypeError):
        calcular(concreto=40)


@pytest.mark.parametrize('kwargs', [
    dict(vk_abs_kn=1e308, gamma_f=10),
    dict(b_cm=1e308, d_cm=1e308),
    dict(gamma_c=5e-324),
])
def test_resultados_nao_finitos_rejeitados(kwargs):
    with pytest.raises(ValueError):
        calcular(**kwargs)


def test_resultado_auditavel_imutavel_e_api():
    from concretopy import api
    from concretopy.verificacoes import calcular_al as exportada
    r = calcular()
    assert isinstance(r, ResultadoDecalagemAl)
    assert api.calcular_al is exportada is calcular_al
    assert api.ResultadoDecalagemAl is ResultadoDecalagemAl
    assert {'calcular_al', 'ResultadoDecalagemAl'} <= set(api.__all__)
    assert asdict(r)['vk_abs_kn'] == 56.4
    assert r.gamma_f == 1.4
    assert r.b_cm == 19
    with pytest.raises(FrozenInstanceError):
        r.al_cm = 1
    assert r == calcular()


def test_ancoragem_permanece_independente():
    from concretopy import Aco, CondicoesAncoragem, calcular_ancoragem
    kwargs = dict(concreto=Concreto(30), aco=Aco(500), bitola_mm=16,
                  as_calculada_cm2=6.2, as_efetiva_cm2=8.04,
                  condicoes=CondicoesAncoragem(True), comprimento_disponivel_cm=50)
    antes = calcular_ancoragem(**kwargs)
    calcular(vk_abs_kn=1e6)
    depois = calcular_ancoragem(**kwargs)
    assert antes == depois
    assert depois.lb_cm == pytest.approx(53.37168018815003)
    assert depois.atende is (50 >= depois.lb_nec_cm)
    assert 'al_cm' not in asdict(depois)
