from __future__ import annotations

from dataclasses import replace
from math import isfinite, isclose
from typing import Sequence

from ..armaduras import CamadaArmaduraLongitudinal
from ..exceptions import TaxaArmaduraExcedida
from ..materiais import Concreto, Aco
from ..normas.nbr6118 import taxa_armadura_min_viga
from ..resultados import ResultadoFlexao, ResultadoVerificacaoFlexao
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


def calcular_alturas_uteis_camadas(
    secao: SecaoRetangular,
    camadas: Sequence[CamadaArmaduraLongitudinal],
) -> tuple[float, ...]:
    """Resolve d em cm pelo critério VIGAS!K5:K7, preservando d explícitos.

    Ordene da camada junto à face tracionada para a face comprimida.
    A primeira camada omitida usa ``secao.d(phi_1)``. Nas seguintes:
    d_i = d_anterior - vao_livre - (phi_anterior + phi_i)/20,
    com vão livre de 2 cm para phi_i < 25 mm, ou phi_i/10 cm caso contrário.
    A regra usa a bitola da camada atual, exatamente como a planilha.
    Uma posição explícita ancora o cálculo da camada seguinte. Não altera
    as camadas originais nem certifica espaçamento normativo/geometria completa.
    """
    if not isinstance(secao, SecaoRetangular):
        raise TypeError("secao deve ser uma SecaoRetangular.")
    for nome, valor in (("h", secao.h), ("cobrimento", secao.cobrimento),
                        ("diametro_estribo_mm", secao.diametro_estribo_mm)):
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            raise TypeError(f"{nome} deve ser numérico.")
        if not isfinite(valor) or valor < 0 or (nome == "h" and valor == 0):
            raise ValueError(f"{nome} possui valor inválido.")
    camadas = tuple(camadas)
    if not camadas:
        raise ValueError("Informe pelo menos uma camada.")
    ds = []
    phi_anterior = None
    for camada in camadas:
        if not isinstance(camada, CamadaArmaduraLongitudinal):
            raise TypeError("Cada camada deve ser CamadaArmaduraLongitudinal.")
        phi = camada.barra.diametro_mm
        d = camada.d_cm
        if d is None:
            if not ds:
                d = secao.d(phi)
            else:
                vao_livre = phi / 10 if phi >= 25 else 2.0
                d = ds[-1] - vao_livre - phi_anterior / 20 - phi / 20
        if not isfinite(d) or d <= 0:
            raise ValueError("Altura útil calculada deve ser finita e positiva.")
        ds.append(d)
        phi_anterior = phi
    return tuple(ds)


