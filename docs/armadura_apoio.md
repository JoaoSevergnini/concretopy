# Armadura positiva necessaria no apoio

`calcular_armadura_positiva_apoio` calcula a demanda para **um unico par
caracteristico Mk/Vk por chamada**, tomando como referencia as condicoes
A/B/C do item 18.3.2.4 da NBR 6118:2023 e as decisoes de engenharia
explicitadas abaixo. Nao aprova a armadura detalhada nem sua ancoragem.

## Entradas, unidades e uso

Geometria e comprimentos em cm; bitolas em mm; areas em cm2; resistencias
em MPa; forcas em kN; momentos em kN.cm; gammas e razoes adimensionais.
Mk e Vk do par sao finitos e nao negativos; Vk representa modulo, sem
abs() silencioso. `nd_tracao_kn` e tracao JA DE CALCULO, nao majorada novamente.

```python
from concretopy import (Aco, Barra, CamadaArmaduraLongitudinal, Concreto,
                        SecaoRetangular, calcular_armadura_positiva_apoio)

resultado = calcular_armadura_positiva_apoio(
    secao=SecaoRetangular(20, 50, 3), concreto=Concreto(30), aco=Aco(500),
    camadas_apoio=(CamadaArmaduraLongitudinal(3, Barra(16), 45),),
    tipo_apoio="extremo", mk_apoio_kncm=4000, vk_apoio_kn=10,
    mk_positivo_max_vao_kncm=8000, mk_negativo_apoio_kncm=0,
    d_vao_cm=45,
)
print(resultado.as_necessaria_cm2, resultado.condicoes_governantes)
print(resultado.condicao_b.fsd_kn, resultado.condicao_b.decalagem.al_cm)
```

`secao_vao` pode diferir da secao do apoio, com os mesmos materiais.
`d_vao_cm` e sempre explicito. `gamma_f=1.4`, `gamma_c=1.4` e
`gamma_s=1.15` sao os padroes existentes. `d_linha_apoio_cm` e
`d_linha_vao_cm` sao necessarios quando o respectivo dimensionamento exige
armadura comprimida; nao certificam sua existencia.

## Configuracao real das barras

A analise existente `verificar_flexao_viga_retangular` fornece:

```text
d = sum(As_i * d_i) / sum(As_i)
x = linha neutra do estado resistente dessa mesma configuracao
z = d - x/2
```

`d_i` e medido da face comprimida. Quando omitido, segue a rotina existente
de posicionamento de camadas, com aviso. A analise deve ter hipoteses validas;
nao se usa x candidato de um estado fisicamente invalido. d e z devem ser positivos.
**z=d-x/2 e uma simplificacao adotada pelo engenheiro neste procedimento**,
nao uma identidade geral do modelo resistente. Nao se duplica o calculo de x.

## Condicoes A, B e C

A aplica quando `mk_apoio_kncm > 0`: reutiliza o dimensionador de flexao
para esse momento, incluindo a armadura minima quando governante.
Mk=0 torna A nao aplicavel, com dimensionamento e As iguais a None.

B aplica somente quando `tipo_apoio="extremo"`, exclusivamente ao par recebido:

```text
Md = gamma_f * mk_apoio_kncm
Vd = gamma_f * vk_apoio_kn
al = calcular_al(concreto, b, d, vk_apoio_kn, gamma_f, gamma_c)
Fsd = Md/z + (al/d)*Vd + nd_tracao_kn
As_b = Fsd / (fyd_mpa * 0.1)
```

A conversao e explicita: 1 MPa = 0.1 kN/cm2. A equacao de Fsd e o criterio
normativo implementado; a selecao dos pares de esforcos pertence ao chamador.
Herda as hipoteses da decalagem: estribos verticais, Vc=Vc0, sem ajuste por Nd.
Apoio intermediario retorna B nao aplicavel, sem al, Fsd ou As_b.

C permanece independente de A e do par Mk/Vk. O momento negativo serve
**somente** para escolher a fracao, nao dimensiona armadura negativa:

```text
As_span = dimensionamento do maximo momento positivo do vao, incluindo minimo
razao = abs(mk_negativo_apoio_kncm) / mk_positivo_max_vao_kncm
C1: razao <= 0.5 -> As_c = As_span / 3
C2: razao >  0.5 -> As_c = As_span / 4
```

Momento negativo nulo e igualdade 0.5 sao C1. O momento negativo recebido
deve ser <=0 e o maximo positivo do vao deve ser >0. C pode coexistir com A.
Os criterios de fracao sao as regras normativas implementadas.

## Resultado e limites de responsabilidade

`ResultadoArmaduraApoio` e imutavel e registra esforcos caracteristicos e de
calculo, d por camada, areas, d, x, z, materiais/gammas, A/B/C, dimensionamentos,
al, Fsd, demanda global e avisos. Objetos aninhados evitam duplicar os
intermediarios: `condicao_b.decalagem`, `condicao_b.fsd_kn`,
`condicao_b.as_cm2`, `condicao_c.as_vao_cm2`, etc.

`As_necessaria = max(As_a, As_b, As_c)` entre condicoes aplicaveis. Todos os
empates numericamente exatos sao preservados em `condicoes_governantes`.
A funcao nao possui campo atende, nao compara As real com a demanda e nao
soma al a comprimentos de ancoragem.

Concretopy nao conhece estados B1/B2, nao seleciona extremos de envoltoria,
nao interpreta TQS e nao verifica concomitancia real de combinacoes.
O engineering-assistant seleciona os pares, realiza quantas chamadas forem
necessarias e compara as demandas retornadas. Nenhuma comparacao entre
chamadas e feita pela biblioteca.

Nao escolhe barras, altera arranjos, verifica comprimento disponivel no apoio,
decide barra reta/gancho, aplica tabela de dobras, dimensiona grampos ou otimiza
detalhamento. A verificacao de comprimento e area e uma operacao independente:
[ancoragem positiva no apoio](ancoragem.md#verificacao-de-ancoragem-positiva-no-apoio-extremo).
Herda limites e hipoteses do dimensionador existente, incluindo taxa minima.

## Alteracao deliberada da API recente

`mk_positivo_apoio_kncm`, `vk_max_abs_apoio_kn` e `vk_min_abs_apoio_kn` foram
substituidos por `mk_apoio_kncm` e `vk_apoio_kn`. Nao ha adaptador legado:
essa API recente foi corrigida antes de sua consolidacao.
`EstadoBArmaduraApoio` foi removido; `CondicaoBArmaduraApoio` guarda somente
uma decalagem, Fsd e As. Os antigos `estados` e `governantes` de B foram removidos.
O resultado global registra Md/Vd do unico par. A API de flexao, calcular_al
e calcular_ancoragem mantem seus comportamentos anteriores.
