
from __future__ import annotations
from ..armaduras import BarraPosicionada
from ..resultados import LayoutBarras
from ..secoes import SecaoRetangular

def coordenadas_barras_retangulares(
    secao: SecaoRetangular,
    camadas_superiores: list[tuple[int, float]],
    camadas_inferiores: list[tuple[int, float]],
    delta_cm: float = 0.8,
) -> LayoutBarras:
    barras = []

    if camadas_superiores:
        y0 = secao.h - (secao.cobrimento + delta_cm + camadas_superiores[0][1] / 20)
        dy = camadas_superiores[0][1] / 10 + 2
        x0 = secao.cobrimento + delta_cm + camadas_superiores[0][1] / 20
        y = y0
        for n_barras, bitola_mm in camadas_superiores:
            if n_barras == 1:
                barras.append(BarraPosicionada(x0, y, bitola_mm))
            else:
                dx = (secao.bw - (2 * (secao.cobrimento + delta_cm) + bitola_mm / 10)) / (n_barras - 1)
                x = x0
                for _ in range(n_barras):
                    barras.append(BarraPosicionada(x, y, bitola_mm))
                    x += dx
            y -= dy

    if camadas_inferiores:
        y0 = secao.cobrimento + delta_cm + camadas_inferiores[0][1] / 20
        dy = camadas_inferiores[0][1] / 10 + 2
        x0 = secao.cobrimento + delta_cm + camadas_inferiores[0][1] / 20
        y = y0
        for n_barras, bitola_mm in camadas_inferiores:
            if n_barras == 1:
                barras.append(BarraPosicionada(x0, y, bitola_mm))
            else:
                dx = (secao.bw - (2 * (secao.cobrimento + delta_cm) + bitola_mm / 10)) / (n_barras - 1)
                x = x0
                for _ in range(n_barras):
                    barras.append(BarraPosicionada(x, y, bitola_mm))
                    x += dx
            y += dy

    return LayoutBarras(barras, camadas_superiores, camadas_inferiores)
