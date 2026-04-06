import math

from concretopy import Aco, BarraPosicionada, Concreto, PilarPoligonal


def _pilar_retangular_simetrico() -> PilarPoligonal:
    contorno = [[0, 0], [20, 0], [20, 50], [0, 50]]
    barras = [
        BarraPosicionada(3, 3, 12.5),
        BarraPosicionada(17, 3, 12.5),
        BarraPosicionada(17, 47, 12.5),
        BarraPosicionada(3, 47, 12.5),
    ]
    return PilarPoligonal(
        contorno=contorno,
        barras=barras,
        concreto=Concreto(30),
        aco=Aco(500),
    )


def test_flexocompressao_regressao_casos_estaveis():
    pilar = _pilar_retangular_simetrico()
    casos = [
        (0.0, 0.0, 0.0, 4470.42759758417, 3.1875),
        (0.0, 30.0, -776.2895868696805, 4329.518018706714, 8.061817116119819),
        (200.0, 45.0, -1403.837253527912, 8102.562917608206, 14.539883188148384),
        (500.0, 90.0, -4952.777776957291, 0.0, 7.075000000000001),
        (1000.0, 180.0, 0.0, -14426.52808425236, 34.3125),
    ]

    for nd, angulo, mxd_ref, myd_ref, x_ref in casos:
        res = pilar.momentos_resistentes(nd=nd, inclinacao_linha_neutra_graus=angulo)
        assert res.convergiu is True
        assert math.isclose(res.mxd_resistente, mxd_ref, rel_tol=0, abs_tol=1e-9)
        assert math.isclose(res.myd_resistente, myd_ref, rel_tol=0, abs_tol=1e-9)
        assert math.isclose(res.linha_neutra, x_ref, rel_tol=0, abs_tol=1e-9)
        assert abs(res.nd_resistente - nd) <= 20.0


def test_flexocompressao_simetria_0_180_graus():
    pilar = _pilar_retangular_simetrico()
    res0 = pilar.momentos_resistentes(nd=200, inclinacao_linha_neutra_graus=0)
    res180 = pilar.momentos_resistentes(nd=200, inclinacao_linha_neutra_graus=180)

    assert math.isclose(res0.mxd_resistente, res180.mxd_resistente, rel_tol=0, abs_tol=1e-9)
    assert math.isclose(res0.myd_resistente, -res180.myd_resistente, rel_tol=0, abs_tol=1e-9)


def test_flexocompressao_my_aproxima_zero_a_90_graus():
    pilar = _pilar_retangular_simetrico()
    res = pilar.momentos_resistentes(nd=500, inclinacao_linha_neutra_graus=90)
    assert abs(res.myd_resistente) < 1e-6


def test_flexocompressao_angulo_60_agora_resolve_sem_excecao():
    pilar = _pilar_retangular_simetrico()
    res = pilar.momentos_resistentes(nd=0, inclinacao_linha_neutra_graus=60)

    assert res.convergiu is True
    assert abs(res.residual_equilibrio) <= 20.0
    assert res.linha_neutra > 0
