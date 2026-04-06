from __future__ import annotations

"""Convenções e conversões de unidades do pacote.

Convenções oficiais do ``concretopy``:
- tensões: MPa
- geometria: cm
- bitolas: mm
- forças: kN
- momentos: kN.cm

Para facilitar o uso em escritório, o módulo também oferece conversões simples
entre tf <-> kN e tf.m <-> kN.cm.
"""

KN_POR_TF_EXATO = 9.80665
KN_POR_TF_APROX = 10.0
CM_POR_M = 100.0


def tf_para_kn(valor: float, aproximado: bool = True) -> float:
    fator = KN_POR_TF_APROX if aproximado else KN_POR_TF_EXATO
    return valor * fator


def kn_para_tf(valor: float, aproximado: bool = True) -> float:
    fator = KN_POR_TF_APROX if aproximado else KN_POR_TF_EXATO
    return valor / fator


def tfm_para_kncm(valor: float, aproximado: bool = True) -> float:
    return tf_para_kn(valor, aproximado=aproximado) * CM_POR_M


def kncm_para_tfm(valor: float, aproximado: bool = True) -> float:
    return kn_para_tf(valor / CM_POR_M, aproximado=aproximado)


def converter_forca(valor: float, unidade_origem: str, unidade_destino: str = 'kN', aproximado: bool = True) -> float:
    origem = unidade_origem.strip().lower()
    destino = unidade_destino.strip().lower()
    if origem == destino:
        return valor
    if origem == 'tf' and destino == 'kn':
        return tf_para_kn(valor, aproximado=aproximado)
    if origem == 'kn' and destino == 'tf':
        return kn_para_tf(valor, aproximado=aproximado)
    raise ValueError(f'Conversão de força não suportada: {unidade_origem} -> {unidade_destino}')


def converter_momento(valor: float, unidade_origem: str, unidade_destino: str = 'kN.cm', aproximado: bool = True) -> float:
    origem = unidade_origem.strip().lower().replace(' ', '')
    destino = unidade_destino.strip().lower().replace(' ', '')
    if origem == destino:
        return valor
    if origem == 'tf.m' and destino == 'kn.cm':
        return tfm_para_kncm(valor, aproximado=aproximado)
    if origem == 'kn.cm' and destino == 'tf.m':
        return kncm_para_tfm(valor, aproximado=aproximado)
    raise ValueError(f'Conversão de momento não suportada: {unidade_origem} -> {unidade_destino}')
