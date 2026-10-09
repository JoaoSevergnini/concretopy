# Ancoragem de armaduras

A API inicial calcula ancoragem reta de barras nervuradas tracionadas de
armadura passiva, sem gancho nem barras transversais soldadas. A aderencia
e obrigatoriamente classificada pelo usuario; o modulo nao infere posicoes.

## Referencias e rastreabilidade

- Trechos da NBR 6118:2023 fornecidos pelo usuario: 9.2 (disposicoes gerais),
  9.3.1 (classificacao da aderencia), 9.3.2.1 (fbd e eta2/eta3),
  9.4.2.4 (lb e piso 25 phi) e 9.4.2.5 (lb_nec, alfa e lb_min).
- Eta1 = 2,25 para o escopo de barras nervuradas: valor da planilha
  `Verificacao - VIGAS E LAJES - R07 - EM REVISAO.xlsm`, aba VIGAS,
  celulas R27:R28, associado pelo usuario ao uso exclusivo de nervuradas.
  O trecho de 9.3.2.1 remete a Tabela 8.2, nao fornecida; nao se implementam
  coeficientes de outras superficies nem se afirma conferencia dessa tabela.
- fctd e fyd reutilizam os materiais existentes, com gamma_c=1,4 e
  gamma_s=1,15 por padrao. As formulas dos materiais nao foram alteradas.

## Calculo e unidades

Tensoes em MPa; bitola em mm; areas em cm2; comprimentos em cm.

```text
phi_cm = bitola_mm / 10
eta1 = 2,25
eta2 = 1,0 (boa) ou 0,7 (ma aderencia)
eta3 = 1,0 para phi < 32 mm; (132 - phi_mm)/100 para phi >= 32 mm
fbd = eta1 * eta2 * eta3 * fctd
lb = max(phi_cm/4 * fyd/fbd, 25 * phi_cm)
lb_min = max(0,3 * lb, 10 * phi_cm, 100/10 cm)
lb_nec = max(lb * As_calculada/As_efetiva, lb_min)  # alfa = 1
atende = comprimento_disponivel_cm >= lb_nec
```

A razao MPa/MPa e adimensional: nao ha conversao para kN/cm2 nesse calculo.
Nao se arredonda o resultado antes da comparacao. Sem comprimento disponivel,
`atende` e `None`; comprimento insuficiente retorna `False`.

```python
from concretopy import Aco, Concreto, CondicoesAncoragem, calcular_ancoragem

resultado = calcular_ancoragem(
    concreto=Concreto(30),
    aco=Aco(500),
    bitola_mm=16,
    as_calculada_cm2=6.20,
    as_efetiva_cm2=8.04,
    condicoes=CondicoesAncoragem(boa_aderencia=True),
    comprimento_disponivel_cm=50,
)
print(resultado.lb_nec_cm, resultado.atende)
```

Pode-se fornecer `Barra(16).diametro_mm` para reutilizar uma barra existente.
Nao se cria outro modelo de aco, concreto ou barra. `CondicoesAncoragem`
e `ResultadoAncoragem` sao dataclasses imutaveis. O resultado registra
fctd/fyd/fbd em MPa, eta1/eta2/eta3 e os tres comprimentos em cm.

## Dominio e validacoes

- Concreto entre 20 e 90 MPa, seguindo o dominio adotado pela verificacao
  de flexao existente; para fck > 50 MPa reutiliza a expressao de Concreto.
- Numeros finitos; bitola, areas, resistencias e gammas positivos.
- Eta3 deve ser positivo. O limite matematico phi < 132 mm nao e um
  catalogo de bitolas comerciais nem uma certificacao do uso de tais barras.
- As_calculada <= As_efetiva: rejeita area insuficiente em vez de sugerir
  que comprimento adicional compensa a falta de aco. As duas areas devem
  corresponder as barras e a solicitacao efetivamente analisadas.
- Comprimento disponivel >= 0, medido da secao onde a forca sera ancorada.
- Tipos invalidos geram TypeError; dados fora do dominio geram ValueError,
  seguindo o padrao das verificacoes existentes. Nenhuma excecao nova.

## Diferencas intencionais em relacao a planilha

A planilha nao aplica o piso 25 phi: para C50, fyk=500 MPa, phi=25 mm e boa
aderencia, mostra 59,324178722 cm; o modulo retorna lb=62,5 cm. Com ma
aderencia, lb=84,748826746 cm permanece igual. Os testes registram tanto a
expressao da planilha quanto a aplicacao posterior do piso normativo.

O modulo acrescenta eta3 por bitola, lb_min e a razao entre areas. Nao copia
os rotulos lb_nec da planilha quando a celula calcula apenas lb. A primitiva calcular_ancoragem permanece com alfa=1. A nova verificacao de
apoio abaixo admite alfa=0,7 somente com gancho previamente validado pelo
chamador conforme 9.4.2.5; nao valida sua geometria.

