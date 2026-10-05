# Verificação da resistência à flexão retangular

## Atualização: alturas úteis automáticas

Por solicitação posterior, `CamadaArmaduraLongitudinal.d_cm` passa a aceitar
`None` (padrão). A função pública `calcular_alturas_uteis_camadas(secao,
camadas)` retorna uma tupla de d em cm e a verificação de flexão a utiliza
quando alguma posição é omitida. Os trechos abaixo que descrevem posições
exclusivamente explícitas registram a versão inicial; esta atualização
amplia esse contrato, sem mudar o cálculo resistente com posições explícitas.

O cálculo reproduz o critério geométrico de VIGAS!K5:K7 documentado neste
relatório: d₁ = h−c−φₜ/10−φ₁/20; dᵢ = dᵢ₋₁−eᵥ,ᵢ−φᵢ₋₁/20−φᵢ/20;
eᵥ,ᵢ = 2 cm se φᵢ<25 mm e φᵢ/10 cm caso contrário. Usa-se a bitola da
camada atual, inclusive no limiar exato de 25 mm, sem substituir a regra
por `max(2,phi/10)` (que diferiria entre 20 e 25 mm).

A ordem da lista, quando há d omitido, é da face tracionada para a comprimida.
Cada valor explícito é preservado e serve de referência para a posição
omitida seguinte. As entradas não são modificadas. Lista inteiramente
explícita continua aceitando a ordem anterior, preservando os resultados.
O auxiliar rejeita alturas não positivas/não finitas; a verificação de flexão
mantém a validação geométrica completa já implementada. O resultado apresenta
os d efetivamente usados e aviso de uso do critério automático. Não se
certifica espaçamento normativo nem se altera a hipótese resistente.

Exemplo: para b=25, h=76, c=2,5 cm, estribo 8 mm e camadas de 20, 16 e
12,5 mm, as posições automáticas são 71,7; 67,9; 64,475 cm.

```python
camadas = [
    CamadaArmaduraLongitudinal(3, Barra(20)),
    CamadaArmaduraLongitudinal(2, Barra(16)),
    CamadaArmaduraLongitudinal(2, Barra(12.5)),
]
ds = calcular_alturas_uteis_camadas(SecaoRetangular(25, 76, 2.5, 8), camadas)
```

Foram acrescentados 11 testes em `tests/test_alturas_uteis_camadas.py`: os
quatro casos geométricos A–D da referência anterior com d omitido, limiar de
25 mm (24,9; 25; 25,1), posições mistas, preservação de posições explícitas,
geometria impossível e exportação/validação do auxiliar. A suíte atual tem
76 testes aprovados. As equações de resistência e os goldens anteriores
permanecem preservados.

## Modelo definido antes da implementação

Data: 04/10/2026. Esta funcionalidade resolve exclusivamente flexão simples de seção retangular com camadas tracionadas conhecidas. O modelo inicial é o bloco retangular de concreto com todas as camadas tracionadas em escoamento. Não é inversão do dimensionador nem chamada ao motor poligonal. Os parâmetros do bloco e limites de deformação são obtidos dos objetos `Concreto` e `Aco` existentes. A capacidade só é disponibilizada se a compatibilidade de deformações justificar a hipótese de escoamento de **cada** camada.

### Tradução da aba VIGAS para equações físicas

Inspeção somente leitura do XML do arquivo `Verificação - VIGAS E LAJES - R07 - EM REVISÃO.xlsm`, no caminho informado na conversa. Macros e scripts embutidos não foram executados.

