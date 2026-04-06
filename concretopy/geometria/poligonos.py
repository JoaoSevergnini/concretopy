
from __future__ import annotations

def area_poligono(pontos: list[list[float]]) -> float:
    if len(pontos) == 0:
        return 0.0
    pontos_aux = list(pontos)
    pontos_aux.append(pontos[0])
    d1 = d2 = 0.0
    for i in range(len(pontos)):
        d1 += pontos_aux[i][0] * pontos_aux[i + 1][1]
        d2 += pontos_aux[i][1] * pontos_aux[i + 1][0]
    return abs(d1 - d2) / 2

def momento_primeira_ordem_x(pontos: list[list[float]]) -> float:
    if len(pontos) == 0:
        return 0.0
    pontos_aux = list(pontos)
    pontos_aux.append(pontos[0])
    s = 0.0
    for i in range(len(pontos)):
        dy = pontos_aux[i + 1][1] - pontos_aux[i][1]
        dx = pontos_aux[i + 1][0] - pontos_aux[i][0]
        s += dy * (3 * pontos_aux[i][0] * pontos_aux[i + 1][0] + dx ** 2)
    return s / 6

def momento_primeira_ordem_y(pontos: list[list[float]]) -> float:
    if len(pontos) == 0:
        return 0.0
    pontos_aux = list(pontos)
    pontos_aux.append(pontos[0])
    s = 0.0
    for i in range(len(pontos)):
        dy = pontos_aux[i + 1][1] - pontos_aux[i][1]
        dx = pontos_aux[i + 1][0] - pontos_aux[i][0]
        s += dx * (3 * pontos_aux[i][1] * pontos_aux[i + 1][1] + dy ** 2)
    return -s / 6
