"""Decalagem deterministica para estribos verticais e Vc = Vc0.

Equacao confirmada pelo engenheiro e auditada em VIGAS!R26/I21.
O trecho normativo fornecido inclui cotg(alfa); aqui alfa = 90 graus.
Nao seleciona esforcos, classifica regioes ou verifica resistencia ao cortante.
"""
from __future__ import annotations

from math import isfinite

from ..materiais import Concreto
from ..resultados import ResultadoDecalagemAl


def _validar(nome: str, valor: float, *, zero: bool = False) -> None:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise TypeError(f"{nome} deve ser numerico.")
    if not isfinite(valor) or valor < 0 or (valor == 0 and not zero):
        raise ValueError(f"{nome} deve ser finito e {'nao negativo' if zero else 'positivo'}.")


def calcular_al(
    *,
    concreto: Concreto,
    b_cm: float,
    d_cm: float,
    vk_abs_kn: float,
    gamma_f: float = 1.4,
    gamma_c: float = 1.4,
) -> ResultadoDecalagemAl:
    """Calcula al_base e al limitado a [0,5 d; d], em cm.

    concreto : Concreto
        Concreto existente, com fck entre 20 e 90 MPa. Reutiliza fctd.
    b_cm : float
        Largura resistente ao cortante, em cm, finita e positiva.
    d_cm : float
        Altura util em cm, finita e positiva, explicitamente escolhida pelo
        chamador. A mesma altura e usada em Vc0, al_base e nos limites.
    vk_abs_kn : float
        Magnitude do cortante caracteristico em kN, finita e nao negativa.
        Zero e valido; negativos sao rejeitados, sem aplicar abs().
        A origem e a selecao do esforco sao responsabilidade do chamador.
    gamma_f : float
        Coeficiente de majoracao do cortante, adimensional e positivo.
    gamma_c : float
        Coeficiente parcial do concreto, adimensional e positivo, passado
        a Concreto.fctd. Ambos os coeficientes devem ser finitos.

    Returns
    -------
    ResultadoDecalagemAl
        Entradas, fctd em MPa, Vsd/Vc0 em kN, al_base, limites e al em cm,
        e branch ('vsd_le_vc0' ou 'vsd_gt_vc0').

    Notes
    -----
    Vsd = gamma_f * Vk; Vc0 = 0,6 * (fctd * 0,1) * b * d.
    A conversao explicita e 1 MPa = 0,1 kN/cm2. Para Vsd <= Vc0,
    al_base = d; caso contrario, al_base = 0,5*d*Vsd/(Vsd-Vc0).
    al = max(min(al_base, d), 0,5*d). Nao compoe al com lb/lb_nec.
    Escopo: estribos verticais, Vc adotado igual a Vc0. Nao aplica a
    variante de estribos a 45 graus nem efeitos de esforco normal sobre Vc.
    Nao verifica Vrd2: calcular al nao significa aprovar resistencia.

    Raises
    ------
    TypeError
        Tipos invalidos, incluindo booleanos no lugar de numeros.
    ValueError
        Dados fora do dominio ou resultados nao representaveis como
        numeros finitos positivos (Vsd pode ser zero).
    """
    if not isinstance(concreto, Concreto):
        raise TypeError("concreto deve ser Concreto.")
    for nome, valor in (("b_cm", b_cm), ("d_cm", d_cm),
                        ("gamma_f", gamma_f), ("gamma_c", gamma_c),
                        ("fck", concreto.fck)):
        _validar(nome, valor)
    _validar("vk_abs_kn", vk_abs_kn, zero=True)
    if not 20 <= concreto.fck <= 90:
        raise ValueError("O modulo suporta 20 <= fck <= 90 MPa.")

    fctd_mpa = concreto.fctd(gamma_c)
    _validar("fctd_mpa", fctd_mpa)
    fctd_kn_cm2 = fctd_mpa * 0.1  # MPa -> kN/cm2
    vc0_kn = 0.6 * fctd_kn_cm2 * b_cm * d_cm
    vsd_kn = gamma_f * vk_abs_kn
    _validar("vc0_kn", vc0_kn)
    _validar("vsd_kn", vsd_kn, zero=True)

    al_min_cm = 0.5 * d_cm
    al_max_cm = d_cm
    if vsd_kn <= vc0_kn:
        branch = "vsd_le_vc0"
        al_base_cm = d_cm
    else:
        branch = "vsd_gt_vc0"
        # Razao antes do produto evita overflow desnecessario em d*Vsd.
        al_base_cm = (0.5 * d_cm) * (vsd_kn / (vsd_kn - vc0_kn))
    _validar("al_base_cm", al_base_cm)
    _validar("al_min_cm", al_min_cm)
    al_cm = max(min(al_base_cm, al_max_cm), al_min_cm)
    return ResultadoDecalagemAl(
        vk_abs_kn=vk_abs_kn, gamma_f=gamma_f, gamma_c=gamma_c,
        vsd_kn=vsd_kn, b_cm=b_cm, d_cm=d_cm, fctd_mpa=fctd_mpa,
        vc0_kn=vc0_kn, al_base_cm=al_base_cm, al_min_cm=al_min_cm,
        al_max_cm=al_max_cm, al_cm=al_cm, branch=branch,
    )
