from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
from .armaduras import BarraPosicionada


@dataclass(frozen=True)
class ResultadoFlexao:
    as_tracao: float
    as_compressao: float
    area_concreto_comprimido: float
    linha_neutra: float
    dominio: int


@dataclass(frozen=True)
class ResultadoCortante:
    asw_por_s: float
    vc: float
    vrd2: float


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
