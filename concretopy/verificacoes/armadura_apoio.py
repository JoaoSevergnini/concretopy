"""Demanda positiva no apoio: condicoes a/b/c de 18.3.2.4.

Avalia um unico par Mk/Vk informado. z=d-x/2 e simplificacao de engenharia.
Nao seleciona esforcos nem verifica comprimento de ancoragem/detalhamento.
"""
from __future__ import annotations

from math import isfinite
from typing import Literal, Sequence

from ..armaduras import CamadaArmaduraLongitudinal
from ..materiais import Aco, Concreto
from ..normas.nbr6118 import fracao_armadura_positiva_apoio
from ..resultados import (
    CondicaoAArmaduraApoio, CondicaoBArmaduraApoio, CondicaoCArmaduraApoio,
    ResultadoArmaduraApoio, ResultadoFlexao,
)
from ..secoes import SecaoRetangular
from .decalagem import calcular_al
from .flexao import dimensionar_flexao_viga_retangular, verificar_flexao_viga_retangular


def _numero(nome: str, valor: float, *, zero: bool = False, sinal: bool = False) -> None:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise TypeError(f"{nome} deve ser numerico.")
    if not isfinite(valor) or (not sinal and (valor < 0 or (valor == 0 and not zero))):
        raise ValueError(f"{nome} fora do dominio: exige numero finito e sinal/valor valido.")


def _secao_valida(secao: SecaoRetangular, nome: str) -> None:
    if not isinstance(secao, SecaoRetangular):
        raise TypeError(f"{nome} deve ser SecaoRetangular.")
    for campo in ('bw', 'h', 'cobrimento', 'diametro_estribo_mm'):
        _numero(f"{nome}.{campo}", getattr(secao, campo), zero=campo == 'cobrimento')


def _dimensionar(
    secao: SecaoRetangular, concreto: Concreto, aco: Aco, mk: float,
    d: float, d_linha: float | None, gamma_f: float, gamma_c: float,
    gamma_s: float, contexto: str,
) -> ResultadoFlexao:
    r = dimensionar_flexao_viga_retangular(
        secao, concreto, aco, mk, gamma_f=gamma_f, gamma_c=gamma_c,
        gamma_s=gamma_s, d_cm=d, d_linha_cm=d_linha,
    )
    for nome, valor in (("as_tracao", r.as_tracao), ("as_compressao", r.as_compressao),
                        ("linha_neutra", r.linha_neutra),
                        ("area_concreto_comprimido", r.area_concreto_comprimido)):
        _numero(f"{contexto}.{nome}", valor, zero=True)
    if r.as_compressao > 0 and d_linha is None:
        raise ValueError(f"{contexto} exige armadura comprimida: informe d_linha_{contexto}_cm.")
    return r


