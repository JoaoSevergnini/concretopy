"""Posições reproduzidas de VIGAS!K5:K7, sem depender de Excel."""
import json
from pathlib import Path

import pytest

from concretopy import (
    Aco, Barra, CamadaArmaduraLongitudinal, Concreto, SecaoRetangular,
    calcular_alturas_uteis_camadas, verificar_flexao_viga_retangular,
)


def camada(phi, d=None, n=2):
    return CamadaArmaduraLongitudinal(n, Barra(phi), d)


@pytest.mark.parametrize("caso", json.loads(
    (Path(__file__).parent / "references/flexure_resistance.json").read_text(encoding="utf-8")
)["casos"][:4], ids=lambda caso: caso["id"])
def test_posicoes_automaticas_reproduzem_referencias_da_planilha(caso):
    cs = [camada(c["diametro_mm"], n=c["numero_barras"]) for c in caso["camadas"]]
    secao = SecaoRetangular(**caso["secao"])
    esperado = tuple(c["d_cm"] for c in caso["camadas"])
    assert calcular_alturas_uteis_camadas(secao, cs) == pytest.approx(esperado, abs=1e-12)
    r = verificar_flexao_viga_retangular(secao, Concreto(caso["fck"]), Aco(), cs)
    assert r.d_por_camada_cm == pytest.approx(esperado, abs=1e-12)
    assert r.mrd_kncm == pytest.approx(caso["esperado"]["mrd_kncm"], rel=1e-12, abs=1e-8)
    assert all(c.d_cm is None for c in cs)  # Entrada imutável preservada.
    assert any("K5:K7" in aviso for aviso in r.avisos)


@pytest.mark.parametrize("phi,esperado", [(24.9,66.955), (25,66.45), (25.1,66.435)])
def test_limiar_25_mm_usa_bitola_da_camada_atual(phi, esperado):
    # Primeira phi25: d1=76-2.5-.8-1.25=71.45.
    ds = calcular_alturas_uteis_camadas(SecaoRetangular(25,76,2.5,8), [camada(25), camada(phi)])
    assert ds == pytest.approx((71.45, esperado), abs=1e-12)


def test_posicao_explicita_ancora_proxima_camada():
    cs = [camada(20,70), camada(16), camada(12.5,60), camada(10)]
    ds = calcular_alturas_uteis_camadas(SecaoRetangular(25,76,2.5,8), cs)
    assert ds == pytest.approx((70,66.2,60,56.875), abs=1e-12)
    r = verificar_flexao_viga_retangular(SecaoRetangular(25,76,2.5,8), Concreto(40), Aco(), cs)
    assert r.d_por_camada_cm == ds


def test_explicitamente_informado_nao_recebe_regra_da_planilha():
    cs = [camada(16,41), camada(20,45)]
    assert calcular_alturas_uteis_camadas(SecaoRetangular(20,50,3), cs) == (41,45)
    r = verificar_flexao_viga_retangular(SecaoRetangular(20,50,3), Concreto(30), Aco(), cs)
    assert r.d_por_camada_cm == (41,45)
    assert not any("K5:K7" in aviso for aviso in r.avisos)


def test_geometria_automatica_fora_da_secao_e_rejeitada():
    with pytest.raises(ValueError):
        verificar_flexao_viga_retangular(SecaoRetangular(20,10,3), Concreto(30), Aco(), [camada(16), camada(16)])
    with pytest.raises(ValueError):
        calcular_alturas_uteis_camadas(SecaoRetangular(20,4,3), [camada(25)])


def test_helper_valida_entradas_e_e_exportado():
    from concretopy.api import __all__ as api_all
    from concretopy.verificacoes import calcular_alturas_uteis_camadas as funcao
    assert "calcular_alturas_uteis_camadas" in api_all
    assert funcao is calcular_alturas_uteis_camadas
    with pytest.raises(ValueError):
        funcao(SecaoRetangular(20,50,3), [])
    with pytest.raises(TypeError):
        funcao(SecaoRetangular(20,50,3), [Barra(16)])
