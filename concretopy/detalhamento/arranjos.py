from __future__ import annotations

import math
from dataclasses import dataclass
from math import pi

from ..armaduras import Armadura, Barra
from ..materiais import Aco
from ..normas import espacamento_min_arm_long_viga
from ..resultados import OpcaoBitola


def area_barra_cm2(bitola_mm: float) -> float:
    return pi * (bitola_mm / 10) ** 2 / 4


def calcular_num_barras(as_necessaria_cm2: float, bitola_mm: float | None = None) -> int | dict[float, int]:
    if bitola_mm is not None:
        return int(as_necessaria_cm2 / area_barra_cm2(bitola_mm)) + 1
    return {bitola: int(as_necessaria_cm2 / area_barra_cm2(bitola)) + 1 for bitola in Aco.BITOLAS_MM}


def calcular_espacamento_equivalente(as_por_s_cm2_m: float, bitola_mm: float | None = None) -> int | dict[float, int]:
    if bitola_mm is not None:
        n = calcular_num_barras(as_por_s_cm2_m, bitola_mm)
        return int(100 / n)
    espacamentos = {}
    for bitola in Aco.BITOLAS_MM:
        n = calcular_num_barras(as_por_s_cm2_m, bitola)
        if n != 1:
            espacamentos[bitola] = int(100 / n)
    return espacamentos


def opcoes_bitola(as_necessaria_cm2: float, bitolas_mm: tuple[float, ...] | None = None) -> list[OpcaoBitola]:
    if bitolas_mm is None:
        bitolas_mm = Aco.BITOLAS_MM
    opcoes = []
    for bitola in bitolas_mm:
        n = calcular_num_barras(as_necessaria_cm2, bitola)
        area_fornecida = n * area_barra_cm2(bitola)
        opcoes.append(OpcaoBitola(bitola, n, area_fornecida))
    return sorted(opcoes, key=lambda x: (x.numero_barras, x.area_fornecida_cm2))


def numero_barras_maximo_camada(
    b_cm: float,
    bitola_longitudinal_mm: float,
    bitola_estribo_mm: float,
    cobrimento: float,
    dimensao_agregado_mm: float = 16,
    espaco_vibrador: float | None = None,
) -> int:
    esp_min = espacamento_min_arm_long_viga(bitola_longitudinal_mm, dimensao_agregado_mm)

    if espaco_vibrador is None or espaco_vibrador < esp_min:
        espaco_vibrador = esp_min

    return math.floor(
        (
            b_cm
            - 2 * cobrimento
            - 2 * bitola_estribo_mm / 10
            - espaco_vibrador
            + 2 * esp_min
        )
        / (esp_min + bitola_longitudinal_mm / 10)
    )


def barras_por_camada(
    b_cm: float,
    numero: int,
    bitola_longitudinal_mm: float,
    bitola_estribo_mm: float,
    cobrimento: float,
    dimensao_agregado_mm: float = 16,
    espaco_vibrador: float | None = None,
) -> list[int]:
    numero_barras_camada = numero_barras_maximo_camada(
        b_cm,
        bitola_longitudinal_mm,
        bitola_estribo_mm,
        cobrimento,
        dimensao_agregado_mm,
        espaco_vibrador,
    )
    if numero <= 0:
        raise ValueError("o Numero de barras deve ser um valor maior que zero")
    if numero_barras_camada <= 0:
        raise ValueError("Nao foi possivel distribuir barras na secao informada")

    numero_camadas = math.ceil(numero / numero_barras_camada)
    camadas = []

    if numero_camadas == 1:
        return [numero]

    for i in range(numero_camadas):
        if i == numero_camadas - 1:
            camadas.append(numero - numero_barras_camada * i)
        else:
            camadas.append(numero_barras_camada)
    return camadas


@dataclass(frozen=True)
class ArranjoArmadura:
    armadura: Armadura
    as_necessaria_cm2: float
    as_excesso: float


