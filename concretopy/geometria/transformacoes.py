
from __future__ import annotations
import math

def rotacionar_ponto(ponto: list[float], inclinacao_graus: float) -> list[float]:
    x, y = ponto
    alfa = inclinacao_graus * math.pi / 180
    xr = x * math.cos(alfa) + y * math.sin(alfa)
    yr = -x * math.sin(alfa) + y * math.cos(alfa)
    return [xr, yr]

def transladar_pontos(pontos: list[list[float]], nova_origem: list[float]) -> list[list[float]]:
    return [[p[0] - nova_origem[0], p[1] - nova_origem[1]] for p in pontos]
