
from __future__ import annotations
from ..materiais import Aco

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