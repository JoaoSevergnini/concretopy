
from __future__ import annotations
from dataclasses import dataclass
from ..materiais import Aco, Concreto
from ..resultados import ResultadoFlexoCompressao
from ..secoes import SecaoPoligonalArmada
from ..verificacoes.flexo_compressao import CalculadoraFlexoCompressao

@dataclass(frozen=True)
class PilarPoligonal:
    contorno: list[list[float]]
    barras: list
    concreto: Concreto
    aco: Aco

    def momentos_resistentes(self, nd: float, inclinacao_linha_neutra_graus: float) -> ResultadoFlexoCompressao:
        calc = CalculadoraFlexoCompressao()
        secao = SecaoPoligonalArmada(self.contorno, self.barras)
        return calc.momentos_resistentes(secao, self.concreto, self.aco, nd, inclinacao_linha_neutra_graus)
