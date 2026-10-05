"""Referências: tests/references/flexure_resistance.json e relatório de implementação.

Valores golden reproduzidos matematicamente antes da rotina, com Decimal de
50 dígitos. Nenhum teste depende de Excel, macros ou caches do XLSM.
"""
import json
import math
from dataclasses import asdict
from pathlib import Path

import pytest

from concretopy.armaduras import Barra, BarraPosicionada, CamadaArmaduraLongitudinal
from concretopy.materiais import Aco, Concreto
from concretopy.secoes import SecaoRetangular, SecaoPoligonalArmada
from concretopy.verificacoes.flexao import verificar_flexao_viga_retangular
from concretopy.verificacoes.flexo_compressao import CalculadoraFlexoCompressao


REFERENCIAS = json.loads((Path(__file__).parent / "references/flexure_resistance.json").read_text(encoding="utf-8"))


def camada(n, phi, d):
    return CamadaArmaduraLongitudinal(n, Barra(phi), d)


def verificar(camadas=None, *, secao=None, concreto=None, aco=None, **kwargs):
    return verificar_flexao_viga_retangular(
        secao or SecaoRetangular(20, 50, 3), concreto or Concreto(30),
        aco or Aco(), [camada(2, 16, 45)] if camadas is None else camadas, **kwargs,
    )


@pytest.mark.parametrize("caso", REFERENCIAS["casos"], ids=lambda caso: caso["id"])
def test_golden_rastreavel(caso):
    resultado = verificar_flexao_viga_retangular(
        SecaoRetangular(**caso["secao"]), Concreto(caso["fck"]),
        Aco(REFERENCIAS["fyk"], REFERENCIAS["es"]),
        [camada(c["numero_barras"], c["diametro_mm"], c["d_cm"]) for c in caso["camadas"]],
        gamma_c=REFERENCIAS["gamma_c"], gamma_s=REFERENCIAS["gamma_s"],
        gamma_f=REFERENCIAS["gamma_f"],
    )
    for nome, valor in caso["esperado"].items():
        obtido = getattr(resultado, nome)
        if valor is None:
            assert obtido is None
        else:
            assert obtido == pytest.approx(valor, rel=REFERENCIAS["tolerancia_relativa"], abs=REFERENCIAS["tolerancia_absoluta"])
    assert resultado.d_por_camada_cm == tuple(c["d_cm"] for c in caso["camadas"])
    assert resultado.hipoteses_validas is caso["hipoteses_validas"]
    assert resultado.ductilidade_atendida is caso["ductilidade_atendida"]
    if not resultado.hipoteses_validas or resultado.ductilidade_atendida is False:
        assert resultado.avisos


def test_resistencia_independe_do_minimo_e_da_transformacao_caracteristica():
    cs = [camada(1, 5, 45)]
    base = verificar(cs)
    minimo = verificar(cs, verificar_armadura_minima=True, gamma_f=1.4)
    assert minimo.mrd_kncm == base.mrd_kncm
    assert minimo.as_total_cm2 == base.as_total_cm2
    assert minimo.as_min_cm2 == pytest.approx(1.5)
    assert minimo.armadura_minima_atendida is False
    assert minimo.hipoteses_validas is True
    assert base.armadura_minima_atendida is None
    assert base.mk_equivalente_kncm is None
    assert minimo.mk_equivalente_kncm == pytest.approx(base.mrd_kncm / 1.4)
    assert minimo.avisos


@pytest.mark.parametrize("fck", [55, 30.5])
def test_minimo_sem_tabela_nao_trunca_fck_nem_impede_resistencia(fck):
    r = verificar(concreto=Concreto(fck), verificar_armadura_minima=True)
    assert r.hipoteses_validas
    assert r.mrd_kncm is not None
    assert r.armadura_minima_atendida is None
    assert r.as_min_cm2 is None
    assert any("tabela" in aviso for aviso in r.avisos)


