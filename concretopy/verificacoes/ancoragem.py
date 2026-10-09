"""Ancoragem reta de barras nervuradas tracionadas de armadura passiva.

NBR 6118:2023, 9.3.2.1, 9.4.2.4 e 9.4.2.5, conforme trechos fornecidos.
A primitiva reta nao inclui gancho; a verificacao de apoio aceita gancho
validado pelo chamador. Nao inclui soldas, compressao ou traspasse.
A classificacao geometrica da aderencia (9.3.1) cabe ao usuario.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from ..materiais import Aco, Concreto
from ..normas.nbr6118 import (
    ETA1_BARRA_NERVURADA,
    coeficiente_alpha_ancoragem_apoio,
    coeficiente_aderencia_eta2,
    coeficiente_aderencia_eta3,
    comprimento_minimo_ancoragem_cm,
    limite_inferior_lb_cm,
)
from ..resultados import ResultadoAncoragem, ResultadoVerificacaoAncoragemApoio


@dataclass(frozen=True)
class CondicoesAncoragem:
    """Aderencia de barra nervurada tracionada; gancho e dado da verificacao.

    boa_aderencia : bool
        True para boa aderencia; False para ma aderencia (adimensional).
        Obrigatorio: o usuario classifica a posicao conforme 9.3.1.
        Nao ha escolha automatica pela geometria nem valor padrao.
    """

    boa_aderencia: bool

    def __post_init__(self) -> None:
        if not isinstance(self.boa_aderencia, bool):
            raise TypeError("boa_aderencia deve ser booleano.")


def _validar_numero(nome: str, valor: float, *, permite_zero: bool = False) -> None:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise TypeError(f"{nome} deve ser numerico.")
    if not isfinite(valor) or valor < 0 or (valor == 0 and not permite_zero):
        raise ValueError(f"{nome} deve ser finito e {'nao negativo' if permite_zero else 'positivo'}.")


def calcular_ancoragem(
    concreto: Concreto,
    aco: Aco,
    bitola_mm: float,
    as_calculada_cm2: float,
    as_efetiva_cm2: float,
    *,
    condicoes: CondicoesAncoragem,
    comprimento_disponivel_cm: float | None = None,
    gamma_c: float = 1.4,
    gamma_s: float = 1.15,
) -> ResultadoAncoragem:
    """Calcula ancoragem reta sem gancho, com alfa = 1 (9.4.2.5).

    concreto : Concreto
        Material existente; fck em MPa. Escopo do modulo: 20 a 90 MPa.
        Reutiliza Concreto.fctd, incluindo a expressao para fck > 50 MPa.
    aco : Aco
        Material existente; fyk em MPa. Admite exclusivamente barra nervurada.
    bitola_mm : float
        Diametro nominal da barra, em mm; pode usar Barra.diametro_mm.
        Deve ser positivo e produzir eta3 positivo; nao limita ao catalogo.
    as_calculada_cm2 : float
        Area de aco necessaria a ancorar, em cm2, finita e positiva.
    as_efetiva_cm2 : float
        Area efetivamente disponivel para ancorar essa solicitacao, em cm2,
        finita, positiva e >= as_calculada_cm2. Nao e a area de outras barras
        que nao participam da ancoragem analisada.
    condicoes : CondicoesAncoragem
        Classificacao explicita de aderencia, sem unidade.
    comprimento_disponivel_cm : float | None
        Comprimento reto disponivel, em cm, finito e >= 0; None omite a
        verificacao. Medido a partir da secao onde se deve ancorar a forca;
        nao inclui automaticamente decalagem nem comprimento de gancho.
    gamma_c, gamma_s : float
        Coeficientes parciais adimensionais, finitos e positivos.
        Padroes 1,4 e 1,15 reutilizam a convencao dos materiais do pacote.

    Returns
    -------
    ResultadoAncoragem
        Resistencias em MPa, coeficientes adimensionais e comprimentos em cm.
        lb = max(phi_cm/4 * fyd/fbd, 25 phi_cm), conforme 9.4.2.4;
        lb_min = max(0,3 lb, 10 phi_cm, 10 cm), conforme 9.4.2.5;
        lb_nec = max(lb * As_calculada/As_efetiva, lb_min), com alfa = 1.
        atende e None sem comprimento, ou resultado da comparacao >=.

    Raises
    ------
    TypeError
        Tipos invalidos, incluindo booleanos usados como numeros.
    ValueError
        Dados nao finitos, fora do dominio ou areas incompativeis.
        Area insuficiente nao pode ser compensada aumentando a ancoragem.
        Comprimento disponivel insuficiente retorna atende=False.
    """
    if not isinstance(concreto, Concreto) or not isinstance(aco, Aco):
        raise TypeError("Materiais devem ser Concreto e Aco.")
    if not isinstance(condicoes, CondicoesAncoragem):
        raise TypeError("condicoes deve ser CondicoesAncoragem.")
    for nome, valor in (
        ("fck", concreto.fck), ("fyk", aco.fyk),
        ("bitola_mm", bitola_mm), ("as_calculada_cm2", as_calculada_cm2),
        ("as_efetiva_cm2", as_efetiva_cm2), ("gamma_c", gamma_c),
        ("gamma_s", gamma_s),
    ):
        _validar_numero(nome, valor)
    if not 20 <= concreto.fck <= 90:
        raise ValueError("O modulo suporta 20 <= fck <= 90 MPa.")
    if as_calculada_cm2 > as_efetiva_cm2:
        raise ValueError("as_efetiva_cm2 deve ser >= as_calculada_cm2.")
    if comprimento_disponivel_cm is not None:
        _validar_numero("comprimento_disponivel_cm", comprimento_disponivel_cm, permite_zero=True)

    # Nivel 1: resistencias em MPa e coeficientes adimensionais.
    fctd = concreto.fctd(gamma_c)
    fyd = aco.fyd(gamma_s)
    eta1 = ETA1_BARRA_NERVURADA
    eta2 = coeficiente_aderencia_eta2(condicoes.boa_aderencia)
    eta3 = coeficiente_aderencia_eta3(bitola_mm)
    fbd = eta1 * eta2 * eta3 * fctd
    for nome, valor in (("fctd", fctd), ("fyd", fyd), ("fbd", fbd)):
        _validar_numero(nome, valor)

    # Nivel 2: mm -> cm explicito; MPa/MPa e adimensional.
    phi_cm = bitola_mm / 10.0
    lb = max(phi_cm / 4.0 * (fyd / fbd), limite_inferior_lb_cm(bitola_mm))
    lb_min = comprimento_minimo_ancoragem_cm(lb, bitola_mm)
    lb_nec = max(lb * (as_calculada_cm2 / as_efetiva_cm2), lb_min)

    # Nivel 3: comparacao de comprimentos, sem arredondamento.
    atende = None if comprimento_disponivel_cm is None else comprimento_disponivel_cm >= lb_nec
    return ResultadoAncoragem(
        fctd_mpa=fctd, fyd_mpa=fyd, eta1=eta1, eta2=eta2, eta3=eta3,
        fbd_mpa=fbd, lb_cm=lb, lb_min_cm=lb_min, lb_nec_cm=lb_nec,
        comprimento_disponivel_cm=comprimento_disponivel_cm, atende=atende,
    )



def verificar_ancoragem_positiva_apoio(
    *,
    concreto: Concreto,
    aco: Aco,
    bitola_mm: float,
    as_calculada_cm2: float,
    as_efetiva_cm2: float,
    condicoes: CondicoesAncoragem,
    comprimento_disponivel_cm: float,
    gancho_valido: bool,
    gamma_c: float = 1.4,
    gamma_s: float = 1.15,
) -> ResultadoVerificacaoAncoragemApoio:
    """Verifica area/comprimento e calcula area inversa no apoio extremo.

    concreto, aco : Concreto, Aco
        Materiais existentes; resistencias em MPa. Herda dominio de concreto
        (20 a 90 MPa), tipo de barra nervurada e regras de calcular_ancoragem.
    bitola_mm : float
        Diametro nominal da barra ancorada, em mm, finito e positivo.
        Configuracoes com bitolas diferentes exigem verificacoes especificas.
    as_calculada_cm2 : float
        Demanda estrutural a ancorar, em cm2, finita e positiva. Selecionar
        eventual demanda governante entre chamadas de apoio cabe ao chamador.
    as_efetiva_cm2 : float
        Area das barras que chegam ao apoio e participam da ancoragem,
        em cm2, finita e positiva. Pode ser menor que a demanda: retorna
        area_suficiente=False em vez de rejeitar essa configuracao fisica.
    condicoes : CondicoesAncoragem
        Boa/ma aderencia informada pelo chamador, sem unidade.
    comprimento_disponivel_cm : float
        Comprimento de ancoragem disponivel em cm, finito e estritamente
        positivo, recebido diretamente. Nao deduz comprimento de apoio ou
        cobrimento. Zero e rejeitado porque o calculo inverso e indefinido.
        Abaixo de lb_min, preserva todos os calculos e retorna advertencia.
    gancho_valido : bool
        True permite alpha=0,7; False usa alpha=1,0 (adimensional).
        O chamador verifica previamente condicoes normativas e geometria do
        gancho, incluindo o cobrimento aplicavel de 9.4.2.5.
    gamma_c, gamma_s : float
        Coeficientes parciais adimensionais, finitos e positivos. Padroes
        1,4 e 1,15 conforme os materiais/primitiva existentes.

    Returns
    -------
    ResultadoVerificacaoAncoragemApoio
        Comprimentos em cm, areas em cm2, resistencias em MPa. Preserva
        lb, lb_min, alpha, parcela variavel, lb_nec e comprimento disponivel.
        Diagnosticos distintos de area, comprimento e limite minimo.
        As_corr_matematica=alpha*lb*As_calculada/comprimento_disponivel;
        As_corr=max(As_calculada, As_corr_matematica);
        As_adicional=max(0, As_corr-As_efetiva).
        Aumento de area nao supera falta de comprimento frente a lb_min.

    Notes
    -----
    Compoe a primitiva calcular_ancoragem com areas iguais (razao unitaria)
    apenas para obter propriedades, lb e lb_min, sem duplicar suas formulas.
    Depois aplica a configuracao real: lb_nec_sem_min=alpha*lb*As_calc/As_ef;
    lb_nec=max(lb_nec_sem_min,lb_min). atende exige area suficiente, comprimento
    suficiente e comprimento nao inferior a lb_min. Nao decide detalhamento,
    nao calcula grampos, nao soma al nem faz geometria de comprimento/gancho.
    As_corr e uma area hipotetica mantendo bitola e demais parametros desta
    chamada; mudar bitola/gancho exige recalcular a verificacao.

    Raises
    ------
    TypeError, ValueError
        Tipos invalidos, numeros nao finitos, entradas fora do dominio ou
        resultados nao representaveis. Insuficiencia estrutural de area ou
        comprimento positivo nao gera excecao.
    """
    for nome, valor in (("as_calculada_cm2", as_calculada_cm2),
                        ("as_efetiva_cm2", as_efetiva_cm2),
                        ("comprimento_disponivel_cm", comprimento_disponivel_cm)):
        _validar_numero(nome, valor)
    alpha = coeficiente_alpha_ancoragem_apoio(gancho_valido)
    basico = calcular_ancoragem(
        concreto=concreto, aco=aco, bitola_mm=bitola_mm,
        as_calculada_cm2=as_calculada_cm2, as_efetiva_cm2=as_calculada_cm2,
        condicoes=condicoes, gamma_c=gamma_c, gamma_s=gamma_s,
    )
    lb_alpha = alpha * basico.lb_cm
    lb_nec_sem_min = lb_alpha * (as_calculada_cm2 / as_efetiva_cm2)
    lb_nec = max(lb_nec_sem_min, basico.lb_min_cm)
    as_corr_matematica = (lb_alpha / comprimento_disponivel_cm) * as_calculada_cm2
    as_corr = max(as_calculada_cm2, as_corr_matematica)
    as_adicional = max(0.0, as_corr - as_efetiva_cm2)
    for nome, valor in (("lb_cm", basico.lb_cm), ("lb_min_cm", basico.lb_min_cm),
                        ("lb_nec_sem_min_cm", lb_nec_sem_min), ("lb_nec_cm", lb_nec),
                        ("as_corr_matematica_cm2", as_corr_matematica),
                        ("as_corr_cm2", as_corr), ("as_adicional_cm2", as_adicional)):
        _validar_numero(nome, valor, permite_zero=nome == 'as_adicional_cm2')

    area_suficiente = as_efetiva_cm2 >= as_calculada_cm2
    comprimento_suficiente = comprimento_disponivel_cm >= lb_nec
    menor_minimo = comprimento_disponivel_cm < basico.lb_min_cm
    avisos = []
    if not area_suficiente:
        avisos.append('Area efetiva inferior a demanda estrutural, independentemente do comprimento.')
    if not comprimento_suficiente:
        avisos.append('Comprimento disponivel inferior ao comprimento necessario de ancoragem.')
    if menor_minimo:
        avisos.append('Comprimento abaixo de lb_min: aumentar area sozinho nao torna a ancoragem atendente; As_corr refere-se a parcela variavel.')
    return ResultadoVerificacaoAncoragemApoio(
        bitola_mm=bitola_mm, boa_aderencia=condicoes.boa_aderencia,
        gancho_valido=gancho_valido, gamma_c=gamma_c, gamma_s=gamma_s,
        fctd_mpa=basico.fctd_mpa, fyd_mpa=basico.fyd_mpa,
        eta1=basico.eta1, eta2=basico.eta2, eta3=basico.eta3, fbd_mpa=basico.fbd_mpa,
        lb_cm=basico.lb_cm, lb_min_cm=basico.lb_min_cm, alpha=alpha,
        as_calculada_cm2=as_calculada_cm2, as_efetiva_cm2=as_efetiva_cm2,
        lb_nec_sem_min_cm=lb_nec_sem_min, lb_nec_cm=lb_nec,
        comprimento_disponivel_cm=comprimento_disponivel_cm,
        area_suficiente=area_suficiente, comprimento_suficiente=comprimento_suficiente,
        comprimento_menor_lb_min=menor_minimo,
        atende=area_suficiente and comprimento_suficiente and not menor_minimo,
        as_corr_matematica_cm2=as_corr_matematica,
        as_corr_cm2=as_corr, as_adicional_cm2=as_adicional, avisos=tuple(avisos),
    )
