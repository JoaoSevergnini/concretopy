from __future__ import annotations

from dataclasses import dataclass

from ..materiais import Aco, Concreto
from ..resultados import ResultadoCortante, ResultadoDecalagemAl, ResultadoFlexao
from ..secoes import SecaoRetangular
from ..unidades import tf_para_kn, tfm_para_kncm
from ..verificacoes.cortante import dimensionar_cortante_viga
from ..verificacoes.decalagem import calcular_al
from ..verificacoes.flexao import dimensionar_flexao_viga_retangular


@dataclass(frozen=True)
class VigaRetangular:
    """Viga retangular de concreto armado.

    Convenções oficiais do pacote:
    - bw, h, cobrimento: cm
    - diametro_estribo_mm: mm
    - esforço cortante: kN
    - momento fletor: kN.cm

    Para entradas em tf/tf.m, use os métodos auxiliares ``dimensionar_cortante_tf``
    e ``dimensionar_flexao_tfm``.
    """

    bw: float
    h: float
    cobrimento: float
    concreto: Concreto
    aco: Aco
    diametro_estribo_mm: float = 5.0

    @property
    def secao(self) -> SecaoRetangular:
        return SecaoRetangular(self.bw, self.h, self.cobrimento, self.diametro_estribo_mm)
    
    @property
    def vrd2_kn(self) -> float:
        return 0.27 * self.concreto.alfa_v2 * (self.concreto.fcd() * 1e-1) *  self.bw * self.secao.d()
    
    @property
    def vrd2_tf(self) -> float:
        return self.vrd2_kn / 10

    def dimensionar_flexao(self, mk: float, diametro_barra_mm: float = 12.5) -> ResultadoFlexao:
        return dimensionar_flexao_viga_retangular(self.secao, self.concreto, self.aco, mk, diametro_barra_mm=diametro_barra_mm)

    def dimensionar_cortante(self, vk: float, alfa_graus: float = 90.0, diametro_barra_mm: float = 12.5, nk: float = 0, mk: float = 0) -> ResultadoCortante:
        return dimensionar_cortante_viga(self.secao, self.concreto, self.aco, vk, alfa_graus=alfa_graus, nk=nk, mk=mk, diametro_barra_mm=diametro_barra_mm)

    def calcular_decalagem(
        self,
        *,
        vk_abs_kn: float,
        d_cm: float,
        gamma_f: float = 1.4,
        gamma_c: float = 1.4,
    ) -> ResultadoDecalagemAl:
        """Calcula a decalagem usando o concreto e a largura bw desta viga.

        vk_abs_kn : float
            Magnitude caracteristica do cortante em kN, finita e >= 0.
            Selecionada pelo chamador; negativos nao sao convertidos em modulo.
        d_cm : float
            Altura util em cm, finita e positiva, obrigatoriamente informada.
            Nao infere camada, centroide ou bitola padrao.
        gamma_f, gamma_c : float
            Coeficientes adimensionais, finitos e positivos, de majoracao do
            cortante e minoracao da resistencia do concreto, respectivamente.

        Returns
        -------
        ResultadoDecalagemAl
            al_base, limites e al em cm, resistencias em MPa e forcas em kN.
            Delega integralmente a calcular_al, inclusive suas validacoes.
            Hipoteses: estribos verticais e Vc=Vc0. Nao verifica Vrd2,
            ancoragem ou corte de barras, nem soma al a lb/lb_nec.
        """
        return calcular_al(
            concreto=self.concreto, b_cm=self.bw, d_cm=d_cm,
            vk_abs_kn=vk_abs_kn, gamma_f=gamma_f, gamma_c=gamma_c,
        )

    def dimensionar_flexao_tfm(self, mk_tfm: float, diametro_barra_mm: float = 12.5, aproximado: bool = True) -> ResultadoFlexao:
        return self.dimensionar_flexao(tfm_para_kncm(mk_tfm, aproximado=aproximado), diametro_barra_mm=diametro_barra_mm)

    def dimensionar_cortante_tf(self, vk_tf: float, alfa_graus: float = 90.0, diametro_barra_mm: float = 12.5, aproximado: bool = True) -> ResultadoCortante:
        return self.dimensionar_cortante(tf_para_kn(vk_tf, aproximado=aproximado), alfa_graus=alfa_graus, diametro_barra_mm=diametro_barra_mm)
