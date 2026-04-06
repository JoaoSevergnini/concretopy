from __future__ import annotations


class ErroConcretopy(Exception):
    """Exceção base do pacote."""


class ErroDimensionamento(ErroConcretopy):
    """Falha genérica de dimensionamento."""


class TaxaArmaduraExcedida(ErroDimensionamento):
    """Seção com taxa máxima de armadura excedida."""


class RompimentoBielaCompressao(ErroDimensionamento):
    """Esforço cortante acima da capacidade da biela comprimida."""


class GeometriaInvalidaFuro(ErroDimensionamento):
    """Furo com geometria inválida ou fora das hipóteses do método."""


class ArmaduraExistenteInterceptada(GeometriaInvalidaFuro):
    """Furo interfere na passagem da armadura existente."""


class FuroEmZonaComprimida(GeometriaInvalidaFuro):
    """Furo localizado na zona comprimida da seção."""


class ConvergenciaNaoAtingida(ErroDimensionamento):
    """Método iterativo não convergiu."""
