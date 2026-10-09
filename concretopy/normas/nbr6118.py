
from __future__ import annotations
from typing import TYPE_CHECKING

from ..materiais import Aco

if TYPE_CHECKING:
    from ..elementos.viga import VigaRetangular

_TAXA_ARMADURA_MIN_VIGA = {
    20: 0.150, 25: 0.150, 30: 0.150, 35: 0.164, 40: 0.179, 45: 0.194, 50: 0.208,
    60: 0.219, 65: 0.226, 70: 0.233, 75: 0.239, 80: 0.245, 85: 0.251, 90: 0.256,
}
def taxa_armadura_min_viga(fck: float) -> float:
    chave = int(fck)
    if chave not in _TAXA_ARMADURA_MIN_VIGA:
        raise ValueError(f"fck={fck} MPa não cadastrado na tabela de taxa mínima.")
    return _TAXA_ARMADURA_MIN_VIGA[chave]

def espacamento_min_arm_long_viga(bitola_mm: float, dimensao_agregado_mm: float = 16) -> float:
    if not bitola_mm in Aco.BITOLAS_MM:
        raise ValueError(f"bitolas={bitola_mm} mm não definida em bitolas padrões")
    return max(bitola_mm/10, 2.0, 1.2 * dimensao_agregado_mm/10)

def espacamento_max_estribo_vigas_cm(viga: VigaRetangular, vd_kn: float, diametro_barra_long_mm: float = 12.5) -> float:
        
        if vd_kn <= 0.67 * viga.vrd2_kn:
            return min(0.6 * viga.secao.d(diametro_barra_long_mm) , 30)
        else:
            return min(0.3 * viga.secao.d(diametro_barra_long_mm), 20)


# Ancoragem: NBR 6118:2023, trechos 9.3.2.1, 9.4.2.4 e 9.4.2.5
# fornecidos pelo usuario. Eta1 nervurada: planilha VIGAS!R27:R28;
# o trecho 9.3.2.1 remete a Tabela 8.2, nao fornecida.
ETA1_BARRA_NERVURADA = 2.25


def coeficiente_aderencia_eta2(boa_aderencia: bool) -> float:
    """Retorna eta2 (adimensional), conforme 9.3.2.1.

    boa_aderencia : bool
        Classificacao informada pelo usuario conforme 9.3.1; sem unidade.
        True retorna 1,0; False retorna 0,7. Nao classifica geometria.
    """
    if not isinstance(boa_aderencia, bool):
        raise TypeError("boa_aderencia deve ser booleano.")
    return 1.0 if boa_aderencia else 0.7


def coeficiente_aderencia_eta3(bitola_mm: float) -> float:
    """Retorna eta3 (adimensional) conforme 9.3.2.1.

    bitola_mm : float
        Diametro nominal em mm, positivo e finito. Exige eta3 positivo.
        Para phi < 32 mm usa 1; nos demais casos usa (132 - phi)/100.
        O limite matematico phi < 132 mm nao certifica bitola comercial.
    """
    from math import isfinite

    if isinstance(bitola_mm, bool) or not isinstance(bitola_mm, (int, float)):
        raise TypeError("bitola_mm deve ser numerico.")
    if not isfinite(bitola_mm) or not 0 < bitola_mm < 132:
        raise ValueError("bitola_mm deve ser finito, positivo e resultar em eta3 > 0.")
    return 1.0 if bitola_mm < 32 else (132.0 - bitola_mm) / 100.0


def limite_inferior_lb_cm(bitola_mm: float) -> float:
    """Retorna o piso 25 phi de lb em cm, conforme 9.4.2.4.

    bitola_mm : float
        Diametro nominal em mm, no dominio de coeficiente_aderencia_eta3.
    """
    coeficiente_aderencia_eta3(bitola_mm)
    return 25.0 * (bitola_mm / 10.0)


def comprimento_minimo_ancoragem_cm(lb_cm: float, bitola_mm: float) -> float:
    """Retorna max(0,3 lb; 10 phi; 100 mm) em cm, conforme 9.4.2.5.

    lb_cm : float
        Comprimento basico em cm, finito e pelo menos 25 phi (9.4.2.4).
    bitola_mm : float
        Diametro nominal em mm, no dominio de coeficiente_aderencia_eta3.

    Hipotese: ancoragem de barra passiva no escopo de 9.4.2.5.
    """
    from math import isfinite

    piso = limite_inferior_lb_cm(bitola_mm)
    if isinstance(lb_cm, bool) or not isinstance(lb_cm, (int, float)):
        raise TypeError("lb_cm deve ser numerico.")
    if not isfinite(lb_cm) or lb_cm < piso:
        raise ValueError("lb_cm deve ser finito e >= 25 phi.")
    phi_cm = bitola_mm / 10.0
    minimo_absoluto_cm = 100.0 / 10.0  # 100 mm -> 10 cm
    return max(0.3 * lb_cm, 10.0 * phi_cm, minimo_absoluto_cm)


def fracao_armadura_positiva_apoio(razao_momentos: float) -> float:
    """Fracao minima de As do vao conforme 18.3.2.4-c (NBR 6118:2023).

    razao_momentos : float
        |Mk_negativo_apoio| / Mk_positivo_max_vao, adimensional, finita e >= 0.

    Retorna fracao adimensional: 1/3 para razao <= 0,5 (incluindo zero),
    ou 1/4 para razao > 0,5. A selecao dos momentos cabe ao chamador.
    Limites conforme especificacao fornecida pelo engenheiro.
    """
    from math import isfinite

    if isinstance(razao_momentos, bool) or not isinstance(razao_momentos, (int, float)):
        raise TypeError("razao_momentos deve ser numerica.")
    if not isfinite(razao_momentos) or razao_momentos < 0:
        raise ValueError("razao_momentos deve ser finita e nao negativa.")
    return 1.0 / 3.0 if razao_momentos <= 0.5 else 1.0 / 4.0


def coeficiente_alpha_ancoragem_apoio(gancho_valido: bool) -> float:
    """Retorna alpha adimensional de 9.4.2.5 para este procedimento.

    gancho_valido : bool
        Validacao do gancho feita pelo chamador, sem unidade. True indica
        que suas condicoes normativas/geometricas foram verificadas e usa
        0,7; False usa 1,0. Nao avalia geometria, cobrimento ou confinamento.
    """
    if not isinstance(gancho_valido, bool):
        raise TypeError("gancho_valido deve ser booleano.")
    return 0.7 if gancho_valido else 1.0
