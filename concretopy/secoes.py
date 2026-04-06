
from __future__ import annotations
from dataclasses import dataclass
from .armaduras import BarraPosicionada

@dataclass(frozen=True)
class SecaoRetangular:
    bw: float
    h: float
    cobrimento: float
    diametro_estribo_mm: float = 5.0

    def __post_init__(self) -> None:
        if self.bw <= 0 or self.h <= 0:
            raise ValueError("bw e h devem ser positivos.")
        if self.cobrimento < 0:
            raise ValueError("cobrimento deve ser >= 0.")

    @property
    def area(self) -> float:
        return self.bw * self.h

    @property
    def inercia(self) -> float:
        return self.bw * self.h ** 3 / 12

    @property
    def modulo_elastico(self) -> float:
        return self.inercia * 2 / self.h

    def d(self, diametro_barra_mm: float = 12.5) -> float:
        return self.h - self.cobrimento - self.diametro_estribo_mm / 10 - diametro_barra_mm / 20

    def d_linha(self, diametro_barra_mm: float = 12.5) -> float:
        return self.cobrimento + self.diametro_estribo_mm / 10 + diametro_barra_mm / 20

@dataclass(frozen=True)
class SecaoPoligonalArmada:
    contorno: list[list[float]]
    barras: list[BarraPosicionada]

    def __post_init__(self) -> None:
        if len(self.contorno) < 3:
            raise ValueError("A seção poligonal deve ter pelo menos 3 pontos.")
