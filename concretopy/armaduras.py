
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite, pi

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


@dataclass(frozen=True)
class CamadaArmaduraLongitudinal:
    """Camada de barras iguais, com centro a ``d_cm`` da face comprimida.

    ``d_cm=None`` solicita posicionamento pelo critério da planilha na
    verificação retangular. O diâmetro é o da ``Barra`` existente, em mm.
    """

    numero_barras: int
    barra: Barra
    d_cm: float | None = None

    def __post_init__(self) -> None:
        if isinstance(self.numero_barras, bool) or not isinstance(self.numero_barras, int):
            raise TypeError("numero_barras deve ser inteiro.")
        if self.numero_barras <= 0:
            raise ValueError("numero_barras deve ser positivo.")
        if not isinstance(self.barra, Barra):
            raise TypeError("barra deve ser uma Barra.")
        for nome, valor in (("diametro_mm", self.barra.diametro_mm), ("d_cm", self.d_cm)):
            if nome == "d_cm" and valor is None:
                continue
            if isinstance(valor, bool) or not isinstance(valor, (int, float)):
                raise TypeError(f"{nome} deve ser numérico.")
            if not isfinite(valor) or valor <= 0:
                raise ValueError(f"{nome} deve ser finito e positivo.")

    @property
    def area_cm2(self) -> float:
        return self.numero_barras * self.barra.area_cm2