## Arquitetura e limites

`normas/nbr6118.py` guarda coeficientes e limites elementares;
`verificacoes/ancoragem.py` coordena propriedades, comprimentos e verificacao;
`resultados.py` guarda o resultado. A API publica expoe as condicoes, os resultados e as funcoes de calculo
e verificacao de ancoragem. Nao ha importacao de elementos no modulo.

O calculo de ancoragem nao inclui classificacao geometrica automatica, desenhos,
TQS, geometria de ganchos, compressao, emendas, soldas ou verificacao de confinamento.
`calcular_ancoragem.atende` verifica exclusivamente o comprimento, nao o detalhamento global.
Nao existe detalhamento/ancoragens.py porque nenhuma geometria e gerada.
Novos regimes exigirao condicoes e regras explicitas, sem flags ficticias
que parecam habilitar calculos ainda nao implementados.

## Decalagem: familia independente

`calcular_al` em `verificacoes/decalagem.py`, tambem exportada na raiz e em
`concretopy.api`, calcula exclusivamente a primitiva deterministica:

```python
from concretopy import Concreto, calcular_al
r = calcular_al(concreto=Concreto(40), b_cm=19, d_cm=67.5625,
                vk_abs_kn=56.4, gamma_f=1.4, gamma_c=1.4)
# r.vsd_kn = 78.96; r.vc0_kn aproximadamente 135.12690073160
# r.al_base_cm = r.al_cm = 67.5625
```

```text
Vsd = gamma_f * vk_abs_kn
Vc0 = 0.6 * (Concreto.fctd(gamma_c) * 0.1) * b_cm * d_cm
al_base = d                              se Vsd <= Vc0
al_base = 0.5*d * Vsd/(Vsd - Vc0)         se Vsd > Vc0
al_min = 0.5*d; al_max = d
al = max(min(al_base, al_max), al_min)
```

Fonte: equacao confirmada pelo engenheiro, auditoria
`../.codex/analises/longitudinal_anchorage_audit.md` e recorte normativo
fornecido nesta implementacao (alinea c, decalagem do diagrama de forca no
banzo tracionado; numero completo do item nao visivel no recorte).
Hipoteses explicitas: estribos verticais (cotg alfa = 0) e Vc = Vc0.
Nao implementa estribos inclinados ou alteracao de Vc por esforco normal.

Forcas em kN, geometria/comprimentos em cm, resistencia em MPa.
A conversao 1 MPa = 0.1 kN/cm2 esta explicita; nenhuma conversao tf existe
na primitiva. Vk e magnitude caracteristica nao negativa, nao Vsd. Nao ha
abs() silencioso; Vk negativo gera ValueError e Vk=0 e valido.
O chamador seleciona Vk e d; a funcao nao conhece vao, apoio, x ou viga.
Usa o mesmo d em todas as etapas, sem inferir camadas ou centroides.
Validacoes seguem TypeError/ValueError; fck entre 20 e 90 MPa, geometria e
coeficientes positivos e finitos. Resultados nao representaveis sao rejeitados.

`ResultadoDecalagemAl` e imutavel e registra entradas, gamma_c/gamma_f,
fctd, Vsd, Vc0, al_base, limites, al final e branch. A base e preservada:
para Vc0 < Vsd < 2Vc0, al_base > d mas al = d. Na igualdade Vsd=Vc0
nao ha divisao. Para Vsd=3Vc0, al=0.75d; para grandes Vsd tende a 0.5d.
A primitiva nao verifica Vrd2 e nao representa aprovacao ao cortante.

Ha duas familias independentes: fbd/lb/lb_min/lb_nec (ancoragem) e
al_base/al limitado (decalagem). Nao se soma al a lb ou lb_nec automaticamente.
`calcular_ancoragem.atende` permanece exclusivamente comprimento_disponivel
>= lb_nec. Composicao, corte, escalonamento, apoio e N3 ficam para o chamador.
A regra de selecao de Vk e documentada no engineering-assistant, nao aplicada
por esta API. A fachada VigaRetangular.calcular_decalagem tambem exige d explicito.


### Uso pela VigaRetangular

O metodo `calcular_decalagem` delega a `calcular_al`, usando `self.concreto`
e `self.bw`. `d_cm` continua obrigatorio; nao usa a bitola padrao de secao.d().
A selecao da magnitude caracteristica do cortante continua com o chamador.

```python
from concretopy import Aco, Concreto, VigaRetangular

viga = VigaRetangular(
    bw=19, h=72, cobrimento=2.5,
    concreto=Concreto(40), aco=Aco(500),
)
resultado = viga.calcular_decalagem(
    vk_abs_kn=56.4, d_cm=67.5625,
    gamma_f=1.4, gamma_c=1.4,
)
# resultado.al_base_cm == resultado.al_cm == 67.5625
```