def calcular_armadura_positiva_apoio(
    *,
    secao: SecaoRetangular,
    concreto: Concreto,
    aco: Aco,
    camadas_apoio: Sequence[CamadaArmaduraLongitudinal],
    tipo_apoio: Literal['extremo', 'intermediario'],
    mk_apoio_kncm: float,
    vk_apoio_kn: float,
    mk_positivo_max_vao_kncm: float,
    mk_negativo_apoio_kncm: float,
    d_vao_cm: float,
    secao_vao: SecaoRetangular | None = None,
    nd_tracao_kn: float = 0.0,
    gamma_f: float = 1.4,
    gamma_c: float = 1.4,
    gamma_s: float = 1.15,
    d_linha_apoio_cm: float | None = None,
    d_linha_vao_cm: float | None = None,
) -> ResultadoArmaduraApoio:
    """Determina max(As_a, As_b, As_c) das condicoes aplicaveis, em cm2.

    secao : SecaoRetangular
        Secao do apoio; geometria em cm, bitola do estribo em mm.
    concreto, aco : Concreto, Aco
        Materiais existentes, resistencias em MPa; comuns ao apoio e vao.
    camadas_apoio : Sequence[CamadaArmaduraLongitudinal]
        Armadura positiva real que chega ao apoio. Bitolas em mm, areas em
        cm2 e d_i em cm a partir da face comprimida. d_i omitido segue a
        rotina existente de camadas. Reutiliza sua analise para d e x.
    tipo_apoio : {'extremo', 'intermediario'}
        Classificacao explicita, sem unidade. B aplica somente a extremo.
    mk_apoio_kncm : float
        Momento caracteristico em kN.cm, >= 0. Zero desativa somente A.
    vk_apoio_kn : float
        Magnitude caracteristica em kN, >= 0, do par recebido. O chamador
        seleciona o esforco; nunca aplica abs() silencioso ao cortante.
    mk_positivo_max_vao_kncm : float
        Maximo momento positivo caracteristico no vao, em kN.cm, > 0.
    mk_negativo_apoio_kncm : float
        Extremo negativo caracteristico no apoio, em kN.cm, <= 0. Usado
        exclusivamente na razao de C; zero seleciona C1. Pode coexistir
        com extremo positivo no apoio. C e avaliada independentemente de A.
    d_vao_cm : float
        Altura util para dimensionar As do vao, em cm; explicita e positiva.
    secao_vao : SecaoRetangular | None
        Geometria do vao (cm; estribo mm). None usa secao do apoio, sem
        reutilizar automaticamente d do apoio. Mesmo concreto e aco.
    nd_tracao_kn : float
        Tracao normal JA DE CALCULO em kN, >= 0, padrao zero, para o par recebido.
        Nao recebe gamma_f novamente. Compressao nao integra este escopo.
    gamma_f, gamma_c, gamma_s : float
        Coeficientes adimensionais positivos; majoracao de Mk/Vk e
        minoracao das resistencias do concreto/aco. Todos finitos.
    d_linha_apoio_cm, d_linha_vao_cm : float | None
        Posicao da armadura comprimida a partir da face comprimida, em cm.
        Necessaria se o dimensionamento correspondente exigir aco comprimido.
        Nao representa aprovacao ou existencia dessa armadura.

    Returns
    -------
    ResultadoArmaduraApoio
        Demanda e estados auditaveis, areas em cm2, comprimentos em cm,
        tensoes em MPa, forcas em kN e momentos em kN.cm. Governantes
        incluem todos os empates exatos. Sem campo de aprovacao/atende.

    Notes
    -----
    A reutiliza dimensionamento por momento positivo; C usa 1/3 ou 1/4
    da demanda do vao (com o minimo do dimensionador existente).
    B avalia exclusivamente Mk/Vk desta chamada, com um unico al.
    Fsd=Md/z+(al/d)*Vd+Nd; As=Fsd/(fyd_mpa*0.1). z=d-x/2 e simplificacao
    adotada pelo engenheiro, nao identidade geral do bloco resistente.
    A selecao de pares e a verificacao da concomitancia pertencem ao
    chamador; a biblioteca nao interpreta envoltorias ou compara chamadas.
    Herda de calcular_al estribos verticais e Vc=Vc0, sem corrigir Vc por Nd.

    Raises
    ------
    TypeError, ValueError
        Entradas invalidas, geometria incompativel ou modelo das camadas
        sem hipoteses validas para usar x. Limites do dimensionador existente
        (incluindo tabela de taxa minima) permanecem aplicaveis.
    """
    _secao_valida(secao, 'secao')
    secao_vao = secao if secao_vao is None else secao_vao
    _secao_valida(secao_vao, 'secao_vao')
    if not isinstance(concreto, Concreto) or not isinstance(aco, Aco):
        raise TypeError("Materiais devem ser Concreto e Aco.")
    if not isinstance(tipo_apoio, str):
        raise TypeError("tipo_apoio deve ser string.")
    if tipo_apoio not in ('extremo', 'intermediario'):
        raise ValueError("tipo_apoio deve ser extremo ou intermediario.")
    for nome, valor in (("mk_apoio_kncm", mk_apoio_kncm),
                        ("vk_apoio_kn", vk_apoio_kn),
                        ("nd_tracao_kn", nd_tracao_kn)):
        _numero(nome, valor, zero=True)
    for nome, valor in (("mk_positivo_max_vao_kncm", mk_positivo_max_vao_kncm),
                        ("d_vao_cm", d_vao_cm), ("gamma_f", gamma_f),
                        ("gamma_c", gamma_c), ("gamma_s", gamma_s)):
        _numero(nome, valor)
    _numero('mk_negativo_apoio_kncm', mk_negativo_apoio_kncm, sinal=True)
    if mk_negativo_apoio_kncm > 0:
        raise ValueError("mk_negativo_apoio_kncm deve ser <= 0.")
    for nome, valor in (("d_linha_apoio_cm", d_linha_apoio_cm),
                        ("d_linha_vao_cm", d_linha_vao_cm)):
        if valor is not None:
            _numero(nome, valor)
    for nome, mk in (("md_apoio", mk_apoio_kncm), ('md_vao', mk_positivo_max_vao_kncm)):
        _numero(nome, gamma_f * mk, zero=True)

    # Reutiliza integralmente validacao geometrica, centroide e linha neutra.
    resistente = verificar_flexao_viga_retangular(
        secao, concreto, aco, camadas_apoio,
        gamma_c=gamma_c, gamma_s=gamma_s,
    )
    if not resistente.hipoteses_validas:
        raise ValueError("Hipoteses da analise das camadas invalidas: " + ' '.join(resistente.avisos))
    d = resistente.d_equivalente_cm
    x = resistente.linha_neutra_cm
    z = d - x / 2  # Simplificacao de engenharia confirmada, nao z do bloco.
    for nome, valor in (("d_cm", d), ("x_cm", x), ("z_cm", z)):
        _numero(nome, valor)
    for nome, valor, geometria, altura in (
        ('d_linha_apoio_cm', d_linha_apoio_cm, secao, d),
        ('d_linha_vao_cm', d_linha_vao_cm, secao_vao, d_vao_cm),
    ):
        if valor is not None:
            margem = geometria.cobrimento + geometria.diametro_estribo_mm / 10
            if not margem < valor < altura:
                raise ValueError(f"{nome} incompativel com cobrimento ou altura util.")

    a_flexao = None
    if mk_apoio_kncm > 0:
        a_flexao = _dimensionar(secao, concreto, aco, mk_apoio_kncm,
                               d, d_linha_apoio_cm, gamma_f, gamma_c, gamma_s, 'apoio')
    a = CondicaoAArmaduraApoio(mk_apoio_kncm, gamma_f * mk_apoio_kncm, a_flexao)

    fyd = aco.fyd(gamma_s)
    _numero('fyd_mpa', fyd)
    fyd_kn_cm2 = fyd * 0.1  # MPa -> kN/cm2; kN/(kN/cm2) -> cm2
    _numero('fyd_kn_cm2', fyd_kn_cm2)
    al = None
    fsd = None
    as_b = None
    md = gamma_f * mk_apoio_kncm
    vd = gamma_f * vk_apoio_kn
    _numero('vd_apoio_kn', vd, zero=True)
    if tipo_apoio == 'extremo':
        al = calcular_al(concreto=concreto, b_cm=secao.bw, d_cm=d,
                         vk_abs_kn=vk_apoio_kn, gamma_f=gamma_f, gamma_c=gamma_c)
        fsd = md / z + (al.al_cm / d) * vd + nd_tracao_kn
        as_b = fsd / fyd_kn_cm2
        _numero('fsd_kn', fsd, zero=True)
        _numero('as_b_cm2', as_b, zero=True)
    b = CondicaoBArmaduraApoio(tipo_apoio == 'extremo', al, fsd, as_b)

    vao = _dimensionar(secao_vao, concreto, aco, mk_positivo_max_vao_kncm,
                      d_vao_cm, d_linha_vao_cm, gamma_f, gamma_c, gamma_s, 'vao')
    razao = abs(mk_negativo_apoio_kncm) / mk_positivo_max_vao_kncm
    fracao = fracao_armadura_positiva_apoio(razao)
    c = CondicaoCArmaduraApoio(mk_positivo_max_vao_kncm, mk_negativo_apoio_kncm,
                             d_vao_cm, vao, razao, fracao,
                             'C1' if razao <= 0.5 else 'C2', fracao * vao.as_tracao)
    demandas = [('C', c.as_cm2)]
    if a.aplicavel:
        demandas.append(('A', a.as_cm2))
    if b.aplicavel:
        demandas.append(('B', b.as_cm2))
    area_necessaria = max(area for _, area in demandas)
    governantes = tuple(sorted(nome for nome, area in demandas if area == area_necessaria))
    avisos = list(resistente.avisos)
    if (a_flexao is not None and a_flexao.as_compressao > 0) or vao.as_compressao > 0:
        avisos.append('Dimensionamento exige armadura comprimida; sua existencia/detalhamento nao foi verificada.')
    return ResultadoArmaduraApoio(
        tipo_apoio=tipo_apoio, secao_apoio=secao, secao_vao=secao_vao,
        fck_mpa=concreto.fck, fyd_mpa=fyd, gamma_f=gamma_f, gamma_c=gamma_c,
        gamma_s=gamma_s, mk_apoio_kncm=mk_apoio_kncm, vk_apoio_kn=vk_apoio_kn,
        md_apoio_kncm=md, vd_apoio_kn=vd, nd_tracao_kn=nd_tracao_kn,
        d_linha_apoio_cm=d_linha_apoio_cm, d_linha_vao_cm=d_linha_vao_cm,
        as_por_camada_cm2=resistente.as_por_camada_cm2,
        d_por_camada_cm=resistente.d_por_camada_cm,
        d_cm=d, x_cm=x, z_cm=z, condicao_a=a, condicao_b=b, condicao_c=c,
        as_necessaria_cm2=area_necessaria, condicoes_governantes=governantes,
        avisos=tuple(avisos),
    )