@dataclass(frozen=True)
class ArranjoArmaduraFlexaoViga(ArranjoArmadura):
    numero_camadas: int
    numero_barras_camada: list[int]

    def to_list(self):
        lista_camada = list()
        for camada in range(self.numero_camadas):
            lista_camada.append(( self.numero_barras_camada[camada], self.armadura.barra.diametro_mm))
        return lista_camada

@dataclass(frozen=True)
class ArranjoEstribosViga(ArranjoArmadura):
    bitola_longitudinal_mm: float
    ramos: int


def definir_arranjo_arm_long_vigas(
    as_nec_cm2: float,
    b_viga_cm: float,
    cobrimento_cm: float,
    bitola_estribo_mm: float,
    bitola_longitudinal_mm: float,
    dimensao_agregado_mm: float = 16,
    espaco_vibrador: float | None = None,
) -> ArranjoArmaduraFlexaoViga:
    if as_nec_cm2 <= 0:
        raise ValueError("as_nec_cm2 deve ser positivo")
    barra = Barra(bitola_longitudinal_mm)
    numero = math.ceil(as_nec_cm2 / barra.area_cm2)
    armadura = Armadura(barra, None, numero, cobrimento_cm)
    camadas = barras_por_camada(
        b_viga_cm,
        numero,
        bitola_longitudinal_mm,
        bitola_estribo_mm,
        cobrimento_cm,
        dimensao_agregado_mm,
        espaco_vibrador,
    )
    excesso = armadura.area_cm2 - as_nec_cm2

    return ArranjoArmaduraFlexaoViga(
        armadura=armadura,
        as_necessaria_cm2=as_nec_cm2,
        as_excesso=excesso,
        numero_camadas=len(camadas),
        numero_barras_camada=camadas,
    )


def escolher_arranjo(
    as_nec_cm2: float,
    b_viga_cm: float,
    cobrimento_cm: float,
    bitola_estribo_mm: float,
    dimensao_agregado_mm: float = 16,
    espaco_vibrador: float | None = None,
    bitolas_mm: tuple[float, ...] | None = None,
) -> ArranjoArmaduraFlexaoViga:
    if as_nec_cm2 <= 0:
        raise ValueError("as_nec_cm2 deve ser positivo")

    if bitolas_mm is None:
        bitolas_mm = Aco.BITOLAS_MM

    def penalizacao_num_barras(numero_barras: int) -> float:
        if 1 < numero_barras <= 4:
            return 0
        if numero_barras <= 6:
            return 1
        if numero_barras <= 8:
            return 3
        if numero_barras <= 10:
            return 6
        if numero_barras == 1:
            return 100
        return 10 + 2 * (numero_barras - 10)

    def penalizacao_num_camadas(numero_camadas: int) -> float:
        if numero_camadas == 1:
            return 0
        if numero_camadas == 2:
            return 1
        if numero_camadas == 3:
            return 4
        return 12

    def penalizacao(arranjo: ArranjoArmaduraFlexaoViga, w1: float, w2: float, w3: float) -> float:
        parcela_barras = w1 * penalizacao_num_barras(arranjo.armadura.numero)
        parcela_camadas = w2 * penalizacao_num_camadas(arranjo.numero_camadas) * arranjo.numero_camadas
        parcela_excesso = w3 * (arranjo.as_excesso / arranjo.as_necessaria_cm2)
        return parcela_barras + parcela_camadas + parcela_excesso

    arranjos: list[ArranjoArmaduraFlexaoViga] = []
    for bitola_mm in bitolas_mm:
        try:
            arranjo = definir_arranjo_arm_long_vigas(
                as_nec_cm2=as_nec_cm2,
                b_viga_cm=b_viga_cm,
                cobrimento_cm=cobrimento_cm,
                bitola_estribo_mm=bitola_estribo_mm,
                bitola_longitudinal_mm=bitola_mm,
                dimensao_agregado_mm=dimensao_agregado_mm,
                espaco_vibrador=espaco_vibrador,
            )
        except ValueError:
            continue
        arranjos.append(arranjo)

    if not arranjos:
        raise ValueError("Nao foi possivel definir um arranjo viavel para a secao informada")

    return min(arranjos, key=lambda arranjo: penalizacao(arranjo, 1, 1, 100))
