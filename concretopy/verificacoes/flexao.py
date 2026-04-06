from __future__ import annotations

from ..exceptions import TaxaArmaduraExcedida
from ..materiais import Concreto, Aco
from ..normas.nbr6118 import taxa_armadura_min_viga
from ..resultados import ResultadoFlexao
from ..secoes import SecaoRetangular


def dimensionar_flexao_viga_retangular(
    secao: SecaoRetangular,
    concreto: Concreto,
    aco: Aco,
    mk: float,
    gamma_f: float = 1.4,
    gamma_c: float = 1.4,
    gamma_s: float = 1.15,
    diametro_barra_mm: float = 12.5,
) -> ResultadoFlexao:
    """Dimensiona a armadura longitudinal de uma viga retangular.

    Convenções oficiais:
    - geometria em cm
    - tensões em MPa
    - bitolas em mm
    - momento característico ``mk`` em kN.cm
    - resultado de armadura em cm²
    """
    d = secao.d(diametro_barra_mm)
    d_linha = secao.d_linha(diametro_barra_mm)
    fcd = concreto.fcd(gamma_c) * 1e-1
    fyd = aco.fyd(gamma_s) * 1e-1
    eyd = aco.ey / gamma_s
    md = mk * gamma_f

    x23 = concreto.ecu / (concreto.ecu + aco.eyu) * d
    x34 = concreto.ecu / (concreto.ecu + aco.ey / gamma_s) * d
    x_dutil = 0.45 * d if concreto.fck <= 50 else 0.35 * d
    x_limite = min(x34, x_dutil)
    y_limite = concreto.lamb * x_limite
    md_max = y_limite * secao.bw * concreto.alfa_c * fcd * (d - y_limite / 2)

    if md > md_max:
        y = y_limite
        acc = y * secao.bw
        e2 = concreto.ecu * (y_limite - concreto.lamb * d_linha) / y_limite
        tensao_arm_sup = e2 * aco.es * 1e-1 if e2 < eyd else fyd
        as_compressao = (md - md_max) / (tensao_arm_sup * (d - d_linha))
        as_tracao = (concreto.alfa_c * acc * fcd + as_compressao * tensao_arm_sup) / fyd
    else:
        y = d - (d ** 2 - 2 * md / (concreto.alfa_c * secao.bw * fcd)) ** 0.5
        acc = y * secao.bw
        as_tracao = concreto.alfa_c * acc * fcd / fyd
        as_compressao = 0.0

    taxa_min = taxa_armadura_min_viga(concreto.fck)
    as_min = taxa_min * secao.area / 100
    as_max = 0.04 * secao.area
    as_tracao = max(as_tracao, as_min)

    if as_tracao + as_compressao > as_max:
        raise TaxaArmaduraExcedida("Taxa máxima de armadura excedida. Redimensione a seção.")

    x = y / concreto.lamb
    if x <= x23:
        dominio = 2
    elif x <= x34:
        dominio = 3
    else:
        dominio = 4

    return ResultadoFlexao(as_tracao, as_compressao, acc, x, dominio)
