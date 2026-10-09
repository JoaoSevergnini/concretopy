from __future__ import annotations

from math import cos, radians, sin

from ..exceptions import RompimentoBielaCompressao
from ..materiais import Concreto, Aco
from ..resultados import ResultadoCortante
from ..secoes import SecaoRetangular


def dimensionar_cortante_viga(
    secao: SecaoRetangular,
    concreto: Concreto,
    aco: Aco,
    vk: float,
    alfa_graus: float = 90.0,
    nk: float = 0,
    mk: float = 0,
    gamma_f: float = 1.4,
    gamma_c: float = 1.4,
    gamma_s: float = 1.15,
    diametro_barra_mm: float = 12.5,
) -> ResultadoCortante:
    """Dimensiona armadura transversal de cortante para viga retangular.

    Convenções oficiais:
    - geometria em cm
    - tensões em MPa
    - bitolas em mm
    - força cortante característica ``vk`` em kN
    - resultado ``asw_por_s`` governante em cm²/m
    - ``asw_por_s_calculado`` antes do mínimo, limitado a zero, em cm²/m
    - ``asw_por_s_minimo`` separado, em cm²/m
    """
    d = secao.d(diametro_barra_mm)
    dl = secao.d_linha(diametro_barra_mm)
    fcd = concreto.fcd(gamma_c) * 1e-1
    fctd = concreto.fctd(gamma_c) * 1e-1
    fyd = aco.fyd(gamma_s) * 1e-1
    vsd = vk * gamma_f
    nsd = nk * gamma_f
    msd = mk * gamma_f

    vc_zero = 0.6 * fctd * secao.bw * d
    vrd2 = 0.27 * concreto.alfa_v2 * fcd * secao.bw * d

    if nk != 0:

        mo = secao.modulo_elastico * (abs(nsd) / secao.area)

        if (nk > 0 and (mk/nk) < (d - dl)/2) or (nk>0 and mk==0):
            vc = 0

        elif nk>0 and (mk/nk) > (d - dl)/2:
            vc = 0.6 * fctd * secao.bw * d

        elif nk < 0 and mk != 0:
            vc = min( 2 * vc_zero, vc_zero * (1 + mo/msd))

        else:
            vc = 2 * vc_zero
    else:
        vc = vc_zero

    if vsd >= vrd2:
        raise RompimentoBielaCompressao("Rompimento da biela comprimida: Vsd >= Vrd2.")

    asw_por_s = ((vsd - vc) / (0.9 * d * fyd * (sin(radians(alfa_graus)) + cos(radians(alfa_graus)))) * 100)
    asw_por_s_min = 0.2 * (concreto.fctm / aco.fyk) * secao.bw * 100
    asw_por_s_calculado = max(0.0, asw_por_s)
    asw_por_s = max(asw_por_s, asw_por_s_min)
    return ResultadoCortante(asw_por_s, vc, vrd2,
                            asw_por_s_calculado=asw_por_s_calculado,
                            asw_por_s_minimo=asw_por_s_min)