def verificar_flexao_viga_retangular(
    secao: SecaoRetangular,
    concreto: Concreto,
    aco: Aco,
    camadas: Sequence[CamadaArmaduraLongitudinal],
    *,
    gamma_c: float = 1.4,
    gamma_s: float = 1.15,
    gamma_f: float | None = None,
    verificar_armadura_minima: bool = False,
) -> ResultadoVerificacaoFlexao:
    """Verifica a resistência de uma seção com camadas tracionadas conhecidas.

    Modelo: bloco retangular do ``Concreto`` e todas as camadas escoadas.
    ``d_cm`` de cada camada é medido da face comprimida ao centro da barra.
    Quando d é omitido, usa ``calcular_alturas_uteis_camadas``: informe
    camadas da face tracionada para a comprimida. Posições explícitas são
    preservadas. Não há dimensionamento ou truncamento de x.

    MRd é retornado em kN.cm somente se as hipóteses forem compatíveis com
    as deformações de cada camada. Ductilidade e mínimo são independentes
    da capacidade e não constituem aprovação global. ``gamma_f`` apenas
    solicita a transformação ``mk_equivalente_kncm = mrd_kncm / gamma_f``.
    Geometria/dados inválidos lançam ValueError ou TypeError; incompatibilidade
    do modelo retorna diagnóstico e momentos None. Ver documentação em
    ``.codex/analises/flexure_resistance_implementation.md``.
    """
    if not isinstance(secao, SecaoRetangular):
        raise TypeError("secao deve ser uma SecaoRetangular.")
    if not isinstance(concreto, Concreto) or not isinstance(aco, Aco):
        raise TypeError("Materiais devem ser Concreto e Aco.")
    if not isinstance(verificar_armadura_minima, bool):
        raise TypeError("verificar_armadura_minima deve ser booleano.")

    dados = {
        "bw": secao.bw, "h": secao.h, "cobrimento": secao.cobrimento,
        "diametro_estribo_mm": secao.diametro_estribo_mm,
        "fck": concreto.fck, "fyk": aco.fyk, "es": aco.es,
        "gamma_c": gamma_c, "gamma_s": gamma_s,
    }
    if gamma_f is not None:
        dados["gamma_f"] = gamma_f
    for nome, valor in dados.items():
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            raise TypeError(f"{nome} deve ser numérico.")
        if not isfinite(valor) or valor < 0 or (valor == 0 and nome != "cobrimento"):
            raise ValueError(f"{nome} deve ser finito e positivo (cobrimento pode ser zero).")
    if not 20 <= concreto.fck <= 90:
        raise ValueError("O modelo suporta 20 <= fck <= 90 MPa.")
    if not 0 < aco.fyd(gamma_s) / aco.es <= aco.eyu:
        raise ValueError("A deformação de escoamento deve ser positiva e <= eyu.")

    camadas = tuple(camadas)
    if not camadas:
        raise ValueError("Informe pelo menos uma camada tracionada.")
    if any(not isinstance(camada, CamadaArmaduraLongitudinal) for camada in camadas):
        raise TypeError("Cada camada deve ser CamadaArmaduraLongitudinal.")
    posicoes_automaticas = any(camada.d_cm is None for camada in camadas)
    if posicoes_automaticas:
        ds_calculados = calcular_alturas_uteis_camadas(secao, camadas)
        camadas = tuple(replace(camada, d_cm=d) for camada, d in zip(camadas, ds_calculados))
    for camada in camadas:
        if not isinstance(camada, CamadaArmaduraLongitudinal):
            raise TypeError("Cada camada deve ser CamadaArmaduraLongitudinal.")
        margem = secao.d_linha(camada.barra.diametro_mm)
        if not margem <= camada.d_cm <= secao.d(camada.barra.diametro_mm):
            raise ValueError("Camada fora da seção ou do cobrimento interno ao estribo.")
        largura_interna = secao.bw - 2 * (secao.cobrimento + secao.diametro_estribo_mm / 10)
        if camada.numero_barras * camada.barra.diametro_mm / 10 > largura_interna:
            raise ValueError("Barras da camada não cabem na largura interna da seção.")
    ordenadas = sorted(camadas, key=lambda camada: camada.d_cm)
    for anterior, atual in zip(ordenadas, ordenadas[1:]):
        if atual.d_cm - anterior.d_cm < (anterior.barra.diametro_mm + atual.barra.diametro_mm) / 20:
            raise ValueError("Camadas coincidentes ou com envelopes verticais sobrepostos.")

    areas = tuple(camada.area_cm2 for camada in camadas)
    ds = tuple(camada.d_cm for camada in camadas)
    as_total = sum(areas)
    d_eq = sum(area * d for area, d in zip(areas, ds)) / as_total
    fcd = concreto.fcd(gamma_c)
    fyd = aco.fyd(gamma_s)
    tracao = as_total * fyd * 0.1
    x = tracao / (concreto.alfa_c * fcd * 0.1 * secao.bw * concreto.lamb)
    x_d = x / d_eq
    limite = 0.45 if concreto.fck <= 50 else 0.35
    avisos = []
    if posicoes_automaticas:
        avisos.append("Alturas úteis omitidas calculadas pelo critério da planilha VIGAS!K5:K7.")
    deformacoes = None
    escoadas = None
    eps_c = None
    valido = x < min(ds) and x < secao.h and concreto.lamb * x <= secao.h
    if not valido:
        avisos.append("Linha neutra candidata fora do regime de todas as camadas tracionadas; MRd indisponível.")
    else:
        eps_c = min(concreto.ecu, aco.eyu * x / (max(ds) - x))
        deformacoes = tuple(eps_c * (d - x) / x for d in ds)
        eps_yd = fyd / aco.es
        escoadas = tuple(eps >= eps_yd or isclose(eps, eps_yd, rel_tol=1e-12, abs_tol=0.0) for eps in deformacoes)
        valido = all(escoadas)
        for i, escoou in enumerate(escoadas, start=1):
            if not escoou:
                avisos.append(f"Camada {i} não escoa no equilíbrio candidato; modelo de aço escoado inválido e MRd indisponível.")

    ductilidade = (x_d <= limite or isclose(x_d, limite, rel_tol=0.0, abs_tol=1e-12)) if valido else None
    if x_d > limite and not isclose(x_d, limite, rel_tol=0.0, abs_tol=1e-12):
        avisos.append("x/d equivalente candidato excede o limite de ductilidade; x não foi truncado.")
    mrd = tracao * (d_eq - concreto.lamb * x / 2) if valido else None
    mk_eq = mrd / gamma_f if mrd is not None and gamma_f is not None else None

    as_min = None
    minimo_atendido = None
    if verificar_armadura_minima:
        try:
            if not float(concreto.fck).is_integer():
                raise ValueError("fck não inteiro")
            as_min = taxa_armadura_min_viga(concreto.fck) * secao.area / 100
            minimo_atendido = as_total >= as_min
            if not minimo_atendido:
                avisos.append("Armadura fornecida inferior ao mínimo tabelado; a área usada em MRd foi preservada.")
        except ValueError:
            avisos.append("Verificação de armadura mínima indisponível: fck sem entrada inteira na tabela existente.")

    return ResultadoVerificacaoFlexao(
        as_total_cm2=as_total, as_por_camada_cm2=areas, d_por_camada_cm=ds,
        d_equivalente_cm=d_eq, linha_neutra_cm=x, x_sobre_d=x_d,
        limite_x_sobre_d=limite, ductilidade_atendida=ductilidade,
        mrd_kncm=mrd, mk_equivalente_kncm=mk_eq, hipoteses_validas=valido,
        deformacoes_aco=deformacoes, camadas_escoadas=escoadas,
        as_min_cm2=as_min, armadura_minima_atendida=minimo_atendido,
        parametros={
            "modelo": "bloco_retangular_camadas_escoadas_v1",
            "unidade_momento": "kN.cm", "unidade_tensao": "MPa",
            "gamma_c": gamma_c, "gamma_s": gamma_s, "gamma_f": gamma_f,
            "fck": concreto.fck, "fyk": aco.fyk, "es": aco.es,
            "fcd": fcd, "fyd": fyd, "alfa_c": concreto.alfa_c,
            "lambda": concreto.lamb, "ecu": concreto.ecu, "eyu": aco.eyu,
            "eyd": fyd / aco.es, "eps_c_adotada": eps_c,
            "bw_cm": secao.bw, "h_cm": secao.h,
            "cobrimento_cm": secao.cobrimento,
            "diametro_estribo_mm": secao.diametro_estribo_mm,
        },
        avisos=tuple(avisos),
    )
