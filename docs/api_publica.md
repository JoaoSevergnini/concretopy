# API pública do concretopy

Esta é a lista de nomes tratados como **interface estável** do pacote.

## Materiais e seções
- `Concreto`
- `Aco`
- `SecaoRetangular`
- `SecaoPoligonalArmada`
- `Barra`
- `BarraPosicionada`
- `CamadaArmaduraLongitudinal(numero_barras, barra, d_cm=None)`

## Elementos
- `VigaRetangular`
- `PilarPoligonal`

## Aplicações
- `CalculadoraReforcoFuros`
- `FuroRetangular`

## Resultados
- `ResultadoFlexao`
- `ResultadoVerificacaoFlexao`
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

## Verificação de resistência à flexão retangular

`verificar_flexao_viga_retangular(secao, concreto, aco, camadas, *,
gamma_c=1.4, gamma_s=1.15, gamma_f=None, verificar_armadura_minima=False)`
está disponível em `concretopy`, `concretopy.api` e `concretopy.verificacoes`.

As camadas contêm barras iguais (`Barra`) e distância `d_cm` da face
comprimida ao centro, em cm. Quando omitida, a posição é calculada por
`calcular_alturas_uteis_camadas(secao, camadas)`, também exportada na API.
A ordem para o posicionamento automático é da face tracionada para a
comprimida. A primeira camada usa `secao.d(bitola)`; as seguintes descontam
o vão livre (2 cm para bitola atual <25 mm, ou bitola atual/10 nos demais
casos) e os raios das barras anterior e atual. Posições explícitas são
preservadas e ancoram a próxima camada. O retorno do auxiliar é uma tupla
de alturas úteis em cm, sem alterar a entrada. A verificação de flexão
continua validando a geometria resultante e registra um aviso quando usa
posições automáticas. Esse critério reproduz VIGAS!K5:K7, sem certificar
espaçamento normativo.

O resultado contém áreas (cm²), alturas úteis e
linha neutra (cm), `x_sobre_d`, limite/estado de ductilidade, `mrd_kncm`
(kN.cm), parâmetros, deformações e diagnósticos. Geometria inválida gera
`ValueError` ou `TypeError`; incompatibilidade com a hipótese de todas as
camadas tracionadas escoadas retorna `hipoteses_validas=False` e momentos
`None`. Nesse caso `linha_neutra_cm` e `x_sobre_d` são candidatos, não solução
validada. O aço não escoado não é resolvido por um motor alternativo.

MRd usa materiais minorados. Quando `gamma_f` é fornecido,
`mk_equivalente_kncm=MRd/gamma_f` é apenas transformação para comparação com
solicitação característica. O mínimo é opcional, independente da capacidade
e não substitui a armadura fornecida. Ductilidade não atendida não trunca x:
MRd continua disponível se o modelo resistente for válido. Não há aprovação
global, ancoragem, cisalhamento ou integração com assistente nessa função.

## Regra prática
Tudo que estiver fora dessa lista pode continuar sendo utilizado pelos
submódulos, mas não deve ser considerado congelado para a versão `1.x`.
