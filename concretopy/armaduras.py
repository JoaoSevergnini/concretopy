
from __future__ import annotations
from dataclasses import dataclass
from math import pi

@dataclass(frozen=True)
class Barra:
    diametro_mm: float

    @property
    def area_cm2(self) -> float:
        return pi * (self.diametro_mm / 10) ** 2 / 4

@dataclass(frozen=True)
class BarraPosicionada:
    x: float
    y: float
    diametro_mm: float

    @property
    def area_cm2(self) -> float:
        return pi * (self.diametro_mm / 10) ** 2 / 4

@dataclass(frozen=True)
class Armadura:
    barra: Barra
    espacamento: float
    numero: int
    cobrimento: float

    @property
    def area_cm2(self) -> float:
        return self.barra.area_cm2 * self.numero