def test_minimo_atendido_separado_da_capacidade():
    r = verificar(verificar_armadura_minima=True)
    assert r.armadura_minima_atendida is True
    assert r.as_total_cm2 > r.as_min_cm2


def test_nao_trunca_x_quando_ductilidade_falha():
    caso = next(c for c in REFERENCIAS["casos"] if c["id"] == "E_acima_limite")
    d = caso["camadas"][0]["d_cm"]
    r = verificar([camada(4, 20, d)])
    assert r.hipoteses_validas
    assert r.ductilidade_atendida is False
    assert r.linha_neutra_cm > .45 * d
    momento_com_truncamento = r.as_total_cm2 * r.parametros["fyd"] * .1 * (d - .4 * .45 * d)
    assert r.mrd_kncm < momento_com_truncamento


def test_escoamento_por_camada_nao_pelo_centroide():
    r = verificar([camada(2, 20, 55), camada(2, 12.5, 12)], secao=SecaoRetangular(30, 60, 3))
    assert r.x_sobre_d < r.limite_x_sobre_d
    assert r.camadas_escoadas == (True, False)
    assert r.hipoteses_validas is False
    assert r.ductilidade_atendida is None
    assert r.mrd_kncm is None
    assert any("Camada 2" in aviso for aviso in r.avisos)


def test_camada_na_zona_comprimida_retorna_diagnostico():
    r = verificar([camada(4, 20, 45), camada(2, 12.5, 8)])
    assert r.linha_neutra_cm >= 8
    assert r.hipoteses_validas is False
    assert r.deformacoes_aco is None
    assert r.mrd_kncm is None
    assert r.mk_equivalente_kncm is None
    assert any("tracionadas" in aviso for aviso in r.avisos)


def test_linha_neutra_fora_da_secao_nao_retorna_capacidade():
    r = verificar([camada(8, 25, 45)], secao=SecaoRetangular(30, 50, 3), concreto=Concreto(20))
    assert r.linha_neutra_cm > 50
    assert r.hipoteses_validas is False
    assert r.ductilidade_atendida is None
    assert r.mrd_kncm is None


def test_concreto_alta_resistencia_reutiliza_parametros_existentes():
    conc = Concreto(60)
    r = verificar([camada(4, 16, 45)], concreto=conc)
    assert r.hipoteses_validas
    assert r.parametros["alfa_c"] == conc.alfa_c
    assert r.parametros["lambda"] == conc.lamb
    assert r.parametros["ecu"] == conc.ecu
    assert r.limite_x_sobre_d == .35
    # Referência analítica com constantes C60, não com motor poligonal.
    area = 4 * math.pi * .8**2
    x = area * (500 / 1.15) / (.8075 * (60 / 1.4) * 20 * .775)
    assert r.linha_neutra_cm == pytest.approx(x)
    assert r.mrd_kncm == pytest.approx(area * (500 / 1.15) * .1 * (45 - .775 * x / 2))


def test_es_do_aco_participa_da_validacao():
    r = verificar([camada(8, 20, 71.7)], secao=SecaoRetangular(25, 76, 2.5, 8), concreto=Concreto(40), aco=Aco(es=50000))
    assert r.deformacoes_aco[0] < r.parametros["fyd"] / 50000
    assert r.camadas_escoadas == (False,)
    assert r.mrd_kncm is None


def test_ordem_das_camadas_preservada_sem_mudar_capacidade():
    cs = [camada(2, 20, 45), camada(2, 16, 41)]
    a, b = verificar(cs), verificar(cs[::-1])
    assert a.mrd_kncm == pytest.approx(b.mrd_kncm)
    assert a.as_por_camada_cm2 == b.as_por_camada_cm2[::-1]
    assert a.d_por_camada_cm == b.d_por_camada_cm[::-1]


def test_parametros_customizados_e_serializacao_headless():
    r = verificar(gamma_c=1.5, gamma_s=1.2, gamma_f=1.3)
    assert r.parametros["fcd"] == 20
    assert r.parametros["fyd"] == pytest.approx(500 / 1.2)
    assert r.parametros["unidade_momento"] == "kN.cm"
    assert r.mk_equivalente_kncm == pytest.approx(r.mrd_kncm / 1.3)
    assert json.loads(json.dumps(asdict(r), allow_nan=False))["hipoteses_validas"] is True


