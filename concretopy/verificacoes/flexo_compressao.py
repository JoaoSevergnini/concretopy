from __future__ import annotations

from math import pi

from ..exceptions import ConvergenciaNaoAtingida
from ..geometria.poligonos import area_poligono, momento_primeira_ordem_x, momento_primeira_ordem_y
from ..geometria.transformacoes import rotacionar_ponto, transladar_pontos
from ..materiais import Aco, Concreto
from ..resultados import ResultadoFlexoCompressao
from ..secoes import SecaoPoligonalArmada

TOL_FORCA_ABS_PADRAO = 1e-3
TOL_FORCA_REL_PADRAO = 0.01
MAX_ITER_ROOT = 200


def _clip_polygon_above_horizontal(secao: list[list[float]], yc: float) -> list[list[float]]:
    """Recorta o polígono pela semi-plano y >= yc usando Sutherland-Hodgman.

    A versão anterior montava a seção comprimida por regras geométricas ad hoc e
    podia gerar saltos numéricos bruscos em pontos próximos a vértices.
    """
    if not secao:
        return []

    def inside(p: list[float]) -> bool:
        return p[1] >= yc - 1e-12

    saida: list[list[float]] = []
    n = len(secao)

    for i in range(n):
        s = secao[i]
        e = secao[(i + 1) % n]
        s_in = inside(s)
        e_in = inside(e)

        if s_in and e_in:
            saida.append([e[0], e[1]])
        elif s_in and not e_in:
            dy = e[1] - s[1]
            if abs(dy) > 1e-12:
                t = (yc - s[1]) / dy
                x = s[0] + t * (e[0] - s[0])
                saida.append([x, yc])
        elif (not s_in) and e_in:
            dy = e[1] - s[1]
            if abs(dy) > 1e-12:
                t = (yc - s[1]) / dy
                x = s[0] + t * (e[0] - s[0])
                saida.append([x, yc])
            saida.append([e[0], e[1]])

    # Remove duplicatas consecutivas
    limpeza: list[list[float]] = []
    for p in saida:
        if not limpeza or abs(limpeza[-1][0] - p[0]) > 1e-9 or abs(limpeza[-1][1] - p[1]) > 1e-9:
            limpeza.append(p)

    if len(limpeza) > 1 and abs(limpeza[0][0] - limpeza[-1][0]) < 1e-9 and abs(limpeza[0][1] - limpeza[-1][1]) < 1e-9:
        limpeza.pop()

    return limpeza


def secao_comprimida(secao: list[list[float]], xo: float, ymax: float, h: float) -> list[list[float]]:
    yc = ymax - 0.8 * xo
    if xo <= 0:
        return []
    if 0.8 * xo >= h:
        return secao
    return _clip_polygon_above_horizontal(secao, yc)


def deformacao_aco(xo: float, di: float, d: float, h: float) -> float:
    if 0 <= xo <= (3.5 / 13.5) * d:
        return 10 * ((xo - di) / (d - xo))
    if (3.5 / 13.5) * d < xo <= h:
        return 3.5 * (xo - di) / xo
    if xo > h:
        return 14 * (xo - di) / (7 * xo - 3 * h)
    return 0.0


def _tensao_aco_kN_cm2(deformacao_permille: float, fyd_kN_cm2: float) -> float:
    """Diagrama bilinear idealizado com deformação em ‰ e tensão em kN/cm²."""
    ey_permille = fyd_kN_cm2 / 21.0
    if deformacao_permille <= 0:
        return 21.0 * deformacao_permille if deformacao_permille > -ey_permille else -fyd_kN_cm2
    return 21.0 * deformacao_permille if deformacao_permille < ey_permille else fyd_kN_cm2


