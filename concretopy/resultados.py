from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
from .armaduras import BarraPosicionada
from .secoes import SecaoRetangular


@dataclass(frozen=True)
class ResultadoFlexao:
    as_tracao: float
    as_compressao: float
    area_concreto_comprimido: float
    linha_neutra: float
    dominio: int


@dataclass(frozen=True)
class ResultadoVerificacaoFlexao:
    """Resistência de cálculo; não representa aprovação global do detalhamento.

    Áreas em cm², comprimentos em cm e momentos em kN.cm. ``linha_neutra_cm``
    e ``x_sobre_d`` são candidatos de equilíbrio com aço escoado quando
    ``hipoteses_validas`` é falso; nesse caso os momentos são ``None``.
    Deformações são adimensionais. Parâmetros de tensão são dados em MPa.
    """

    as_total_cm2: float
    as_por_camada_cm2: tuple[float, ...]
    d_por_camada_cm: tuple[float, ...]
    d_equivalente_cm: float
    linha_neutra_cm: float
    x_sobre_d: float
    limite_x_sobre_d: float
    ductilidade_atendida: bool | None
    mrd_kncm: float | None
    mk_equivalente_kncm: float | None
    hipoteses_validas: bool
    deformacoes_aco: tuple[float, ...] | None
    camadas_escoadas: tuple[bool, ...] | None
    as_min_cm2: float | None
    armadura_minima_atendida: bool | None
    parametros: dict[str, float | str | None]
    avisos: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResultadoCortante:
    asw_por_s: float
    vc: float
    vrd2: float
    # Additive cm²/m components; legacy construction/equality remain valid.
    asw_por_s_calculado: float | None = field(default=None, compare=False)
    asw_por_s_minimo: float | None = field(default=None, compare=False)


@dataclass(frozen=True)
class OpcaoBitola:
    diametro_mm: float
    numero_barras: int
    area_fornecida_cm2: float


@dataclass(frozen=True)
class LayoutBarras:
    barras: List[BarraPosicionada]
    camadas_superiores: list[tuple[int, float]]
    camadas_inferiores: list[tuple[int, float]]


@dataclass(frozen=True)
class ResultadoFlexoCompressao:
    nd_resistente: float
    mxd_resistente: float
    myd_resistente: float
    inclinacao_linha_neutra_graus: float
    linha_neutra: float
    residual_equilibrio: float = 0.0
    convergiu: bool = True


@dataclass(frozen=True)
class ResultadoReforcoFuro:
    asw_banzo_comprimido: float | None
    asw_banzo_tracionado: float | None
    as_suspensao: float
    armadura_longitudinal: list[tuple[int, float]] | None
    configuracao_estribos_banzo_comprimido: dict[float, int] | None
    configuracao_estribos_banzo_tracionado: dict[float, int] | None
    configuracao_armadura_suspensao: dict[float, int]
    avisos: list[str] = field(default_factory=list)
    memorial: str = ''
    verificacao_dimensoes_norma: bool = True
    resistencia_biela_equivalente_kn: float | None = None


@dataclass(frozen=True)
class ResultadoAncoragem:
    """Ancoragem de barra nervurada tracionada, sem gancho (9.4.2).

    fctd_mpa, fyd_mpa, fbd_mpa : float
        Resistencias de calculo do concreto a tracao, aco e aderencia, em MPa.
    eta1, eta2, eta3 : float
        Coeficientes de aderencia adimensionais.
    lb_cm, lb_min_cm, lb_nec_cm : float
        Comprimentos basico, minimo e necessario, em cm.
    comprimento_disponivel_cm : float | None
        Comprimento reto disponivel em cm; None quando nao informado.
    atende : bool | None
        Compara apenas comprimento disponivel >= lb_nec_cm, sem unidade.
        None quando nao ha comprimento disponivel. Nao aprova detalhamento
        global, cobrimento, confinamento ou resistencia da secao.
    """

    fctd_mpa: float
    fyd_mpa: float
    eta1: float
    eta2: float
    eta3: float
    fbd_mpa: float
    lb_cm: float
    lb_min_cm: float
    lb_nec_cm: float
    comprimento_disponivel_cm: float | None
    atende: bool | None


@dataclass(frozen=True)
class ResultadoDecalagemAl:
    """Decalagem independente da ancoragem, com intermediarios auditaveis.

    vk_abs_kn, vsd_kn, vc0_kn: magnitude caracteristica, cortante de calculo
    e contribuicao Vc0, em kN. gamma_f/gamma_c sao adimensionais.
    b_cm/d_cm sao largura e altura util, em cm; fctd_mpa e resistencia de
    calculo a tracao, em MPa. al_base_cm conserva o valor antes dos limites;
    al_min_cm/al_max_cm/al_cm sao comprimentos em cm. branch identifica
    'vsd_le_vc0' ou 'vsd_gt_vc0'. Nao representa aprovacao de resistencia,
    ancoragem, apoio ou corte de barras. Hipotese: estribos verticais, Vc=Vc0.
    """

    vk_abs_kn: float
    gamma_f: float
    gamma_c: float
    vsd_kn: float
    b_cm: float
    d_cm: float
    fctd_mpa: float
    vc0_kn: float
    al_base_cm: float
    al_min_cm: float
    al_max_cm: float
    al_cm: float
    branch: str


