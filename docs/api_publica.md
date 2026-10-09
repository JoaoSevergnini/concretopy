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

## Ancoragem

- `CondicoesAncoragem(boa_aderencia=...)`
- `ResultadoAncoragem`
- `calcular_ancoragem(concreto, aco, bitola_mm, as_calculada_cm2,
  as_efetiva_cm2, *, condicoes, comprimento_disponivel_cm=None,
  gamma_c=1.4, gamma_s=1.15)`

Disponiveis em `concretopy` e `concretopy.api`. Barras nervuradas tracionadas,
retas e sem gancho; aderencia informada obrigatoriamente pelo usuario.
Resistencias em MPa, bitola em mm, areas em cm2 e comprimentos em cm.
Veja [regras, hipoteses, validacoes e exemplo](ancoragem.md).

## Decalagem longitudinal

- `calcular_al(*, concreto, b_cm, d_cm, vk_abs_kn, gamma_f=1.4, gamma_c=1.4)`
- `ResultadoDecalagemAl`

Disponiveis em `concretopy` e `concretopy.api`. Magnitude caracteristica de
cortante em kN e d explicito em cm. Retorna al_base e al limitado em cm;
nao seleciona esforcos nem compoe comprimentos de ancoragem.
Hipoteses e unidades em [ancoragem e decalagem](ancoragem.md).

Tambem disponivel como `VigaRetangular.calcular_decalagem(*, vk_abs_kn,
d_cm, gamma_f=1.4, gamma_c=1.4)`, usando o concreto e bw da viga, com d
obrigatorio e o mesmo ResultadoDecalagemAl da funcao pura.

## Demanda positiva no apoio

- `calcular_armadura_positiva_apoio(...)`
- `ResultadoArmaduraApoio`

Disponiveis em `concretopy`, `concretopy.api` e, para a funcao, em
`concretopy.verificacoes`. Condicoes A/B/C com camadas reais do apoio,
d do vao explicito e secao do vao opcional. Retorna demanda em cm2, sem
aprovar armadura detalhada ou ancoragem. Veja [contrato, hipoteses e exemplo](armadura_apoio.md).


## Apoio: um par de esforcos e ancoragem independente

`calcular_armadura_positiva_apoio` recebe `mk_apoio_kncm` e `vk_apoio_kn`
caracteristicos, nao negativos, para uma unica chamada. Os antigos argumentos
maximo/minimo e resultados de estados internos foram removidos deliberadamente.
Veja [armadura no apoio](armadura_apoio.md).

A raiz e `concretopy.api` exportam `verificar_ancoragem_positiva_apoio` e
`ResultadoVerificacaoAncoragemApoio`. Essa verificacao recebe diretamente o
comprimento disponivel, a demanda e area efetiva (cm2), bitola (mm), aderencia
e gancho previamente validado pelo chamador. Veja [ancoragem](ancoragem.md).
`calcular_ancoragem` e `calcular_al` permanecem independentes e inalterados.

## Componentes aditivos do resultado de cortante

`dimensionar_cortante_viga` conserva assinatura e `ResultadoCortante(asw_por_s, vc, vrd2)`. Retorna adicionalmente `asw_por_s_calculado` (cm²/m): parcela de cortante antes da governância do mínimo, limitada inferiormente a zero, e `asw_por_s_minimo` (cm²/m). `asw_por_s` permanece governante com o comportamento anterior. Os novos campos são opcionais na construção direta e não participam da comparação dos três valores legados. `dataclasses.asdict` os inclui como campos adicionais. Não substituem controles de biela/espaçamento ou verificações geométricas. A exposição não altera critérios resistentes/normativos.