def funcao_linha_neutra(xo: float, argumentos: dict) -> float:
    secao_rot = argumentos["secao"]
    ymax = argumentos["ymax"]
    h = argumentos["h"]
    di = argumentos["di"]
    d = argumentos["d"]
    fyd = argumentos["fyd"]
    fcd = argumentos["fcd"]
    nd = argumentos["Nd"]
    areas_barras = argumentos["areas_barras"]

    deform_barras = [deformacao_aco(xo, i, d, h) for i in di]
    tensao_barras = [_tensao_aco_kN_cm2(eps, fyd) for eps in deform_barras]

    secao_com_rot = secao_comprimida(secao_rot, xo, ymax, h)
    area_com = area_poligono(secao_com_rot)
    fs = sum(tensao * area for tensao, area in zip(tensao_barras, areas_barras))
    return nd - area_com * 0.8 * fcd - fs


def _avaliar_grade(funcao, argumentos: dict, x_max: float, n: int = 4000) -> list[tuple[float, float]]:
    pontos: list[tuple[float, float]] = []
    for i in range(n + 1):
        x = x_max * i / n
        try:
            fx = funcao(x, argumentos)
        except ZeroDivisionError:
            continue
        if fx == fx:  # evita NaN
            pontos.append((x, fx))
    return pontos


def _resolver_por_bissecao(funcao, a: float, b: float, argumentos: dict, tol_force_abs: float) -> tuple[float, float, bool]:
    fa = funcao(a, argumentos)
    fb = funcao(b, argumentos)

    if abs(fa) <= tol_force_abs:
        return a, fa, True
    if abs(fb) <= tol_force_abs:
        return b, fb, True
    if fa * fb > 0:
        raise ConvergenciaNaoAtingida("Intervalo sem mudança de sinal para a linha neutra.")

    melhor_x, melhor_f = (a, fa) if abs(fa) <= abs(fb) else (b, fb)

    for _ in range(MAX_ITER_ROOT):
        c = 0.5 * (a + b)
        fc = funcao(c, argumentos)
        if abs(fc) < abs(melhor_f):
            melhor_x, melhor_f = c, fc
        if abs(fc) <= tol_force_abs:
            return c, fc, True
        if fa * fc < 0:
            b, fb = c, fc
        else:
            a, fa = c, fc
    return melhor_x, melhor_f, abs(melhor_f) <= tol_force_abs


def _resolver_linha_neutra(funcao, argumentos: dict, x_max: float, tol_force_abs: float) -> tuple[float, float, bool]:
    grade = _avaliar_grade(funcao, argumentos, x_max=x_max, n=4000)
    if not grade:
        raise ConvergenciaNaoAtingida("Não foi possível avaliar a função de equilíbrio da linha neutra.")

    melhor_x, melhor_f = min(grade, key=lambda item: abs(item[1]))

    # Primeiro tenta em todos os intervalos com mudança de sinal.
    for (xa, fa), (xb, fb) in zip(grade, grade[1:]):
        if abs(fa) <= tol_force_abs:
            return xa, fa, True
        if fa * fb < 0:
            x, f, ok = _resolver_por_bissecao(funcao, xa, xb, argumentos, tol_force_abs)
            if ok:
                return x, f, True
            if abs(f) < abs(melhor_f):
                melhor_x, melhor_f = x, f

    # Se não existir raiz exata por conta de um salto do diagrama idealizado,
    # aceita o melhor ponto desde que o desequilíbrio esteja dentro de uma
    # tolerância de engenharia.
    return melhor_x, melhor_f, abs(melhor_f) <= tol_force_abs


