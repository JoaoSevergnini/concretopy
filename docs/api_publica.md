# API pública do concretopy

Esta é a lista de nomes tratados como **interface estável** do pacote.

## Materiais e seções
- `Concreto`
- `Aco`
- `SecaoRetangular`
- `SecaoPoligonalArmada`
- `Barra`
- `BarraPosicionada`

## Elementos
- `VigaRetangular`
- `PilarPoligonal`

## Aplicações
- `CalculadoraReforcoFuros`
- `FuroRetangular`

## Resultados
- `ResultadoFlexao`
- `ResultadoCortante`
- `ResultadoFlexoCompressao`
- `ResultadoReforcoFuro`

## Exceptions
- `ErroConcretopy`
- `ErroDimensionamento`
- `TaxaArmaduraExcedida`
- `RompimentoBielaCompressao`
- `GeometriaInvalidaFuro`
- `ArmaduraExistenteInterceptada`
- `FuroEmZonaComprimida`
- `ConvergenciaNaoAtingida`

## Conversões de unidades
- `tf_para_kn`
- `kn_para_tf`
- `tfm_para_kncm`
- `kncm_para_tfm`
- `converter_forca`
- `converter_momento`

## Regra prática
Tudo que estiver fora dessa lista pode continuar sendo utilizado pelos
submódulos, mas não deve ser considerado congelado para a versão `1.x`.
