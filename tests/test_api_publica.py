from concretopy import (
    Aco,
    CalculadoraReforcoFuros,
    Concreto,
    ResultadoReforcoFuro,
    VigaRetangular,
)
from concretopy.api import __all__ as api_all


def test_api_publica_exporta_nomes_essenciais():
    assert 'Concreto' in api_all
    assert 'Aco' in api_all
    assert 'VigaRetangular' in api_all
    assert 'CalculadoraReforcoFuros' in api_all
    assert 'ResultadoReforcoFuro' in api_all


def test_imports_top_level_basicos():
    conc = Concreto(30)
    aco = Aco(500)
    viga = VigaRetangular(bw=20, h=50, cobrimento=3, concreto=conc, aco=aco)
    assert viga.bw == 20
    assert isinstance(ResultadoReforcoFuro.__name__, str)
    assert CalculadoraReforcoFuros is not None
