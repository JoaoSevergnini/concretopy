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
