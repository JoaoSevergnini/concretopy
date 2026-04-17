from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable

from ..detalhamento.arranjos import (
    area_barra_cm2,
    calcular_espacamento_equivalente,
    calcular_num_barras,
)
from ..detalhamento.layouts import coordenadas_barras_retangulares
from ..exceptions import (
    ArmaduraExistenteInterceptada,
    ConvergenciaNaoAtingida,
    FuroEmZonaComprimida,
    GeometriaInvalidaFuro,
    RompimentoBielaCompressao,
)
from ..elementos.viga import VigaRetangular
from ..materiais import Aco, Concreto
from ..resultados import ResultadoReforcoFuro
from ..secoes import SecaoPoligonalArmada, SecaoRetangular
from ..unidades import converter_forca, converter_momento, kn_para_tf, kncm_para_tfm
from ..verificacoes.flexo_compressao import CalculadoraFlexoCompressao


GAMMA_F = 1.4
GAMMA_S = 1.15
GAMMA_C = 1.4
GAMMA_N = 1.2

# Convenção legada preservada para facilitar a migração.
REFORCOS_PADRAO = [
    [(2, 10.0)],
    [(3, 10.0)],
    [(2, 12.5)],
    [(3, 12.5)],
    [(2, 16.0)],
    [(3, 16.0)],
    [(2, 20.0)],
    [(3, 20.0)],
    [(4, 20.0)],
    [(2, 25.0)],
    [(3, 25.0)],
    [(4, 25.0)],
    [(5, 25.0)],
    [(6, 25.0)],
    [(7, 25.0)],
    [(8, 25.0)],
    [(9, 25.0)],
    [(10, 25.0)],
    [(11, 25.0)],
    [(12, 25.0)],
    [(15, 25.0)],
]


@dataclass(frozen=True)
class FuroRetangular:
    """Geometria do furo em cm."""

    b: float
    h: float



def pontos_retangulo(b: float, h: float, po: list[float] | None = None) -> list[list[float]]:
    if po is None:
        po = [0.0, 0.0]
    return [po, [po[0] + b, po[1]], [po[0] + b, po[1] + h], [po[0], po[1] + h]]



def calcular_as(n_barras: int, bitola_mm: float) -> float:
    return n_barras * area_barra_cm2(bitola_mm)



def calcular_as_arranjo(arranjo: Iterable[tuple[int, float]]) -> float:
    return sum(calcular_as(n, bitola) for n, bitola in arranjo)


