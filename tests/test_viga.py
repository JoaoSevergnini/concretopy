
from concretopy import Aco, Concreto, VigaRetangular

def test_dimensionamento_basico_viga():
    viga = VigaRetangular(20, 60, 3, Concreto(30), Aco(500))
    res_flex = viga.dimensionar_flexao(mk=1800)
    res_cort = viga.dimensionar_cortante(vk=120)
    assert res_flex.as_tracao > 0
    assert res_flex.dominio in (2, 3, 4)
    assert res_cort.asw_por_s > 0
    assert res_cort.vrd2 > res_cort.vc