- `K5`: d₁ = h − c − φₜ/10 − φ₁/20. É a distância, em cm, da face comprimida ao centro das barras inferiores. Cobrimento c em cm; diâmetros em mm.
- `K6` e `K7`: dᵢ = dᵢ₋₁ − eᵥ,ᵢ − (φᵢ₋₁ + φᵢ)/20. A expressão representa distância vertical entre centros. O vão livre adotado na planilha é 2 cm se φᵢ < 25 mm; caso contrário, φᵢ/10 cm. O significado geométrico é inequívoco; a justificativa normativa dessa seleção não foi demonstrada e não será imposta pela nova API.
- `L5:L7`: Asᵢ = nᵢ π(φᵢ/10)²/4, em cm².
- `M5:M7`: primeiro momento das áreas de aço, Asᵢ dᵢ, em cm³. `B7`, `L13`, `O13`: d equivalente = ΣAsᵢdᵢ / ΣAsᵢ. É o braço da resultante de tração se todas as barras têm a mesma tensão.
- `I14`, `L14`, `O14`: x = As fyd / (0,68 b fcd), com tensões convertidas a kN/cm². O coeficiente 0,68 = 0,85 × 0,8 representa intensidade do bloco e profundidade λx, respectivamente. A expressão pressupõe concreto sem tração e aço tracionado em escoamento, com equilíbrio axial C=T.
- Linha 15: x/d, adimensional, sem truncamento.
- Linha 16: Mdresist = As fyd [d − 0,4 min(x,0,45d)]. O fator 0,4 é λ/2 para λ=0,8. Os fatores finais `/10*0.01` convertem kN.cm para tf.m usando 10 kN/tf. A expressão usa x calculado no equilíbrio, mas **trunca apenas x no braço** quando x/d>0,45. Não foi identificada justificativa física para essa alteração: o mesmo bloco deixa de equilibrar a força de aço. Essa parte não será reproduzida. Fica registrada como dúvida do procedimento do escritório, sem interpretação normativa inventada.
- Linha 17: Mkresist = Mdresist/1,4. É um limiar equivalente de solicitação característica para comparação, supondo Md=1,4Mk. Não é resistência calculada com materiais característicos.

### Equações adotadas para a rotina nova

Asᵢ é obtido por `Barra.area_cm2`, reutilizando a implementação existente. As = ΣAsᵢ; d_eq = ΣAsᵢdᵢ/As. fcd = `Concreto.fcd(gamma_c)` e fyd = `Aco.fyd(gamma_s)` em MPa; nas forças usar 0,1fcd e 0,1fyd em kN/cm².

T = As × 0,1fyd; C = αc × 0,1fcd × b × λx. De C=T:

    x = T / (αc × 0,1fcd × b × λ)
    z = d_eq − λx/2
    MRd = T × z = Σ(Asᵢ × 0,1fyd × (dᵢ − λx/2))

T e C em kN; x, z, d e b em cm; MRd em kN.cm. x não é limitado artificialmente. O resultado x é um candidato derivado da hipótese de escoamento até essa hipótese ser validada.

Compatibilidade: d_max = max(dᵢ); εc = min(εcu, εsu x/(d_max−x)); εsᵢ = εc(dᵢ−x)/x; εyd = fyd/Es. Essa escolha respeita o limite de deformação do concreto ou do aço mais distante da face comprimida. Todas as camadas devem estar tracionadas e satisfazer εyd ≤ εsᵢ ≤ εsu, com linha neutra interna à seção. Se isso falhar, o MRd não é emitido (`None`), e o resultado explica a hipótese inválida. Não há solver elástico ou armadura comprimida nesta versão.

Ductilidade é separada: comparar x/d_eq a 0,45 para fck≤50 MPa e 0,35 acima, conforme limite já adotado no dimensionador atual. O limite é aplicado a d_eq como convenção explícita deste modelo multicamadas, não como certificação normativa universal. Se todas as camadas escoam mas x/d ultrapassa o limite, a capacidade do modelo continua disponível, com ductilidade não atendida. Se o modelo é inválido, o status de ductilidade é indisponível (`None`); x/d candidato continua visível.

Gamma_c=1,4 e gamma_s=1,15 por padrão. Gamma_f é opcional e não participa de MRd. Quando fornecido, M equivalente característico = MRd/gamma_f. Não há comparação interna com solicitação.

### Representação e limites adotados

`Barra` já representa diâmetro/área; `Armadura` representa quantidade, mas não uma posição vertical; `BarraPosicionada` representa cada barra, sem quantidade agregada. O tipo pequeno `CamadaArmaduraLongitudinal(numero_barras, barra, d_cm)` reutiliza `Barra` e acrescenta número de barras e d explícito em cm, medido da face comprimida ao centro. A API não infere espaçamento vertical nem usa `delta_cm=0.8`. A ordem de entrada é preservada nos resultados. Geometria impossível é rejeitada; verificação normativa de espaçamento/ancoragem continua fora do escopo.

