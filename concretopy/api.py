"""API pública estável do concretopy.

Importe daqui os nomes congelados para uso pelo cliente do pacote.
Itens fora desta lista continuam disponíveis pelos submódulos, mas são
considerados internos ou sujeitos a revisão.
"""

from .aplicacoes.calculadora_furos import CalculadoraReforcoFuros, FuroRetangular
from .armaduras import Barra, BarraPosicionada, CamadaArmaduraLongitudinal
from .elementos.pilar import PilarPoligonal
from .elementos.viga import VigaRetangular
from .materiais import Aco, Concreto
from .resultados import (
    ResultadoArmaduraApoio,
    ResultadoDecalagemAl,
    ResultadoVerificacaoAncoragemApoio,
    ResultadoAncoragem,
    ResultadoCortante,
    ResultadoFlexao,
    ResultadoVerificacaoFlexao,
    ResultadoFlexoCompressao,
    ResultadoReforcoFuro,
)
from .secoes import SecaoPoligonalArmada, SecaoRetangular
from .detalhamento.arranjos import definir_arranjo_arm_long_vigas
from .verificacoes.flexao import calcular_alturas_uteis_camadas, verificar_flexao_viga_retangular

from .verificacoes.ancoragem import CondicoesAncoragem, calcular_ancoragem, verificar_ancoragem_positiva_apoio

from .verificacoes.decalagem import calcular_al

from .verificacoes.armadura_apoio import calcular_armadura_positiva_apoio

__all__ = [
    'verificar_ancoragem_positiva_apoio',
    'ResultadoVerificacaoAncoragemApoio',
    'calcular_armadura_positiva_apoio',
    'ResultadoArmaduraApoio',
    'calcular_al',
    'ResultadoDecalagemAl',
    'CondicoesAncoragem',
    'ResultadoAncoragem',
    'calcular_ancoragem',
    'Aco',
    'Barra',
    'BarraPosicionada',
    'CamadaArmaduraLongitudinal',
    'CalculadoraReforcoFuros',
    'Concreto',
    'FuroRetangular',
    'PilarPoligonal',
    'ResultadoCortante',
    'ResultadoFlexao',
    'ResultadoVerificacaoFlexao',
    'ResultadoFlexoCompressao',
    'ResultadoReforcoFuro',
    'SecaoPoligonalArmada',
    'SecaoRetangular',
    'VigaRetangular',
    'definir_arranjo_arm_long_vigas',
    'verificar_flexao_viga_retangular',
    'calcular_alturas_uteis_camadas',
]
