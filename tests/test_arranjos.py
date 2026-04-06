
import pytest

from concretopy.detalhamento.arranjos import (
    area_barra_cm2,
    barras_por_camada,
    calcular_num_barras,
    escolher_arranjo,
)

def test_area_barra():
    assert area_barra_cm2(10.0) > 0

def test_numero_barras():
    n = calcular_num_barras(4.0, 10.0)
    assert n >= 1


def test_barras_por_camada_retorna_numero_total_quando_ha_uma_camada():
    camadas = barras_por_camada(30.0, 3, 10.0, 5.0, 3.0)
    assert camadas == [3]


def test_escolher_arranjo_retorna_arranjo_compativel():
    arranjo = escolher_arranjo(
        as_nec_cm2=4.0,
        b_viga_cm=20.0,
        cobrimento_cm=3.0,
        bitola_estribo_mm=5.0,
    )

    assert arranjo.as_necessaria_cm2 == 4.0
    assert sum(arranjo.numero_barras_camada) == arranjo.armadura.numero
    assert arranjo.numero_camadas == len(arranjo.numero_barras_camada)
    assert arranjo.armadura.area_cm2 >= arranjo.as_necessaria_cm2


def test_escolher_arranjo_falha_sem_secao_viavel():
    with pytest.raises(ValueError, match="arranjo viavel"):
        escolher_arranjo(
            as_nec_cm2=4.0,
            b_viga_cm=6.0,
            cobrimento_cm=3.0,
            bitola_estribo_mm=12.5,
        )