A resistência nunca substitui As por As,min. A verificação de mínimo é opcional, separada e baseada na tabela existente apenas para fck inteiro cadastrado. Demais casos têm diagnóstico de mínimo indisponível sem impedir o cálculo resistente.

O modelo é restrito a 20≤fck≤90 MPa, intervalo compatível com as expressões e tabela dos objetos atuais. Seu uso não declara equivalência à norma vigente. O [catálogo oficial da ABNT](https://www.abntcatalogo.com.br/default.aspx) foi consultado; ele não fornece nesta análise o conteúdo das cláusulas para auditar os coeficientes legados. A implementação preserva os parâmetros existentes, sem prometer atualização normativa.

## Arquivos alterados e criados

| Arquivo | Alteração |
| --- | --- |
| `concretopy/verificacoes/flexao.py` | Acrescenta `verificar_flexao_viga_retangular`; preserva o corpo do dimensionador existente. |
| `concretopy/armaduras.py` | Acrescenta camada tipada e validada que reutiliza `Barra.area_cm2`. Classes anteriores preservadas. |
| `concretopy/resultados.py` | Acrescenta `ResultadoVerificacaoFlexao`; resultados anteriores preservados. |
| `concretopy/api.py`, `concretopy/__init__.py`, `concretopy/verificacoes/__init__.py` | Exportam a nova função e, na API principal, os dois tipos novos. |
| `tests/test_resistencia_flexao.py` | Testes golden, diagnóstico de hipóteses, geometria, materiais, coeficientes, mínimo, API e comparação poligonal. |
| `tests/references/flexure_resistance.json` | Entradas, valores esperados, origem e tolerâncias dos oito casos golden. |
| `README.md`, `docs/api_publica.md` | Exemplo headless e contrato da nova API. |
| `.codex/analises/flexure_resistance_implementation.md` | Este relatório, inicialmente escrito antes da implementação e completado após os testes. |

Não foram modificados `materiais.py`, `secoes.py`, `nbr6118.py`, `viga.py`, `flexo_compressao.py` nem os testes existentes. O relatório da arquitetura atual permanece como registro da etapa anterior.

## API e resultado estruturado

```python
from concretopy import (
    Aco, Barra, CamadaArmaduraLongitudinal, Concreto, SecaoRetangular,
    verificar_flexao_viga_retangular,
)

r = verificar_flexao_viga_retangular(
    SecaoRetangular(25, 76, 2.5, 8), Concreto(40), Aco(500),
    [
        CamadaArmaduraLongitudinal(4, Barra(20), 71.7),
        CamadaArmaduraLongitudinal(2, Barra(16), 67.9),
    ],
    gamma_c=1.4, gamma_s=1.15,
    gamma_f=1.4,  # somente para Mk equivalente, não para calcular MRd
    verificar_armadura_minima=True,
)
```

A função está em `flexao.py` e pode ser importada de `concretopy`, `concretopy.api` ou `concretopy.verificacoes`. Não foi criado método adicional na viga nem integração externa.

| Campos | Significado |
| --- | --- |
| `as_total_cm2`, `as_por_camada_cm2` | Área efetivamente fornecida; não substituída pelo mínimo. |
| `d_por_camada_cm`, `d_equivalente_cm` | Centros das camadas e centroide ponderado pela área. |
| `linha_neutra_cm`, `x_sobre_d` | Equilíbrio do modelo escoado; se inválido, são valores **candidatos**, não resistência validada. |
| `limite_x_sobre_d`, `ductilidade_atendida` | Limite independente; status `True`/`False` se o modelo é válido e `None` se não é possível afirmar uma verificação válida. |
| `mrd_kncm` | Capacidade de cálculo do modelo, positiva como magnitude; `None` se hipóteses inválidas. |
| `mk_equivalente_kncm` | MRd/gamma_f; `None` quando gamma_f é omitido ou MRd é indisponível. |
| `hipoteses_validas` | Compatibilidade da seção com o modelo de camadas tracionadas em escoamento. Não significa aprovação global. |
| `deformacoes_aco`, `camadas_escoadas` | Diagnóstico por camada, na ordem de entrada; `None` quando nem o regime tracionado é viável. |
| `as_min_cm2`, `armadura_minima_atendida` | Checagem opcional independente; `None` se não solicitada ou tabela não aplicável. |
| `parametros` | Modelo, unidades, geometria, gamma_c/s/f, fck/fyk/Es, fcd/fyd, αc, λ, εcu, εsu, εyd e εc adotada. Tensões em MPa; deformações adimensionais. |
| `avisos` | Mensagens explícitas de hipótese inválida, ductilidade ou mínimo. Não há campo genérico `OK`. |

O resultado é uma dataclass e pode ser serializado explicitamente com `dataclasses.asdict` e `json.dumps`; não exige Excel, GUI, serviço ou pacote externo de execução. Não recebe solicitação, não aprova detalhamento e não produz dimensionamento novo.

## Múltiplas camadas e geometria

Cada camada tem bitola única e quantidade inteira positiva, mas camadas diferentes podem usar bitolas diferentes. É necessário informar d de todas as camadas. Não há camada de quantidade zero: camadas vazias da planilha devem ser omitidas.

O centro da barra deve estar dentro do estribo e respeitar o cobrimento geométrico fornecido: a margem até cada face é c + φₜ/10 + φᵢ/20, reutilizando `SecaoRetangular.d_linha` e `d`. O somatório dos diâmetros de uma camada deve caber na largura interna b−2(c+φₜ/10). Envelopes verticais de camadas devem ser separados por pelo menos a soma dos raios; camadas coincidentes ou sobrepostas são rejeitadas. Essas são verificações geométricas, sem certificar os espaçamentos mínimos normativos. Sem coordenadas horizontais, o modelo não representa barras intercaladas que permitiriam envelopes verticais sobrepostos.

Convenção: a face comprimida é a origem da profundidade. Para uma viga com tração inferior, d é medido do topo para baixo. Para tração superior, espelhar a referência e medir da face inferior comprimida. O resultado é magnitude, sem sinal global do momento ou orientação CAD. O usuário é responsável por definir a face comprimida correta.

Quando todas as camadas escoam no mesmo fyd, o centroide de área é também o centro da resultante de tração e a expressão de MRd equivale à soma dos momentos de todas as camadas. Se uma camada não escoa, essa equivalência por área deixa de ser válida: o modelo se recusa a emitir capacidade, em vez de tratar a camada como se estivesse escoada.

## Tratamento de validade, x/d e mínimo

Os três conceitos têm retornos distintos:

1. **Capacidade:** depende de equilíbrio e compatibilidade das camadas no modelo declarado. Aço não escoado, camada na zona comprimida ou linha neutra fora da seção levam a `hipoteses_validas=False`, MRd/Mk equivalente indisponíveis e diagnóstico.
2. **Ductilidade:** se o modelo é válido, compara x/d_eq ao limite 0,45 ou 0,35, sem alterar x nem MRd. A comparação aceita igualdade com tolerância absoluta de 1e-12 em x/d para arredondamento; não é tolerância de projeto. Para escoamento usa-se tolerância relativa de 1e-12 em εyd. Não há tolerância física ampliada de equilíbrio axial nesse cálculo fechado.
3. **Mínimo:** se solicitado e a tabela é aplicável, compara As fornecida a taxa_min × bh/100. fck não inteiro ou ausente da tabela, inclusive 55 MPa, resulta em status indisponível com aviso. Não há truncamento de fck nem interpolação inventada. Uma área inferior ao mínimo mantém sua capacidade calculada e recebe um status separado.

A rotina não aplica taxa máxima de 4% como corte de capacidade nem certifica o restante do detalhamento. Os dados de materiais e coeficientes devem ser finitos e positivos; cobrimento pode ser zero. O módulo Es deve permitir εyd≤εsu. `fck` fora de 20–90 MPa é rejeitado nesta rotina sem alterar o contrato dos objetos legados.

## Relação com a planilha e diferenças dos motores

### Planilha VIGAS

Para fck≤50 MPa, com posições coincidentes, todas as camadas escoadas e x/d≤0,45, o novo MRd coincide com a expressão física da linha 16 antes da conversão para tf.m. O caso real A demonstra essa relação por reprodução matemática, sem assumir o cache como referência normativa.

Acima de 0,45d, o novo cálculo preserva x. A expressão da planilha usa um braço maior, pois substitui x apenas nesse braço por 0,45d. Essa divergência é intencional e documentada; fica pendente esclarecer a justificativa do procedimento do escritório. Não há tentativa de reproduzir esse truncamento como capacidade equilibrada.

Para fck>50 MPa, a rotina usa αc, λ e εcu variáveis dos objetos Concretopy, enquanto as fórmulas retangulares da região inspecionada da planilha mantêm 0,68 e 0,4. Essas entradas não são declaradas equivalentes. O espaço vertical condicional da planilha é reproduzido **apenas nas entradas dos casos de referência**, não imposto como regra pela API.

O caso real A tem espaçamentos horizontais pequenos na planilha (`VIGAS!O5` aproximadamente 0,343 cm e `N5` negativo na hipótese com espaço para vibrador). O cálculo de resistência não aprova esse espaçamento: esse caso comprova uma equação, não um detalhamento globalmente adequado.

### Dimensionador retangular existente

O dimensionador recebe Mk, majora a solicitação, calcula áreas necessárias, impõe mínimo e resolve armadura dupla quando requerido. A verificação recebe camadas reais, não recebe solicitação, não impõe mínimo e não adiciona aço. Utiliza a mesma família de parâmetros dos materiais e os limites de ductilidade já adotados, mas verifica escoamento camada a camada. Não chama nem inverte `dimensionar_flexao_viga_retangular`. O corpo desse dimensionador foi comparado por AST à versão HEAD e permaneceu idêntico.

### Motor poligonal existente

O poligonal calcula esforço normal e dois componentes de momento para contorno/barras posicionadas, mediante busca de linha neutra. Tem profundidade 0,8x, tensão 0,8fcd, Es fixo na lei do aço e tolerância axial baseada na capacidade de referência. A rotina nova usa profundidade λx, tensão αc fcd e Es/limites do objeto Aco; resolve equilíbrio fechado no regime de camadas escoadas, sem esforço normal.

**Comparação diagnóstica executada:** seção b=20 cm, h=50 cm, c=3 cm, estribo 5 mm, C30, fyk=500 MPa e Es=210.000 MPa. Duas barras de 16 mm a d=45 cm. Contorno poligonal anti-horário `[(0,0),(20,0),(20,50),(0,50)]`, barras em `(5,5)` e `(15,5)` cm. Motor poligonal com Nd=0 e ângulo 0°; compara-se `myd_resistente`, conforme convenção de braço y do motor. Parâmetros de segurança iguais nos dois cálculos.

| Execução | MRd novo (kN.cm) | MRd poligonal (kN.cm) | Diferença absoluta (kN.cm) | Diferença percentual em relação ao novo |
| --- | --- | --- | --- | --- |
| Poligonal com tolerâncias padrão, relativa 0,01 e absoluta 0,001 kN | 7448,082857991116 | 7041,829214430380 | 406,253643560736 | 5,454472665068% |
| Diagnóstico adicional: tolerância relativa 0 e absoluta 1e-8 kN | 7448,082857991116 | 7421,860490937440 | 26,222367053676 | 0,352068680675% |

No cálculo padrão, o residual axial retornado foi +18,836460721519 kN, a resistência axial −18,836460721519 kN e x=5,6875 cm. O cálculo novo tem x=5,999290318876 cm. Na chamada com tolerância menor, o poligonal obteve residual aproximadamente −5,08e-9 kN e x=6,374245963991 cm. Assim, a diferença de 5,45% inclui a tolerância axial, além da hipótese do bloco. O diagnóstico com tolerância menor evidencia que os modelos também diferem mesmo com equilíbrio axial praticamente exato. A chamada utiliza os argumentos já existentes; nenhum motor ou valor padrão foi modificado.

## Golden tests rastreáveis

Referências completas em `tests/references/flexure_resistance.json`: entradas por camada, áreas por camada e total, d_eq, x, x/d, MRd, Mk equivalente, validade, ductilidade e origem. Valores gerados por cálculo independente com `decimal.Decimal`, precisão de 50 dígitos, π literal com 50 algarismos; esse cálculo não importou Concretopy nem leu os caches para gerar saídas. Não houve recálculo no Excel: a alternativa usada foi reprodução matemática das equações inspecionadas, permitida pelo escopo.

Todos os goldens usam fyk=500 MPa, Es=210.000 MPa, gamma_c=1,4, gamma_s=1,15, gamma_f=1,4. Tolerância numérica de comparação: relativa 1e-12 e absoluta 1e-8, nas unidades de cada campo (kN.cm nos momentos, cm nos comprimentos, cm² nas áreas). Os valores abaixo são arredondados para leitura; o JSON contém os valores usados nos testes.

| Caso | Entrada de camadas `(n, φ_mm, d_cm)` | d_eq (cm) | x (cm) | x/d | MRd (kN.cm) | Mk equivalente (kN.cm) | Origem / status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A — uma camada | `(8,20,71.7)` | 71,700000000 | 22,497338696 | 0,313770414 | 68515,201277770 | 48939,429484122 | Entradas reais de VIGAS; equações I12:I17 reproduzidas, modelo válido. |
| B — duas camadas | `(4,20,71.7)`, `(2,16,67.9)` | 70,778787879 | 14,848243539 | 0,209783806 | 46762,266488665 | 33401,618920475 | Entradas sintéticas com geometria K5/K6 e procedimento L12:L17, válido. |
| C — três camadas | `(3,20,71.7)`, `(2,16,67.9)`, `(2,12.5,64.475)` | 69,623728081 | 14,233081934 | 0,204428610 | 44196,501779166 | 31568,929842261 | Sintético com geometria K5:K7 e O12:O17, válido. |
| D — bitolas diferentes, camada com φ≥25 | `(3,16,71.9)`, `(2,25,67.35)` | 69,081615461 | 14,187384215 | 0,205371344 | 43693,626944756 | 31209,733531969 | Sintético; reproduz ramo de vão livre de 2,5 cm em K6, válido. |
| E− — abaixo do limite | `(4,20,41.75452616143966)` | 41,754526161 | 18,747782246 | 0,449 | 18715,922548215 | 13368,516105868 | Equilíbrio analítico; d=x/0,449, válido e dúctil pelo critério adotado. |
| E0 — no limite | `(4,20,41.66173832552534)` | 41,661738326 | 18,747782246 | 0,45 | 18665,226620624 | 13332,304729017 | d=x/0,45; válido, igualdade aceita. |
| E+ — acima do limite | `(4,20,41.569361965601786)` | 41,569361966 | 18,747782246 | 0,451 | 18614,755508676 | 13296,253934768 | d=x/0,451; modelo válido, ductilidade não atendida, sem truncamento. |
| F — fora da validade de escoamento | `(6,25,45)` | 45 | 43,940114640 | 0,976446992 | indisponível | indisponível | Equilíbrio candidato analítico; εs<εyd, modelo inválido. |

Geometria e concreto: A–D usam b=25, h=76, c=2,5 cm, estribo 8 mm, fck=40 MPa. E−/E0/E+ usam b=20, h=50, c=3 cm, estribo 5 mm, fck=30 MPa. F usa b=30, h=50, c=3 cm, estribo 5 mm, fck=20 MPa.

Exemplo de reprodução do caso A: As=8π cm²; T=As×(500/1,15)×0,1 kN; x=T/[0,68×25×(40/1,4)×0,1]; MRd=T(71,7−0,4x). Dividindo por 1.000, obtém-se Mdresist≈68,51520127777044 tf.m; dividindo depois por 1,4, Mkresist≈48,93942948412174 tf.m. Os valores salvos no arquivo coincidem no arredondamento, mas essa coincidência não foi usada para definir a referência.

Para B–D, áreas e d são calculados independentemente a partir das quantidades/bitolas e dos vãos livres descritos. O centroide usa a soma de primeiros momentos. Todos têm x/d abaixo de 0,45, de modo que o truncamento da planilha é inativo. Os três casos E definem d a partir de x analítico e da razão alvo; E+ usa a equação equilibrada nova, não a expressão truncada da planilha. F verifica indisponibilidade de capacidade: não congela como MRd um valor derivado de uma hipótese falsa.

### Outros testes

- G — geometria inválida: lista vazia, camada fora das margens, camadas coincidentes, envelopes sobrepostos, largura insuficiente, quantidade/diâmetro/posição inválidos. Esperado: `ValueError` ou `TypeError`, sem tolerância.
- Escoamento por camada: C30, b=30, h=60, duas barras de 20 mm a d=55 e duas de 12,5 mm a d=12 cm. x/d_eq fica abaixo do limite, mas a segunda camada não escoa: hipótese inválida e MRd indisponível.
- Camada na zona comprimida e candidato x além da altura: MRd e status de ductilidade indisponíveis, com diagnóstico.
- Aço com Es distinto: testa que o Es configurado participa da validação de escoamento.
- C60: confirma reutilização dos parâmetros variáveis do concreto e limite 0,35; referência analítica própria, sem equivalência à planilha de coeficientes constantes.
- Mínimo: abaixo e acima do mínimo, casos sem tabela (55 e 30,5 MPa), sem alterar As ou MRd.
- Coeficientes customizados, transformação característica opcional, ordem das camadas, exportações públicas e serialização JSON.
- Comparação poligonal: resultados conhecidos tratados como regressão diagnóstica, não como golden normativo.

### Verificação executada

**65 testes passaram**, incluindo 17 testes existentes e 48 novos casos coletados, em Python 3.10.11. Comando: `python -m pytest -q -p no:cacheprovider`, com `PYTHONPATH` apontando para dependências de teste em pasta temporária. Como pytest não estava instalado, foi disponibilizado somente nessa pasta; nenhum requisito externo foi acrescentado a `pyproject.toml` ou ao pacote.

Também foi feita comparação por AST do dimensionador contra HEAD e comparação dos arquivos dos motores/materiais/seções/normas/viga com HEAD. O dimensionador e esses arquivos permanecem sem alteração funcional. `git diff --check` não apontou erros de whitespace. As referências são determinísticas e dispensam o arquivo XLSM durante os testes.

## Limitações conhecidas e próximos passos

- Modelo simplificado de bloco retangular, com concreto sem tração, aderência perfeita, seções planas e aço idealizado escoado. Mesmo no ramo limitado por εsu, o bloco usa os coeficientes simplificados dos objetos existentes; não integra o diagrama real do concreto para cada deformação.
- Não calcula capacidade elástica de aço não escoado nem armadura comprimida. Nesses casos é necessário outro modelo futuro explicitamente validado; não há fallback automático para o poligonal.
- Uma bitola por camada e aço de propriedades comuns a todas as camadas. Não representa misturas de categorias de aço dentro da mesma seção.
- Posições explícitas em cm; nenhum gerador automático de camadas ou interpretação de desenho. As validações de largura/envelopes não substituem espaçamento mínimo, confinamento, ancoragem ou verificação construtiva.
- Ductilidade multicamadas usa d_eq como critério declarado; sua aplicação ao procedimento normativo específico do escritório precisa ser revisada antes de aprovação normativa de detalhamentos.
- Verificação de mínimo opcional usa a infraestrutura existente, com cobertura discreta de fck e escopo de vigas; não é auditoria completa da regra de mínimo. Taxa máxima e demais exigências não são certificadas.
- Não há interação N–M, seção T, lajes, escalonamento, cisalhamento, torção, ancoragem ou interpolação de diagramas.
- Resultados não certificam a norma vigente nem supõem equivalência dos três motores. Parâmetros legados de materiais devem ser avaliados em uma etapa normativa própria, sem alteração silenciosa.

Antes da integração com o engineering-assistant: confirmar a convenção de face comprimida e unidades no extrator de detalhamento; esclarecer o truncamento de x do procedimento da planilha; ampliar referências independentes do escritório; definir quais diagnósticos impedem a comparação automática; manter a distinção entre capacidade, validade, ductilidade e mínimo no contrato de transporte; revisar coeficientes para a edição normativa adotada. Nenhuma dessas integrações foi implementada nesta etapa.
