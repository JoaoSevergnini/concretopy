
from __future__ import annotations
from dataclasses import dataclass
from math import log

@dataclass(frozen=True)
class Concreto:
    fck: float

    def __post_init__(self) -> None:
        if not isinstance(self.fck, (int, float)):
            raise TypeError("fck deve ser numérico.")
        if self.fck < 20:
            raise ValueError("fck deve ser >= 20 MPa.")

    @property
    def fctm(self) -> float:
        if self.fck <= 50:
            return 0.3 * self.fck ** (2 / 3)
        return 2.12 * log(1 + 0.11 * self.fck)

    @property
    def fctk_inf(self) -> float:
        return 0.7 * self.fctm

    @property
    def fctk_sup(self) -> float:
        return 1.3 * self.fctm

    @property
    def eci(self) -> float:
        if self.fck <= 50:
            return 5600 * self.fck ** 0.5
        return 21500 * ((self.fck / 10) + 1.25) ** (1 / 3)

    @property
    def ecs(self) -> float:
        return self.eci * min(1.0, 0.8 + 0.2 * (self.fck / 80))

    @property
    def gc(self) -> float:
        return self.ecs / 2.4

    @property
    def poisson(self) -> float:
        return 0.2

    @property
    def ec2(self) -> float:
        if self.fck <= 50:
            return 2.0 / 1000
        return 2.0 / 1000 + 0.85 / 1000 * (self.fck - 50) ** 0.53

    @property
    def ecu(self) -> float:
        if self.fck <= 50:
            return 3.5 / 1000
        return 2.6 / 1000 + 3.5 / 1000 * ((90 - self.fck) / 100) ** 4

    @property
    def alfa_c(self) -> float:
        if self.fck <= 50:
            return 0.85
        return 0.85 * (1 - (self.fck - 50) / 200)

    @property
    def lamb(self) -> float:
        if self.fck <= 50:
            return 0.8
        return 0.8 - (self.fck - 50) / 400

    @property
    def alfa_v2(self) -> float:
        return 1 - self.fck / 250

    def fcd(self, gamma_c: float = 1.4) -> float:
        return self.fck / gamma_c

    def fctd(self, gamma_c: float = 1.4) -> float:
        return self.fctk_inf / gamma_c

@dataclass(frozen=True)
class Aco:
    fyk: float = 500.0
    es: float = 210000.0
    BITOLAS_MM = (5.0, 6.3, 8.0, 10.0, 12.5, 16.0, 20.0, 25.0)

    @property
    def ey(self) -> float:
        return self.fyk / self.es

    @property
    def eyu(self) -> float:
        return 10.0 / 1000

    def fyd(self, gamma_s: float = 1.15) -> float:
        return self.fyk / gamma_s