class CalculadoraReforcoFuros:
    """
    Calculadora de reforço de furos em vigas de concreto armado.

    Convenções oficiais do pacote:
    - dimensões em cm
    - fck em MPa
    - Mk em kN.cm
    - Vk em kN

    Para facilitar a migração de rotinas antigas, a classe também aceita
    entrada em tf e tf.m por meio dos parâmetros ``unidade_forca`` e
    ``unidade_momento`` ou pelo construtor alternativo ``from_tf_tfm``.
    """

    def __init__(
        self,
        h: float,
        b: float,
        h_furo: float,
        b_furo: float,
        fck: float,
        C: float,
        Mk: float,
        Vk: float,
        cobrimento: float,
        armadura_superior: list[tuple[int, float]],
        armadura_inferior: list[tuple[int, float]],
        *,
        fyk: float = 500.0,
        diametro_estribo_mm: float = 5.0,
        unidade_forca: str = "kN",
        unidade_momento: str = "kN.cm",
        conversao_tf_aproximada: bool = True,
    ) -> None:
        self.concreto = Concreto(fck)
        self.aco = Aco(fyk)
        self.viga = VigaRetangular(
            bw=b,
            h=h,
            cobrimento=cobrimento,
            concreto=self.concreto,
            aco=self.aco,
            diametro_estribo_mm=diametro_estribo_mm,
        )
        self.furo = FuroRetangular(b_furo, h_furo)

        self.Mk = converter_momento(Mk, unidade_momento, "kN.cm", aproximado=conversao_tf_aproximada)
        self.Vk = converter_forca(Vk, unidade_forca, "kN", aproximado=conversao_tf_aproximada)
        self.As_sup = [(int(n), float(bitola)) for n, bitola in armadura_superior]
        self.As_inf = [(int(n), float(bitola)) for n, bitola in armadura_inferior]
        self.C = C

        self.parametros_calculo()
        self._geo_banzos()

        self.verificado = False
        self.pos_LN = self.viga.dimensionar_flexao(abs(self.Mk)).linha_neutra
        self.avisos: list[str] = []

        self.Asw_sec_comp: float | None = None
        self.Asw_sec_trac: float | None = None
        self.As_susp: float = 0.0
        self.As_long: list[tuple[int, float]] | None = None
        self.memorial = ""
        self.resultado: ResultadoReforcoFuro | None = None
        self.cfg_est_sc: dict[float, int] | None = None
        self.cfg_est_st: dict[float, int] | None = None
        self.cfg_arm_susp: dict[float, int] = {}
        self._verificacao_dimensoes_norma = True
        self._frd_biela_equivalente_kn: float | None = None



    @classmethod
    def from_tf_tfm(
        cls,
        h: float,
        b: float,
        h_furo: float,
        b_furo: float,
        fck: float,
        C: float,
        Mk_tfm: float,
        Vk_tf: float,
        cobrimento: float,
        armadura_superior: list[tuple[int, float]],
        armadura_inferior: list[tuple[int, float]],
        **kwargs,
    ) -> "CalculadoraReforcoFuros":
        return cls(
            h=h,
            b=b,
            h_furo=h_furo,
            b_furo=b_furo,
            fck=fck,
            C=C,
            Mk=Mk_tfm,
            Vk=Vk_tf,
            cobrimento=cobrimento,
            armadura_superior=armadura_superior,
            armadura_inferior=armadura_inferior,
            unidade_forca="tf",
            unidade_momento="tf.m",
            **kwargs,
        )

    def parametros_calculo(
        self,
        per_comp: float | None = None,
        per_trac: float | None = None,
        per_susp: float | None = None,
    ) -> None:
        self.per_comp = 0.8 if per_comp is None else per_comp
        self.per_trac = 0.2 if per_trac is None else per_trac
        self.per_susp = 1.0 if per_susp is None else per_susp

    def _geo_banzos(self) -> None:
        if self.Mk >= 0:
            h_comp = self.C
            h_trac = self.viga.h - self.furo.h - self.C
        else:
            h_trac = self.C
            h_comp = self.viga.h - self.furo.h - self.C

        if h_comp <= 0 or h_trac <= 0:
            raise GeometriaInvalidaFuro("O furo elimina um dos banzos resistentes da viga.")

        self.secao_comp = SecaoRetangular(self.viga.bw, h_comp, self.viga.cobrimento, self.viga.diametro_estribo_mm)
        self.secao_trac = SecaoRetangular(self.viga.bw, h_trac, self.viga.cobrimento, self.viga.diametro_estribo_mm)

        self.viga_comp = VigaRetangular(
            bw=self.viga.bw,
            h=h_comp,
            cobrimento=self.viga.cobrimento,
            concreto=self.concreto,
            aco=self.aco,
            diametro_estribo_mm=self.viga.diametro_estribo_mm,
        )
        self.viga_trac = VigaRetangular(
            bw=self.viga.bw,
            h=h_trac,
            cobrimento=self.viga.cobrimento,
            concreto=self.concreto,
            aco=self.aco,
            diametro_estribo_mm=self.viga.diametro_estribo_mm,
        )

    def _calcular_solicitacoes_metodo1(self) -> None:
        self.Vk_comp = self.Vk * self.per_comp
        self.Vk_trac = self.Vk * self.per_trac
        self.Z = self.secao_comp.h / 2 + self.secao_trac.h / 2 + self.furo.h
        self.Nk = abs(self.Mk / self.Z)
        self.Mk_comp1 = self.Vk_comp * self.furo.b / 2
        self.Mk_comp2 = -self.Vk_comp * self.furo.b / 2
        self.Mk_trac1 = -self.Vk_trac * self.furo.b / 2
        self.Mk_trac2 = self.Vk_trac * self.furo.b / 2

    def _calcular_solicitacoes_metodo2(self) -> None:
        self.Vk_comp = self.Vk * self.per_comp
        self.Vk_trac = self.Vk * self.per_trac
        self.Z = self.viga.secao.d() - self.pos_LN / 2
        self.Nk = abs(self.Mk / self.Z)

        l_comp = self.secao_comp.h / 2 - self.pos_LN / 2
        l_trac = self.secao_trac.h / 2 - (self.viga.h - self.viga.secao.d())

        if self.Mk >= 0:
            self.Mk_comp1 = self.Vk_comp * self.furo.b / 2 + self.Nk * l_comp
            self.Mk_comp2 = -self.Vk_comp * self.furo.b / 2 + self.Nk * l_comp
            self.Mk_trac1 = -self.Vk_trac * self.furo.b / 2 + self.Nk * l_trac
            self.Mk_trac2 = self.Vk_trac * self.furo.b / 2 + self.Nk * l_trac
        else:
            self.Mk_comp1 = -self.Vk_comp * self.furo.b / 2 - self.Nk * l_comp
            self.Mk_comp2 = self.Vk_comp * self.furo.b / 2 - self.Nk * l_comp
            self.Mk_trac1 = self.Vk_trac * self.furo.b / 2 + self.Nk * l_trac
            self.Mk_trac2 = -self.Vk_trac * self.furo.b / 2 + self.Nk * l_trac

    def _vrd2_secao(self, secao: SecaoRetangular) -> float:
        d = secao.d()
        fcd = self.concreto.fcd(GAMMA_C) * 1e-1
        return 0.27 * self.concreto.alfa_v2 * fcd * secao.bw * d

    def _dimensionar_cortante(self, metodo_verif_corte: str = "NBR6118") -> None:
        per_comp_max = min(self._vrd2_secao(self.secao_comp) / (self.Vk * GAMMA_F * GAMMA_N), 1)
        per_trac_max = min(self._vrd2_secao(self.secao_trac) / (self.Vk * GAMMA_F * GAMMA_N), 1)

        if (per_comp_max + per_trac_max) < 1:
            raise RompimentoBielaCompressao("Região do furo não tem capacidade de absorver o esforço cortante.")

        if (per_comp_max + per_trac_max) == 2:
            self.per_comp = 0.5
            self.per_trac = 0.5

            limite_sup = 1
            limite_inf = 0

        else:
            if per_comp_max > per_trac_max:

                limite_sup = per_comp_max - 0.001
                limite_inf =  1 - per_trac_max - 0.001

                self.per_comp = (limite_sup + limite_inf) / 2
                self.per_trac = 1 - self.per_comp

            else:
                limite_sup = per_comp_max - 0.001
                limite_inf = max(1 - per_trac_max - 0.001, 0)

                self.per_comp = (limite_sup + limite_inf) / 2
                self.per_trac = 1 - self.per_comp

        self._calcular_solicitacoes()

        if metodo_verif_corte.upper() == "NBR6118":
            self._calcular_asw_nbr6118()
        elif metodo_verif_corte.lower() == "tensoes":
            self.Asw_sec_comp, self.Asw_sec_trac = self._metodo_tensoes()
        else:
            raise ValueError(f"Método de verificação ao cortante inválido: {metodo_verif_corte}")

        if self.Asw_sec_comp is None or self.Asw_sec_trac is None:
            return

        diferenca_asw = self.Asw_sec_comp - self.Asw_sec_trac
        max_iter = 0

        while abs(diferenca_asw) > 0.01 and max_iter < 100:

            if diferenca_asw < 0:
                novo_per_comp = self.per_comp + (limite_sup - self.per_comp)/2
                limite_inf = float(self.per_comp)
                self.per_comp = novo_per_comp

            elif diferenca_asw > 0:
                novo_per_comp = self.per_comp - (self.per_comp - limite_inf)/2
                limite_sup = float(self.per_comp)
                self.per_comp = novo_per_comp

            self.per_trac = 1 - self.per_comp

            self._calcular_solicitacoes()

            if metodo_verif_corte.upper() == "NBR6118":
                self._calcular_asw_nbr6118()
            elif metodo_verif_corte.lower() == "tensoes":
                self.Asw_sec_comp, self.Asw_sec_trac = self._metodo_tensoes()

            if self.Asw_sec_comp is None or self.Asw_sec_trac is None:
                return

            diferenca_asw = self.Asw_sec_comp - self.Asw_sec_trac

            max_iter += 1

    def _calcular_asw_nbr6118(self) -> None:
        try:
            mk_comp = max( abs(self.Mk_comp1), abs(self.Mk_comp2))
            self.Asw_sec_comp = self.viga_comp.dimensionar_cortante(self.Vk_comp * GAMMA_N, nk=-self.Nk * GAMMA_N,
                                                                    mk = mk_comp * GAMMA_N).asw_por_s
        except RompimentoBielaCompressao:
            self.Asw_sec_comp = None
            self.avisos.append("Rompimento da biela de compressão no banzo comprimido pelo método da NBR6118.")

        try:
            self.Asw_sec_trac = self.viga_trac.dimensionar_cortante(self.Vk_trac * GAMMA_N, nk= self.Nk * GAMMA_N).asw_por_s
        except RompimentoBielaCompressao:
            self.Asw_sec_trac = None
            self.avisos.append("Rompimento da biela de compressão no banzo tracionado pelo método da NBR6118.")

    def _dimensionar_suspensao(self) -> None:
        fyd_kN_cm2 = self.aco.fyd(GAMMA_S) * 1e-1
        self.As_susp = self.per_susp * self.Vk * GAMMA_F * GAMMA_N / fyd_kN_cm2

    def _dimensionar_arm_long(self, flex_composta: bool) -> None:
        if flex_composta:
            self.As_long = self._flexao_composta()
            if self.As_long is None:
                self.avisos.append("Reforço longitudinal não encontrado.")
            return

        a_nec = (self.Nk * GAMMA_F) / (self.aco.fyd(GAMMA_S) * 1e-1)
        as_exis = self.As_inf if self.Mk >= 0 else self.As_sup
        a_existente = calcular_as_arranjo(as_exis)
        a_reforco = max(a_nec - a_existente, 0.0)

        for reforco in REFORCOS_PADRAO:
            if calcular_as_arranjo(reforco) > a_reforco:
                self.As_long = list(reforco)
                return

        self.As_long = None
        self.avisos.append("Reforço longitudinal não encontrado no catálogo padrão.")

    def _flexao_composta(self) -> list[tuple[int, float]] | None:
        pts_sc = pontos_retangulo(self.secao_comp.bw, self.secao_comp.h)
        pts_st = pontos_retangulo(self.secao_trac.bw, self.secao_trac.h)

        mxsd_sc1 = self.Mk_comp1 * GAMMA_N * GAMMA_F
        mxsd_sc2 = self.Mk_comp2 * GAMMA_N * GAMMA_F
        mxsd_st1 = self.Mk_trac1 * GAMMA_N * GAMMA_F
        mxsd_st2 = self.Mk_trac2 * GAMMA_N * GAMMA_F

        calc = CalculadoraFlexoCompressao()

        for reforco in REFORCOS_PADRAO:
            if self.Mk >= 0:
                layout_sc = coordenadas_barras_retangulares(self.secao_comp, self.As_sup, list(reforco))
                layout_st = coordenadas_barras_retangulares(self.secao_trac, list(reforco), self.As_inf)
            else:
                layout_sc = coordenadas_barras_retangulares(self.secao_comp, list(reforco), self.As_inf)
                layout_st = coordenadas_barras_retangulares(self.secao_trac, self.As_sup, list(reforco))

            try:
                m_sc_0 = calc.momentos_resistentes(
                    SecaoPoligonalArmada(pts_sc, layout_sc.barras),
                    self.concreto,
                    self.aco,
                    GAMMA_F * self.Nk,
                    0.0,
                ).myd_resistente
                m_sc_180 = calc.momentos_resistentes(
                    SecaoPoligonalArmada(pts_sc, layout_sc.barras),
                    self.concreto,
                    self.aco,
                    GAMMA_F * self.Nk,
                    180.0,
                ).myd_resistente

                m_st_0 = calc.momentos_resistentes(
                    SecaoPoligonalArmada(pts_st, layout_st.barras),
                    self.concreto,
                    self.aco,
                    -GAMMA_F * self.Nk,
                    0.0,
                ).myd_resistente
                m_st_180 = calc.momentos_resistentes(
                    SecaoPoligonalArmada(pts_st, layout_st.barras),
                    self.concreto,
                    self.aco,
                    -GAMMA_F * self.Nk,
                    180.0,
                ).myd_resistente
            except (OverflowError, ZeroDivisionError, ConvergenciaNaoAtingida):
                continue

            verif = (
                min(m_sc_0, m_sc_180) < mxsd_sc1 < max(m_sc_0, m_sc_180)
                and min(m_sc_0, m_sc_180) < mxsd_sc2 < max(m_sc_0, m_sc_180)
                and min(m_st_0, m_st_180) < mxsd_st1 < max(m_st_0, m_st_180)
                and min(m_st_0, m_st_180) < mxsd_st2 < max(m_st_0, m_st_180)
            )
            if verif:
                self.layout_sc = layout_sc
                self.layout_st = layout_st
                return list(reforco)

        return None

    def _metodo_tensoes(self) -> tuple[float | None, float | None]:
        twd_comp = self.Vk_comp * GAMMA_F / self.secao_comp.area * 10
        twd_trac = self.Vk_trac * GAMMA_F / self.secao_trac.area * 10
        twu = min(0.25 * self.concreto.fck * 10 / GAMMA_C, 45)
        tconc = 0.15 * (self.concreto.fck ** 0.5)

        if twd_comp > twu:
            self.avisos.append("Rompimento da biela de compressão no banzo comprimido pelo método das tensões.")
            asw_comp = None
        else:
            td_comp = GAMMA_N * twd_comp - tconc
            ro_comp = td_comp * 10 / self.aco.fyd(GAMMA_S)
            asw_comp = ro_comp * self.secao_comp.bw

        if twd_trac > twu:
            self.avisos.append("Rompimento da biela de compressão no banzo tracionado pelo método das tensões.")
            asw_trac = None
        else:
            td_trac = GAMMA_N * twd_trac - tconc
            ro_trac = td_trac * 10 / self.aco.fyd(GAMMA_S)
            asw_trac = ro_trac * self.secao_trac.bw

        return asw_comp, asw_trac

    def _construir_resultado(self) -> ResultadoReforcoFuro:
        memorial = self._gerar_memorial_texto()
        self.memorial = memorial
        self.resultado = ResultadoReforcoFuro(
            asw_banzo_comprimido=self.Asw_sec_comp,
            asw_banzo_tracionado=self.Asw_sec_trac,
            as_suspensao=self.As_susp,
            armadura_longitudinal=self.As_long,
            configuracao_estribos_banzo_comprimido=self.cfg_est_sc,
            configuracao_estribos_banzo_tracionado=self.cfg_est_st,
            configuracao_armadura_suspensao=self.cfg_arm_susp,
            avisos=list(self.avisos),
            memorial=memorial,
            verificacao_dimensoes_norma=self._verif_dim_norma(),
            resistencia_biela_equivalente_kn=self._verif_romp_bielas(),
        )
        return self.resultado

    def calcular_reforco(
        self,
        flex_composta: bool = True,
        metodo_solicitacoes: str = "SUSSEKIND",
        ramos_estribo: int = 2,
        metodo_verif_corte: str = "NBR6118",
    ) -> ResultadoReforcoFuro:
        if metodo_solicitacoes.upper() == "FUSCO":
            self._calcular_solicitacoes = self._calcular_solicitacoes_metodo1
        elif metodo_solicitacoes.upper() == "SUSSEKIND":
            self._calcular_solicitacoes = self._calcular_solicitacoes_metodo2
        else:
            raise ValueError("metodo_solicitacoes deve ser 'FUSCO' ou 'SUSSEKIND'.")

        self._dimensionar_cortante(metodo_verif_corte)
        self._dimensionar_suspensao()
        self._dimensionar_arm_long(flex_composta)

        self.cfg_est_sc = (
            calcular_espacamento_equivalente(self.Asw_sec_comp / ramos_estribo)
            if self.Asw_sec_comp is not None
            else None
        )
        self.cfg_est_st = (
            calcular_espacamento_equivalente(self.Asw_sec_trac / ramos_estribo)
            if self.Asw_sec_trac is not None
            else None
        )
        self.cfg_arm_susp = calcular_num_barras(self.As_susp / ramos_estribo)

        self.verificado = True
        return self._construir_resultado()

    def armaduras(self) -> str:
        if self.resultado is None:
            self._construir_resultado()

        linhas: list[str] = []
        linhas.append("Estribos na parte comprimida")
        linhas.append("----------------------------")
        if self.Asw_sec_comp is not None and self.cfg_est_sc is not None:
            linhas.append(f"As/s = {round(self.Asw_sec_comp, 2)} cm²/m")
            for d, espac in self.cfg_est_sc.items():
                linhas.append(f"Ø{d} c/{espac} cm")
        else:
            linhas.append("Biela de compressão rompida; armadura não calculada.")

        linhas.append("")
        linhas.append("Estribos na parte tracionada")
        linhas.append("----------------------------")
        if self.Asw_sec_trac is not None and self.cfg_est_st is not None:
            linhas.append(f"As/s = {round(self.Asw_sec_trac, 2)} cm²/m")
            for d, espac in self.cfg_est_st.items():
                linhas.append(f"Ø{d} c/{espac} cm")
        else:
            linhas.append("Biela de compressão rompida; armadura não calculada.")

        linhas.append("")
        linhas.append("Armadura de suspensão")
        linhas.append("---------------------")
        linhas.append(f"As = {round(self.As_susp, 2)} cm²")
        for d, n in self.cfg_arm_susp.items():
            linhas.append(f"{n} estribos de Ø{d}")

        linhas.append("")
        linhas.append("Armadura longitudinal")
        linhas.append("---------------------")
        if self.As_long is not None:
            for n, bit in self.As_long:
                linhas.append(f"{n} barras de Ø{bit}")
        else:
            linhas.append("Armadura de reforço longitudinal não encontrada.")

        return "\n".join(linhas)


    def _gerar_memorial_texto(self) -> str:
        if not self.verificado:
            return "Furo não calculado."

        avisos = "\n".join(f"- {aviso}" for aviso in self.avisos) if self.avisos else "- Sem avisos."
        return (
            "--------------------------------\n"
            "Informações gerais\n"
            "--------------------------------\n\n"
            f"fck (MPa) = {self.concreto.fck}\n"
            f"Altura da viga (cm) = {self.viga.h}\n"
            f"Largura da viga (cm) = {self.viga.bw}\n\n"
            f"Altura do furo (cm) = {self.furo.h}\n"
            f"Largura do furo (cm) = {self.furo.b}\n"
            f"Distância entre topo do furo e topo da viga (cm) = {self.C}\n\n"
            f"Altura do banzo comprimido (cm) = {self.secao_comp.h}\n"
            f"Altura do banzo tracionado (cm) = {self.secao_trac.h}\n\n"
            "--------------------\n"
            "Solicitações\n"
            "--------------------\n"
            f"Mk (kN.cm) = {round(self.Mk, 2)} | {round(kncm_para_tfm(self.Mk), 2)} tf.m\n"
            f"Md (kN.cm) = {round(self.Mk * GAMMA_F * GAMMA_N, 2)} | {round(kncm_para_tfm(self.Mk * GAMMA_F * GAMMA_N), 2)} tf.m\n"
            f"Vk (kN) = {round(self.Vk, 2)} | {round(kn_para_tf(self.Vk), 2)} tf\n"
            f"Vd (kN) = {round(self.Vk * GAMMA_F * GAMMA_N, 2)} | {round(kn_para_tf(self.Vk * GAMMA_F * GAMMA_N), 2)} tf\n\n"
            "------------------------------\n"
            "Solicitação normal nos banzos\n"
            "------------------------------\n"
            f"Z (cm) = {round(self.Z, 2)}\n"
            f"Nk (kN) = {round(self.Nk, 2)} | {round(kn_para_tf(self.Nk), 2)} tf\n\n"
            "--------------------------------\n"
            "Solicitações no banzo comprimido\n"
            "--------------------------------\n"
            f"Nd_bc (kN) = {round(self.Nk * GAMMA_F * GAMMA_N, 2)} | {round(kn_para_tf(self.Nk * GAMMA_F * GAMMA_N), 2)} tf\n"
            f"Vd_bc (kN) = {round(self.Vk_comp * GAMMA_F * GAMMA_N, 2)} | {round(kn_para_tf(self.Vk_comp * GAMMA_F * GAMMA_N), 2)} tf\n"
            f"Md_bc1 (kN.cm) = {round(self.Mk_comp1 * GAMMA_F * GAMMA_N, 2)} | {round(kncm_para_tfm(self.Mk_comp1 * GAMMA_F * GAMMA_N), 2)} tf.m\n"
            f"Md_bc2 (kN.cm) = {round(self.Mk_comp2 * GAMMA_F * GAMMA_N, 2)} | {round(kncm_para_tfm(self.Mk_comp2 * GAMMA_F * GAMMA_N), 2)} tf.m\n\n"
            "--------------------------------\n"
            "Solicitações no banzo tracionado\n"
            "--------------------------------\n"
            f"Nd_bt (kN) = {-round(self.Nk * GAMMA_F * GAMMA_N, 2)} | {-round(kn_para_tf(self.Nk * GAMMA_F * GAMMA_N), 2)} tf\n"
            f"Vd_bt (kN) = {round(self.Vk_trac * GAMMA_F * GAMMA_N, 2)} | {round(kn_para_tf(self.Vk_trac * GAMMA_F * GAMMA_N), 2)} tf\n"
            f"Md_bt1 (kN.cm) = {round(self.Mk_trac1 * GAMMA_F * GAMMA_N, 2)} | {round(kncm_para_tfm(self.Mk_trac1 * GAMMA_F * GAMMA_N), 2)} tf.m\n"
            f"Md_bt2 (kN.cm) = {round(self.Mk_trac2 * GAMMA_F * GAMMA_N, 2)} | {round(kncm_para_tfm(self.Mk_trac2 * GAMMA_F * GAMMA_N), 2)} tf.m\n\n"
            "--------------------\n"
            "Armaduras\n"
            "--------------------\n"
            f"As/s banzo comprimido (cm²/m) = {None if self.Asw_sec_comp is None else round(self.Asw_sec_comp, 2)}\n"
            f"As/s banzo tracionado (cm²/m) = {None if self.Asw_sec_trac is None else round(self.Asw_sec_trac, 2)}\n"
            f"As suspensão (cm²) = {round(self.As_susp, 2)}\n"
            f"Armadura longitudinal = {self.As_long}\n\n"
            "--------------------\n"
            "Avisos\n"
            "--------------------\n"
            f"{avisos}"
        )

    def memorial_de_calculo(self) -> None:
        self.memorial = self._gerar_memorial_texto()

    def _verificar_espaco_arm_existentes(self) -> bool:
        camadas_arm_sup = len(self.As_sup)
        camadas_arm_inf = len(self.As_inf)

        e_sup = 2 * self.viga.cobrimento
        e_inf = 2 * self.viga.cobrimento

        if camadas_arm_sup == 1:
            e_sup += self.As_sup[0][1] / 10
        else:
            for idx, (_, bitola) in enumerate(self.As_sup):
                e_sup += bitola / 10
                if idx < camadas_arm_sup - 1:
                    e_sup += 2 if bitola < 25 else bitola / 10

        if camadas_arm_inf == 1:
            e_inf += self.As_inf[0][1] / 10
        else:
            for idx, (_, bitola) in enumerate(self.As_inf):
                e_inf += bitola / 10
                if idx < camadas_arm_inf - 1:
                    e_inf += 2 if bitola < 25 else bitola / 10

        if e_sup > self.C and e_inf > self.viga.h - self.furo.h - self.C:
            raise ArmaduraExistenteInterceptada(
                "Furo interrompe a passagem da armadura existente na parte superior e inferior da viga."
            )
        if e_sup > self.C:
            raise ArmaduraExistenteInterceptada(
                "Furo interrompe a passagem da armadura existente na parte superior da viga."
            )
        if e_inf > self.viga.h - self.furo.h - self.C:
            raise ArmaduraExistenteInterceptada(
                "Furo interrompe a passagem da armadura existente na parte inferior da viga."
            )
        return True

    def _verificar_zona_posicionada(self) -> bool:
        if self.pos_LN > self.secao_comp.h:
            raise FuroEmZonaComprimida(
                f"Furo se encontra em zona de compressão da viga. Linha neutra em {round(self.pos_LN, 2)} cm."
            )
        return True

    def _verif_dim_norma(self) -> bool:
        return max(self.furo.b, self.furo.h) <= min(12, self.viga.h / 3)

    def _verif_romp_bielas(self) -> float:
        dl_sup = self.viga.cobrimento + 2
        dl_inf = self.viga.cobrimento + 2

        h_sup = self.C
        h_inf = self.viga.h - self.C - self.furo.h

        lh_biela_sup = h_sup - dl_sup - (self.furo.b + self.viga.cobrimento + 0.5)
        l_biela_sup = lh_biela_sup / sqrt(2)

        lh_biela_inf = h_inf - dl_inf - (self.furo.b + self.viga.cobrimento + 0.5)
        l_biela_inf = lh_biela_inf / sqrt(2)

        if lh_biela_sup <= 0 and lh_biela_inf <= 0:
            frd_biela = 0.0
        elif lh_biela_inf <= 0 < lh_biela_sup:
            frd_biela = 0.42 * self.concreto.alfa_v2 * self.concreto.fck / GAMMA_C * 1e-1 * self.viga.bw * l_biela_sup
        elif lh_biela_sup <= 0 < lh_biela_inf:
            frd_biela = 0.42 * self.concreto.alfa_v2 * self.concreto.fck / GAMMA_C * 1e-1 * self.viga.bw * l_biela_inf
        else:
            frd_biela = 0.42 * self.concreto.alfa_v2 * self.concreto.fck / GAMMA_C * 1e-1 * self.viga.bw * (l_biela_sup + l_biela_inf)

        if frd_biela != 0 and frd_biela < self.Vk * GAMMA_N * GAMMA_F:
            self.avisos.append("Biela equivalente não resiste aos esforços; calcular reforço.")

        return frd_biela

    def verificar_furo(self) -> bool:
        self._verificar_espaco_arm_existentes()
        self._verificar_zona_posicionada()
        self._verificacao_dimensoes_norma = self._verif_dim_norma()
        if not self._verificacao_dimensoes_norma:
            self._frd_biela_equivalente_kn = self._verif_romp_bielas()
        return True