class CalculadoraFlexoCompressao:
    def momentos_resistentes(
        self,
        secao: SecaoPoligonalArmada,
        concreto: Concreto,
        aco: Aco,
        nd: float,
        inclinacao_linha_neutra_graus: float,
        tolerancia_relativa_forca: float = TOL_FORCA_REL_PADRAO,
        tolerancia_absoluta_forca: float = TOL_FORCA_ABS_PADRAO,
    ) -> ResultadoFlexoCompressao:
        area_sec = area_poligono(secao.contorno)
        sx = momento_primeira_ordem_x(secao.contorno)
        sy = momento_primeira_ordem_y(secao.contorno)
        if area_sec == 0:
            raise ValueError("A seção poligonal possui área nula.")

        centroide = [sx / area_sec, sy / area_sec]
        secao_centrada = transladar_pontos(secao.contorno, centroide)
        posicoes_barras = [[b.x, b.y] for b in secao.barras]
        bitolas_mm = [b.diametro_mm for b in secao.barras]
        barras_centradas = transladar_pontos(posicoes_barras, centroide)

        alfa = inclinacao_linha_neutra_graus
        secao_rot = [rotacionar_ponto(p, alfa) for p in secao_centrada]
        barras_rot = [rotacionar_ponto(p, alfa) for p in barras_centradas]

        ymax = ymin = secao_rot[0][1]
        for ponto in secao_rot:
            ymax = max(ymax, ponto[1])
            ymin = min(ymin, ponto[1])

        h = ymax - ymin
        di = [ymax - i[1] for i in barras_rot]
        d = max(di)
        areas_barras = [pi * ((bitola / 10) ** 2) / 4 for bitola in bitolas_mm]

        # Unidades oficiais do pacote: MPa -> kN/cm²
        fyd_kN_cm2 = aco.fyd(1.15) * 0.1
        fcd_kN_cm2 = concreto.fcd(1.4) * 0.1

        capacidade_referencia = area_sec * 0.8 * fcd_kN_cm2 + sum(area * fyd_kN_cm2 for area in areas_barras)
        tol_force_abs = max(tolerancia_absoluta_forca, tolerancia_relativa_forca * capacidade_referencia)

        argumentos = {
            "secao": secao_rot,
            "ymax": ymax,
            "h": h,
            "di": di,
            "d": d,
            "fyd": fyd_kN_cm2,
            "fcd": fcd_kN_cm2,
            "Nd": nd,
            "areas_barras": areas_barras,
        }

        x_max = max(5.0 * h, 5.0 * d, 100.0)
        xo, residual, convergiu = _resolver_linha_neutra(funcao_linha_neutra, argumentos, x_max=x_max, tol_force_abs=tol_force_abs)
        if not convergiu:
            raise ConvergenciaNaoAtingida(
                "Não foi possível equilibrar a linha neutra dentro da tolerância "
                f"adotada. Residual final = {residual:.6f} kN; tolerância = {tol_force_abs:.6f} kN."
            )

        secao_com_rot = secao_comprimida(secao_rot, xo, ymax, h)
        secao_com = [rotacionar_ponto(p, -alfa) for p in secao_com_rot]
        acc = area_poligono(secao_com)
        sxc = momento_primeira_ordem_x(secao_com)
        syc = momento_primeira_ordem_y(secao_com)

        deform_barras = [deformacao_aco(xo, i, d, h) for i in di]
        tensao_barras = [_tensao_aco_kN_cm2(eps, fyd_kN_cm2) for eps in deform_barras]

        fs = sum(area * tensao for area, tensao in zip(areas_barras, tensao_barras))
        somatorio_x = sum(area * tensao * coord[0] for area, tensao, coord in zip(areas_barras, tensao_barras, barras_centradas))
        somatorio_y = sum(area * tensao * coord[1] for area, tensao, coord in zip(areas_barras, tensao_barras, barras_centradas))

        nd_res = acc * 0.8 * fcd_kN_cm2 + fs
        mxd = sxc * 0.8 * fcd_kN_cm2 + somatorio_x
        myd = syc * 0.8 * fcd_kN_cm2 + somatorio_y

        return ResultadoFlexoCompressao(
            nd_resistente=nd_res,
            mxd_resistente=mxd,
            myd_resistente=myd,
            inclinacao_linha_neutra_graus=alfa,
            linha_neutra=xo,
            residual_equilibrio=residual,
            convergiu=convergiu,
        )
