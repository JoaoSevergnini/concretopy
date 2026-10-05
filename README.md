# concretopy

Biblioteca Python para cálculo de estruturas de concreto armado.

O `concretopy` é um núcleo de cálculo desacoplado de CAD, desenho, detalhamento gráfico e integração com TQS. A proposta é concentrar em um pacote único:

- propriedades de materiais;
- seções e elementos estruturais;
- verificações de flexão, cortante e flexo-compressão;
- apoio ao detalhamento de armaduras;
- calculadoras de aplicação, como reforço de furos em vigas.

## Convenções oficiais

As unidades públicas oficiais do pacote são:

- tensões: **MPa**
- geometria: **cm**
- bitolas: **mm**
- forças: **kN**
- momentos: **kN.cm**

O pacote também fornece conversões simples para entrada legada em **tf** e **tf.m**.

## Instalação

```bash
pip install -e .
```

## Exemplo rápido

```python
from concretopy import Concreto, Aco, VigaRetangular

viga = VigaRetangular(
    bw=20,
    h=60,
    cobrimento=3,
    concreto=Concreto(30),
    aco=Aco(500),
)

res_flex = viga.dimensionar_flexao(mk=18000)  # kN.cm
res_cort = viga.dimensionar_cortante(vk=120)  # kN
```

## Resistência de uma viga com armadura conhecida

```python
from concretopy import (
    Aco, Barra, CamadaArmaduraLongitudinal, Concreto, SecaoRetangular,
    verificar_flexao_viga_retangular,
)

resultado = verificar_flexao_viga_retangular(
    SecaoRetangular(bw=20, h=50, cobrimento=3),
    Concreto(30), Aco(500),
    [CamadaArmaduraLongitudinal(numero_barras=2, barra=Barra(16), d_cm=45)],
    gamma_f=1.4,  # opcional: Mk equivalente = MRd / gamma_f
    verificar_armadura_minima=True,
)
print(resultado.mrd_kncm)  # resistência de cálculo em kN.cm
print(resultado.ductilidade_atendida, resultado.armadura_minima_atendida)
```

`d_cm` é a distância da face comprimida ao centro de cada camada. Quando
omitido (`CamadaArmaduraLongitudinal(2, Barra(16))`), é calculado pelo critério
da aba VIGAS: primeira camada junto à face tracionada; seguintes com vão livre
de 2 cm se a bitola atual for menor que 25 mm, ou uma bitola atual em cm nos
demais casos. Informe as camadas da face tracionada para a comprimida quando
houver posições omitidas. Valores explícitos são preservados e servem de
referência para a próxima camada. A função pública
`calcular_alturas_uteis_camadas(secao, camadas)` retorna essas alturas em cm.

O modelo
usa bloco retangular e exige que todas as camadas tracionadas escoem. Se essa
hipótese falhar, `hipoteses_validas=False` e `mrd_kncm=None`, com diagnósticos
em `avisos`. Ductilidade e armadura mínima são verificações separadas;
nenhum desses campos representa aprovação global do detalhamento. Não há
dimensionamento de armadura nova nem truncamento da linha neutra.

Procedimento, referências numéricas e limites:
`.codex/analises/flexure_resistance_implementation.md`.

## Entrada legada em tf / tf.m

```python
from concretopy import tf_para_kn, tfm_para_kncm

vk = tf_para_kn(12.0)
mk = tfm_para_kncm(18.0)
```

## Calculadora de furos

```python
from concretopy import CalculadoraReforcoFuros

calc = CalculadoraReforcoFuros.from_tf_tfm(
    h=60,
    b=20,
    h_furo=10,
    b_furo=12,
    fck=30,
    C=15,
    Mk_tfm=18.0,
    Vk_tf=12.0,
    cobrimento=3,
    armadura_superior=[(2, 12.5)],
    armadura_inferior=[(2, 12.5)],
)

resultado = calc.calcular_reforco()
print(resultado.memorial)
```

## API pública

A interface pública estável do pacote está em `concretopy.api` e é reexportada em `concretopy`.

Principais nomes públicos:

- `Concreto`
- `Aco`
- `SecaoRetangular`
- `SecaoPoligonalArmada`
- `Barra`
- `BarraPosicionada`
- `VigaRetangular`
- `PilarPoligonal`
- `CalculadoraReforcoFuros`
- `FuroRetangular`
- `ResultadoFlexao`
- `ResultadoCortante`
- `ResultadoFlexoCompressao`
- `ResultadoReforcoFuro`

## Documentação complementar

- `docs/hipoteses_e_limites.md`
- `docs/checklist_release.md`
- `docs/validacao_flexocompressao.md`
- `docs/api_publica.md`
- `CHANGELOG.md`

## Observação importante

Esta versão está organizada como release estável de pacote. Ainda assim, para uso externo mais amplo, continua sendo prudente validar continuamente os resultados com casos reais do escritório e exemplos de referência.