@pytest.mark.parametrize("cs", [
    [], [camada(2, 16, 49)], [camada(2, 16, 1)],
    [camada(2, 16, 45), camada(2, 16, 45)],
    [camada(2, 16, 45), camada(2, 16, 44)], [camada(20, 20, 45)],
])
def test_geometria_invalida(cs):
    with pytest.raises(ValueError):
        verificar(cs)


@pytest.mark.parametrize("n,phi,d", [(0,16,45), (-1,16,45), (2,0,45), (2,-16,45), (2,16,0), (2,16,float("nan")), (2,float("inf"),45)])
def test_camada_valores_invalidos(n, phi, d):
    with pytest.raises(ValueError):
        camada(n, phi, d)


@pytest.mark.parametrize("n", [True, 2.5, "2"])
def test_quantidade_de_barras_deve_ser_inteira(n):
    with pytest.raises(TypeError):
        camada(n, 16, 45)


@pytest.mark.parametrize("kwargs", [{"gamma_c":0}, {"gamma_s":-1}, {"gamma_f":0}, {"gamma_f":float("nan")}, {"aco":Aco(es=0)}, {"aco":Aco(fyk=-500)}, {"aco":Aco(es=1000)}, {"concreto":Concreto(91)}, {"concreto":Concreto(float("nan"))}, {"secao":SecaoRetangular(20,50,3,0)}])
def test_parametros_invalidos(kwargs):
    with pytest.raises(ValueError):
        verificar(**kwargs)


def test_comparacao_poligonal_diagnostica_mesma_secao_e_armadura():
    # Seção 20x50, C30, CA50, 2 phi16 a d=45 cm.
    novo = verificar()
    barras = [BarraPosicionada(5, 5, 16), BarraPosicionada(15, 5, 16)]
    secao = SecaoPoligonalArmada([[0,0],[20,0],[20,50],[0,50]], barras)
    r = CalculadoraFlexoCompressao().momentos_resistentes(secao, Concreto(30), Aco(), 0, 0)
    assert r.convergiu
    assert abs(r.residual_equilibrio) <= max(.001, .01 * (1000*.8*(30/1.4)*.1 + novo.as_total_cm2*(500/1.15)*.1))
    assert novo.mrd_kncm > 0 and r.myd_resistente > 0
    # Não se exige coincidência: o motor poligonal mantém concreto 0.8fcd
    # e sua tolerância axial padrão. Valores e diferenças no relatório.
    assert not math.isclose(novo.mrd_kncm, r.myd_resistente, rel_tol=1e-6)
    assert novo.mrd_kncm == pytest.approx(7448.082857991116, rel=1e-12, abs=1e-8)
    # Regressão diagnóstica do motor legado, não uma referência normativa.
    assert r.myd_resistente == pytest.approx(7041.82921443038, rel=1e-12, abs=1e-8)


def test_api_publica_verificacao_headless():
    import concretopy
    from concretopy.api import __all__ as api_all
    from concretopy.verificacoes import verificar_flexao_viga_retangular as funcao
    for nome in ("CamadaArmaduraLongitudinal", "ResultadoVerificacaoFlexao", "verificar_flexao_viga_retangular"):
        assert nome in api_all
        assert nome in concretopy.__all__
    assert funcao is concretopy.verificar_flexao_viga_retangular
    r = concretopy.verificar_flexao_viga_retangular(
        concretopy.SecaoRetangular(20, 50, 3), concretopy.Concreto(30), concretopy.Aco(),
        [concretopy.CamadaArmaduraLongitudinal(2, concretopy.Barra(16), 45)],
    )
    assert isinstance(r, concretopy.ResultadoVerificacaoFlexao)
    assert r.mrd_kncm is not None