O retorno e o mesmo ResultadoDecalagemAl imutavel da funcao pura, com
forcas em kN, resistencia em MPa e comprimentos em cm. Hipoteses e
validacoes sao as da primitiva; nao adiciona verificacao de ancoragem.


## Demanda de armadura no apoio

A nova rotina [calcular_armadura_positiva_apoio](armadura_apoio.md) determina
As necessaria pelas condicoes A/B/C. Nao chama calcular_ancoragem, nao muda
seu atende e nao verifica comprimento disponivel ou escolha de gancho.

## Verificacao de ancoragem positiva no apoio extremo

`verificar_ancoragem_positiva_apoio` compoe a primitiva existente e retorna
`ResultadoVerificacaoAncoragemApoio` imutavel. Nao altera calcular_ancoragem.

```python
from concretopy import (Concreto, Aco, CondicoesAncoragem,
                        verificar_ancoragem_positiva_apoio)
r = verificar_ancoragem_positiva_apoio(
    concreto=Concreto(50), aco=Aco(500), bitola_mm=25,
    as_calculada_cm2=4, as_efetiva_cm2=5,
    condicoes=CondicoesAncoragem(boa_aderencia=True),
    comprimento_disponivel_cm=25, gancho_valido=False,
)
# lb=62.5 cm; lb_min=25 cm; lb_nec_sem_min=lb_nec=50 cm.
# As_corr_matematica=As_corr=10 cm2; As_adicional=5 cm2; atende=False.
```

- `as_calculada_cm2`: demanda estrutural que precisa ser ancorada, em cm2.
  Normalmente a demanda de apoio governante selecionada pelo chamador entre
  as chamadas que ele realizou, nao pela biblioteca.
- `as_efetiva_cm2`: area real das barras que chegam e participam desta
  ancoragem, em cm2. Area inferior a demanda e aceita como configuracao
  nao atendente e diagnosticada separadamente.
- `comprimento_disponivel_cm`: comprimento em cm, informado diretamente.
  Nao se calcula comprimento do apoio menos cobrimento no Concretopy.
- `gancho_valido`: booleano informado pelo chamador, que verifica previamente
  geometria e condicoes normativas, incluindo cobrimento aplicavel de 9.4.2.5.
  True usa alpha=0.7; False usa alpha=1.0. Alpha e adimensional.
- `bitola_mm`: diametro nominal da barra em mm; mudanca de bitola exige
  recalculo, inclusive de eta3/25phi. Aderencia e sempre informada.
- `gamma_c`, `gamma_s`: coeficientes adimensionais, positivos e finitos;
  padroes 1.4 e 1.15. Tensoes do resultado em MPa.

As areas e o comprimento devem ser finitos e estritamente positivos.
Comprimento zero e rejeitado porque o calculo inverso e indefinido; a
primitiva legada continua aceitando zero para verificacao somente de comprimento.
Comprimento **positivo abaixo de lb_min nao gera excecao nem retorno antecipado**.
Materiais, bitola e aderencia seguem os dominios existentes.

```text
lb e lb_min = regras existentes, sem duplicacao das formulas
lb_nec_sem_min = alpha * lb * As_calculada / As_efetiva
lb_nec = max(lb_nec_sem_min, lb_min)

area_suficiente = As_efetiva >= As_calculada
comprimento_suficiente = comprimento_disponivel >= lb_nec
comprimento_menor_lb_min = comprimento_disponivel < lb_min
atende = area_suficiente AND comprimento_suficiente AND NOT comprimento_menor_lb_min

As_corr_matematica = alpha * lb * As_calculada / comprimento_disponivel
As_corr = max(As_calculada, As_corr_matematica)
As_adicional = max(0, As_corr - As_efetiva)
```

O resultado preserva separadamente lb, lb_min, alpha, parcela variavel,
lb_nec, comprimento e todos os diagnosticos. Insuficiencia de aco nao e
mascarada por comprimento suficiente. `avisos` explica cada falha.

O calculo inverso e uma transformacao algebrica para a parcela variavel,
nao uma nova regra normativa de detalhamento. Mesmo abaixo de lb_min,
As_corr_matematica, As_corr e As_adicional sao calculados: **aumento de area
sozinho nao resolve a falta de comprimento minimo**. Exemplo anterior com
comprimento=10 cm: As_corr=25 cm2 e As_adicional=20 cm2, mas lb_min=25 cm
continua impedindo atendimento mesmo com a area corrigida.

As_corr pressupoe manter bitola, materiais, aderencia e alpha desta chamada.
As_adicional e area longitudinal adicional hipotetica, nunca automaticamente
area de grampo. Nao escolhe barras, arranjos, dobras, gancho, grampos ou solucao
otima. Nao verifica geometria do gancho, nao interpreta desenhos/TQS e nao
altera prancha. `atende` cobre somente area e comprimento neste procedimento,
nao certifica o detalhamento global. Nao ha soma automatica com al.
