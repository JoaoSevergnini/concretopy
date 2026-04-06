from concretopy import CalculadoraReforcoFuros
from concretopy.exceptions import FuroEmZonaComprimida, GeometriaInvalidaFuro


def _criar_calculadora_kn():
    return CalculadoraReforcoFuros(
        h=60,
        b=20,
        h_furo=10,
        b_furo=12,
        fck=30,
        C=15,
        Mk=18000,
        Vk=120,
        cobrimento=3,
        armadura_superior=[(2, 12.5)],
        armadura_inferior=[(2, 12.5)],
    )


def test_calculadora_furos_basico_em_kn():
    calc = _criar_calculadora_kn()
    resultado = calc.calcular_reforco()

    assert resultado.as_suspensao > 0
    assert resultado.armadura_longitudinal is not None or 'Reforço longitudinal não encontrado.' in resultado.memorial
    assert resultado.configuracao_armadura_suspensao
    assert "Solicitações" in resultado.memorial


def test_calculadora_furos_from_tf_tfm_converte_corretamente():
    calc = CalculadoraReforcoFuros.from_tf_tfm(
        h=60,
        b=20,
        h_furo=10,
        b_furo=12,
        fck=30,
        C=15,
        Mk_tfm=18.0,
        Vk_tf=12.0,
        cobrimento=3,
        armadura_superior=[(2, 12.5)],
        armadura_inferior=[(2, 12.5)],
    )

    assert calc.Mk == 18000.0
    assert calc.Vk == 120.0


def test_calculadora_furos_geometria_invalida():
    try:
        CalculadoraReforcoFuros(
            h=20,
            b=20,
            h_furo=25,
            b_furo=12,
            fck=30,
            C=5,
            Mk=10000,
            Vk=80,
            cobrimento=3,
            armadura_superior=[(2, 12.5)],
            armadura_inferior=[(2, 12.5)],
        )
    except GeometriaInvalidaFuro:
        pass
    else:
        raise AssertionError("Era esperado erro de geometria inválida.")


def test_verificar_furo_pode_identificar_zona_comprimida():
    calc = _criar_calculadora_kn()
    try:
        calc.verificar_furo()
    except FuroEmZonaComprimida:
        pass
    else:
        raise AssertionError("Era esperado erro de furo em zona comprimida para este caso base.")