@dataclass(frozen=True)
class CondicaoAArmaduraApoio:
    """Condicao a: momentos em kN.cm e dimensionamento em cm2/cm.

    dimensionamento=None significa condicao nao aplicavel (Mk positivo zero).
    A propriedade as_cm2 e a demanda calculada, nao a area detalhada.
    """

    mk_kncm: float
    md_kncm: float
    dimensionamento: ResultadoFlexao | None

    @property
    def aplicavel(self) -> bool:
        return self.dimensionamento is not None

    @property
    def as_cm2(self) -> float | None:
        return None if self.dimensionamento is None else self.dimensionamento.as_tracao


@dataclass(frozen=True)
class CondicaoBArmaduraApoio:
    """Condicao b para o unico par Mk/Vk recebido, apenas em apoio extremo.

    decalagem preserva Vk/Vd em kN e al/d em cm. fsd_kn em kN e as_cm2
    em cm2. Todos sao None quando nao aplicavel; nao seleciona esforcos.
    """

    aplicavel: bool
    decalagem: ResultadoDecalagemAl | None
    fsd_kn: float | None
    as_cm2: float | None


@dataclass(frozen=True)
class CondicaoCArmaduraApoio:
    """Condicao c independente de momento positivo no apoio.

    Momentos em kN.cm, alturas em cm; razao/fracao adimensionais.
    dimensionamento_vao preserva a demanda de flexao (cm2), inclusive minimo
    e eventual armadura comprimida. criterio e C1 ou C2.
    """

    mk_positivo_max_vao_kncm: float
    mk_negativo_apoio_kncm: float
    d_vao_cm: float
    dimensionamento_vao: ResultadoFlexao
    razao_momentos: float
    fracao: float
    criterio: str
    as_cm2: float

    @property
    def aplicavel(self) -> bool:
        return True

    @property
    def as_vao_cm2(self) -> float:
        return self.dimensionamento_vao.as_tracao


@dataclass(frozen=True)
class ResultadoArmaduraApoio:
    """Demanda de armadura positiva no apoio, sem aprovacao do detalhamento.

    d_cm/x_cm/z_cm e d_por_camada_cm em cm; areas em cm2; fyd_mpa/fck_mpa
    em MPa. Cortantes caracteristicos sao magnitudes em kN. Coeficientes
    adimensionais. x vem da analise resistente das camadas que chegam ao
    apoio; z=d-x/2 e a simplificacao de engenharia deste procedimento.
    condicoes_governantes registra empates exatos. avisos conserva os
    diagnosticos da analise resistente, sem campo atende.
    """

    tipo_apoio: str
    secao_apoio: SecaoRetangular
    secao_vao: SecaoRetangular
    fck_mpa: float
    fyd_mpa: float
    gamma_f: float
    gamma_c: float
    gamma_s: float
    mk_apoio_kncm: float
    vk_apoio_kn: float
    md_apoio_kncm: float
    vd_apoio_kn: float
    nd_tracao_kn: float
    d_linha_apoio_cm: float | None
    d_linha_vao_cm: float | None
    as_por_camada_cm2: tuple[float, ...]
    d_por_camada_cm: tuple[float, ...]
    d_cm: float
    x_cm: float
    z_cm: float
    condicao_a: CondicaoAArmaduraApoio
    condicao_b: CondicaoBArmaduraApoio
    condicao_c: CondicaoCArmaduraApoio
    as_necessaria_cm2: float
    condicoes_governantes: tuple[str, ...]
    avisos: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResultadoVerificacaoAncoragemApoio:
    """Area e comprimento de ancoragem positiva no apoio extremo.

    fctd_mpa/fyd_mpa/fbd_mpa em MPa; eta1/eta2/eta3, alpha e gammas
    adimensionais. Bitola em mm; areas em cm2; todos os comprimentos em cm.
    lb_nec_sem_min_cm preserva a parcela variavel antes de lb_min_cm.
    as_corr_matematica_cm2 e a inversao apenas dessa parcela; as_corr_cm2
    nunca fica abaixo da demanda. as_adicional_cm2 nao identifica grampos.
    comprimento_menor_lb_min impede atendimento mesmo que se aumente area.
    Gancho e aderencia sao condicoes informadas, nao validadas geometricamente.
    """

    bitola_mm: float
    boa_aderencia: bool
    gancho_valido: bool
    gamma_c: float
    gamma_s: float
    fctd_mpa: float
    fyd_mpa: float
    eta1: float
    eta2: float
    eta3: float
    fbd_mpa: float
    lb_cm: float
    lb_min_cm: float
    alpha: float
    as_calculada_cm2: float
    as_efetiva_cm2: float
    lb_nec_sem_min_cm: float
    lb_nec_cm: float
    comprimento_disponivel_cm: float
    area_suficiente: bool
    comprimento_suficiente: bool
    comprimento_menor_lb_min: bool
    atende: bool
    as_corr_matematica_cm2: float
    as_corr_cm2: float
    as_adicional_cm2: float
    avisos: tuple[str, ...] = ()
