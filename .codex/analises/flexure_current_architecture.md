# Arquitetura atual da flexão no Concretopy

Data da análise: 04/10/2026. Escopo: código e testes presentes neste checkout, com inspeção complementar da planilha `Verificação - VIGAS E LAJES - R07 - EM REVISÃO.xlsm`, no caminho informado pelo usuário.

Este relatório é a única entrega implementada nesta etapa. Não foram criadas APIs, copiadas fórmulas para implementação, alterados cálculos ou refatorados módulos. As referências `arquivo:linha` apontam para o código observado. As hipóteses normativas abaixo descrevem a implementação; não constituem auditoria de conformidade com uma edição da NBR 6118.

## 1. Conclusão da análise

**Fato encontrado:** o pacote já é uma biblioteca Python utilizável sem interface gráfica. O dimensionamento retangular segue o fluxo momento característico → áreas necessárias. Entretanto, existe também o fluxo armadura posicionada → momentos resistentes, implementado por `CalculadoraFlexoCompressao.momentos_resistentes` e acessível pela classe pública `PilarPoligonal`. Esse segundo fluxo aceita esforço normal de cálculo igual a zero e é o principal candidato a reutilização para verificar detalhamentos.

**Limite encontrado:** os dois fluxos usam hipóteses diferentes. O motor poligonal não reproduz automaticamente os parâmetros variáveis do concreto nem o limite de ductilidade do dimensionador de vigas. Também não equivale à verificação retangular da planilha. A existência de um cálculo de resistência não basta para declarar uma verificação normativa de viga aprovada.

**Sugestão de arquitetura:** começar por caracterizar e validar o motor resistente existente com armaduras efetivamente posicionadas. Depois, avaliar um adaptador pequeno para o engineering-assistant, responsável por entradas, unidades, orientação, diagnóstico e serialização, mantendo o cálculo no Concretopy. Não inverter numericamente o dimensionador nem portar as fórmulas da planilha antes dessa avaliação.

## 2. Mapa dos arquivos — fatos encontrados

| Arquivo e referência | Responsabilidade e relação com a flexão |
| --- | --- |
| `concretopy/api.py:1`, `concretopy/__init__.py:1` | Interface pública declarada estável e reexportações. Incluem materiais, seções, barras, vigas, pilares e resultados. |
| `concretopy/elementos/viga.py:15` | `VigaRetangular`: agrega geometria e materiais; constrói a seção; delega dimensionamento de flexão e cortante. |
| `concretopy/verificacoes/flexao.py:10` | `dimensionar_flexao_viga_retangular`: único núcleo de dimensionamento de flexão retangular encontrado. |
| `concretopy/materiais.py:7`, `:83` | `Concreto` e `Aco`: resistências, deformações, coeficientes e módulo do aço. |
| `concretopy/secoes.py:7`, `:38` | `SecaoRetangular`: geometria e alturas úteis; `SecaoPoligonalArmada`: contorno e barras posicionadas. |
| `concretopy/armaduras.py:7`, `:15`, `:25` | `Barra`, `BarraPosicionada`, `Armadura`: diâmetros, posições e áreas fornecidas. |
| `concretopy/normas/nbr6118.py:10` | Tabela de taxa mínima de vigas; funções de espaçamento longitudinal e de estribos. |
| `concretopy/resultados.py:8`, `:24`, `:31`, `:38` | Dataclasses de resultados de dimensionamento, opções de bitola, layout e resistência poligonal. |
| `concretopy/detalhamento/arranjos.py:13` | Áreas, quantidades, capacidade de uma camada, distribuição e escolha de armadura nova. |
| `concretopy/detalhamento/layouts.py:7` | `coordenadas_barras_retangulares`: converte camadas superiores/inferiores em barras posicionadas. |
| `concretopy/elementos/pilar.py:10` | `PilarPoligonal.momentos_resistentes`: fachada pública do cálculo resistente. |
| `concretopy/verificacoes/flexo_compressao.py:177` | `CalculadoraFlexoCompressao`: equilíbrio axial, linha neutra e momentos da seção já armada. |
| `concretopy/geometria/poligonos.py:4`, `concretopy/geometria/transformacoes.py:5` | Área, primeiros momentos, translação e rotação usados pelo motor resistente. |
| `concretopy/aplicacoes/calculadora_furos.py:379` | Consumidor existente: usa layouts e o motor resistente nos banzos, nas orientações 0° e 180°. É precedente de reutilização, não fachada adequada para verificar uma viga íntegra. |
| `concretopy/verificacoes/cortante.py:11` | Cálculo adjacente, chamado pela viga e pela aplicação de furos; não é necessário para dimensionar a flexão isolada. |
| `concretopy/unidades.py:21`, `concretopy/exceptions.py:12` | Conversões e erros de domínio, incluindo taxa excedida e não convergência. |
| `pyproject.toml`, `README.md`, `docs/api_publica.md` | Empacotamento, convenções e contrato público. Python ≥ 3.10, sem dependências de execução declaradas. |
| `docs/hipoteses_e_limites.md`, `docs/validacao_flexocompressao.md` | Documentam que a flexo-compressão ainda necessita de validação com exemplos e planilhas do escritório. |
| `tests/` | Testes de viga, flexo-compressão, unidades, API, arranjos e furos. |

## 3. Fluxo atual de dimensionamento — fatos encontrados

```text
concretopy / concretopy.api
  → Concreto + Aco + VigaRetangular
  → dimensionar_flexao(mk, diametro_barra_mm)
  → propriedade secao → SecaoRetangular
  → dimensionar_flexao_viga_retangular(...)
  → ResultadoFlexao

Entrada opcional em tf.m
  → dimensionar_flexao_tfm
  → tfm_para_kncm
  → mesmo fluxo

Etapa opcional de detalhamento, chamada separadamente
  → definir_arranjo_arm_long_vigas / escolher_arranjo
  → ArranjoArmaduraFlexaoViga
  → to_list() → camadas (quantidade, bitola)
```

Dentro de `flexao.py:10`, a sequência é:

1. Obter `d` e `d_linha` da seção a partir de cobrimento, estribo e uma bitola longitudinal.
2. Obter resistências de cálculo dos materiais e converter MPa para kN/cm². Majorar `mk` para `md`.
3. Determinar fronteiras dos domínios 2/3 e 3/4, limite de ductilidade e capacidade máxima com armadura simples.
4. Se a solicitação supera essa capacidade, manter a profundidade comprimida limite e calcular armaduras de compressão e tração. Caso contrário, calcular a profundidade comprimida e a armadura simples.
5. Aplicar área mínima à armadura de tração. Verificar o limite de área total de aço, lançando `TaxaArmaduraExcedida` se ultrapassado.
6. Classificar domínio e retornar áreas, área comprimida e linha neutra.

Não há chamada automática de escolha de bitolas nem iteração para atualizar `d` depois de distribuir barras em várias camadas. `ResultadoFlexao` descreve áreas necessárias, não uma armadura detalhada nem um momento resistente.

## 4. Funções, classes, entradas e saídas — fatos encontrados

| Ponto de entrada existente | Entradas | Saídas / observações |
| --- | --- | --- |
| `Concreto(fck)` | Resistência característica em MPa | Objeto imutável; `fcd(gamma_c=1.4)`, `ecu`, `alfa_c`, `lamb` e demais propriedades. Valida tipo numérico e mínimo de 20 MPa. |
| `Aco(fyk=500, es=210000)` | Resistência e módulo em MPa | `fyd(gamma_s=1.15)`, `ey`, `eyu`; sem validação própria de valores. |
| `SecaoRetangular(bw,h,cobrimento,diametro_estribo_mm=5)` | Dimensões em cm e estribo em mm | `area`, `inercia`, `modulo_elastico`, `d(bitola=12.5)`, `d_linha(bitola=12.5)`. |
| `VigaRetangular(bw,h,cobrimento,concreto,aco,diametro_estribo_mm=5)` | Geometria e materiais | Fachada; `secao` cria um novo objeto. Validação da seção ocorre ao acessar essa propriedade. |
| `VigaRetangular.dimensionar_flexao(mk,diametro_barra_mm=12.5)` | Momento característico em kN.cm | `ResultadoFlexao`. A fachada não expõe os coeficientes de segurança. |
| `dimensionar_flexao_viga_retangular(secao,concreto,aco,mk,gamma_f=1.4,gamma_c=1.4,gamma_s=1.15,diametro_barra_mm=12.5)` | Mesmos dados com coeficientes configuráveis | `ResultadoFlexao`; disponível no submódulo e em `concretopy.verificacoes`, fora da lista estável de `concretopy.api`. |
| `dimensionar_flexao_tfm(mk_tfm,diametro_barra_mm=12.5,aproximado=True)` | Momento característico em tf.m | Mesmo resultado, após conversão. |
| `Barra(diametro_mm)` / `BarraPosicionada(x,y,diametro_mm)` | Diâmetro; na segunda classe, coordenadas em cm | Propriedade `area_cm2`. Ambos são públicos. |
| `Armadura(barra,espacamento,numero,cobrimento)` | Barra, quantidade e metadados | Área total; não contém coordenadas nem separação tração/compressão. Não é exportada na API estável. |
| `definir_arranjo_arm_long_vigas(...)` | Área necessária, largura, cobrimento, bitolas de estribo e longitudinal, agregado, espaço de vibrador | Arranjo com área fornecida, excesso, quantidade e distribuição por camadas. É público. |
| `escolher_arranjo(...)` | Dados anteriores, com catálogo opcional de bitolas | Escolhe arranjo por penalização de quantidade, camadas e excesso. É utilitário de dimensionamento, não leitura de detalhamento existente. |
| `coordenadas_barras_retangulares(secao,camadas_superiores,camadas_inferiores,delta_cm=0.8)` | Camadas como listas de `(numero_barras,bitola_mm)` | `LayoutBarras`, contendo barras posicionadas e camadas originais. Não faz parte da API estável. |
| `PilarPoligonal(contorno,barras,concreto,aco).momentos_resistentes(nd,inclinacao_linha_neutra_graus)` | Contorno e barras, esforço normal de cálculo e orientação | `ResultadoFlexoCompressao`; aceita `nd=0`, inclusive nos testes. |
| `CalculadoraFlexoCompressao.momentos_resistentes(secao,concreto,aco,nd,inclinacao_linha_neutra_graus,tolerancia_relativa_forca=0.01,tolerancia_absoluta_forca=0.001)` | Seção armada e tolerâncias | Mesmo resultado; fachada do pilar não expõe tolerâncias. Classe disponível no submódulo, fora da API estável. |

`ResultadoFlexao` (`resultados.py:8`) contém `as_tracao`, `as_compressao`, `area_concreto_comprimido` (cm²), `linha_neutra` (cm) e `dominio` (inteiro). Não retorna `md`, capacidade limite, alturas úteis, deformações, coeficientes ou avisos. Ao impor a área mínima, o código não recalcula linha neutra e área comprimida para a área mínima fornecida: esses campos continuam associados à solicitação calculada anteriormente.

`ResultadoFlexoCompressao` (`resultados.py:38`) contém `nd_resistente` (kN), `mxd_resistente` e `myd_resistente` (kN.cm), `inclinacao_linha_neutra_graus`, `linha_neutra` (cm), `residual_equilibrio` (kN) e `convergiu`. Não contém domínio, taxa mínima/máxima, razão de ductilidade ou aprovação normativa. Se não converge segundo o critério implementado, a calculadora lança exceção antes de retornar o resultado.

## 5. Fluxo resistente já existente — fatos encontrados

```text
contorno + lista de BarraPosicionada + Concreto + Aco
  → PilarPoligonal.momentos_resistentes(nd, angulo)
  → SecaoPoligonalArmada
  → CalculadoraFlexoCompressao.momentos_resistentes
  → centralização e rotação
  → compatibilidade de deformações + equilíbrio axial
  → busca da linha neutra
  → integração de forças e momentos
  → ResultadoFlexoCompressao
```

O motor calcula centroide, centraliza contorno e barras, gira a seção e mede a distância de cada barra à borda comprimida. Obtém as áreas de aço por diâmetro. Usa as funções existentes `deformacao_aco`, `_tensao_aco_kN_cm2`, `secao_comprimida` e `funcao_linha_neutra` para montar o equilíbrio.

A busca avalia uma grade de 4.001 posições até `max(5h,5d,100 cm)`, procura intervalos com mudança de sinal e aplica bisseção com até 200 iterações. Pode aceitar um ponto aproximado dentro da tolerância, mesmo sem raiz exata. A tolerância efetiva é o maior valor entre a tolerância absoluta e 1% da capacidade axial de referência da seção; não é 1% de `nd`. Portanto, `nd=0` não implica equilíbrio axial rigorosamente nulo. O residual retornado é a solicitação axial menos a resistência axial calculada.

Depois do equilíbrio, o motor volta o bloco comprimido à orientação original e soma as contribuições do concreto e das barras em relação ao centroide.

**Convenções observadas:** compressão contribui positivamente para `nd_resistente`; tração, negativamente. A rotação usa `xr=x cos(alfa)+y sin(alfa)` e `yr=-x sin(alfa)+y cos(alfa)`. A componente chamada `mxd_resistente` usa braços na coordenada x; `myd_resistente`, braços em y. É necessário preservar essa convenção do código, sem inferir o eixo apenas pelo nome. Para o retângulo vertical dos testes, 0° produz `myd_resistente` positivo e 180° negativo. A calculadora de furos já usa essas duas orientações e essa componente para a flexão dos banzos (`calculadora_furos.py:399`). Um único ângulo não representa automaticamente a direção de uma solicitação biaxial arbitrária.

## 6. Unidades — fatos encontrados

| Grandeza | Convenção |
| --- | --- |
| Geometria, cobrimento, coordenadas, profundidades | cm |
| Bitolas e dimensão do agregado | mm |
| Áreas de concreto/aço | cm² |
| Inércia / módulo geométrico da seção | cm⁴ / cm³ |
| Resistências e módulo dos materiais | MPa na entrada |
| Tensões no equilíbrio | kN/cm², convertidas de MPa pelo fator 0,1 |
| Forças e residual axial | kN |
| Momentos | kN.cm |
| Ângulo | graus |
| Deformações em `materiais.py` e no dimensionador | Adimensionais, por exemplo `ecu=0.0035` |
| Deformações nas funções do motor poligonal | Por mil, por exemplo 3,5 e 10 |
| Taxa mínima tabelada | Percentual; o dimensionador divide por 100 |

As funções de `unidades.py` já fornecem conversão tf ↔ kN e tf.m ↔ kN.cm. O padrão é aproximado: 1 tf = 10 kN e 1 tf.m = 1.000 kN.cm. O modo `aproximado=False` usa 9,80665 kN/tf. Trocar esse padrão alteraria os resultados legados. Não há conversão pronta de kN.m nessa interface.

`mk` do dimensionador é característico e recebe `gamma_f`. `nd` do motor resistente já é de cálculo e não recebe majoração interna. Os momentos resistentes desse motor são de cálculo porque usam resistências minoradas. Comparar valores característicos e de cálculo sem conversão explícita seria incompatível com esses contratos.

## 7. Hipóteses normativas codificadas — fatos encontrados

### Dimensionamento retangular

- Flexão de seção retangular, sem esforço normal nessa função; concreto tracionado não participa do equilíbrio.
- Bloco retangular comprimido com `Concreto.alfa_c`, `Concreto.lamb` e `Concreto.ecu`, variáveis com `fck` acima de 50 MPa. Até 50 MPa: 0,85, 0,8 e 3,5‰.
- Limite de ductilidade de 0,45d até 50 MPa e 0,35d acima, combinado com a fronteira 3/4. Excesso de solicitação é atendido por armadura dupla.
- Aço tracionado considerado à resistência de cálculo. Aço comprimido usa tensão elástica ou de escoamento conforme a deformação calculada.
- Área mínima de vigas pela tabela em `nbr6118.py`; área máxima total igual a 4% da área bruta.
- Uma mesma bitola estabelece a posição idealizada das armaduras tracionada e comprimida. Não representa diretamente centroides de múltiplas camadas.
- Tabela mínima discreta com chaves 20–50 a cada 5 MPa e 60–90 a cada 5 MPa; 55 não está cadastrado. A consulta usa `int(fck)` sem interpolação, podendo truncar uma entrada não inteira.
- Os arquivos examinados não fixam edição ou cláusulas da NBR para cada regra. O nome do módulo não prova conformidade com a norma vigente.

### Resistência poligonal

- Bloco com profundidade 0,8x e tensão de concreto 0,8fcd, ambos fixos. Não consulta `Concreto.lamb` nem `Concreto.alfa_c`.
- Deformações do concreto e do aço determinadas por ramos com constantes 3,5‰, 10‰ e outras constantes do domínio comprimido. Não consulta `Concreto.ecu` nem `Aco.eyu`.
- Lei bilinear simétrica do aço, sem encruamento, com módulo fixo equivalente a 210.000 MPa. `Aco.es` configurado não altera essa lei.
- Coeficientes do concreto e do aço fixados em 1,4 e 1,15. Não há `gamma_f` interno.
- Não aplica o limite de ductilidade do dimensionador nem verifica taxas de aço, espaçamentos ou ancoragem.
- O bloco de concreto é calculado sobre o polígono cheio, sem descontar a área ocupada pelas barras antes de somar as forças de aço.

Essas diferenças são evidências de modelos distintos; não foram corrigidas nesta etapa. O suporte de `Concreto` a parâmetros de alta resistência não torna o motor poligonal automaticamente equivalente ao dimensionador para esses materiais.

## 8. Planilha fornecida — fatos encontrados e limites da inspeção

O arquivo foi aberto somente como contêiner ZIP/XML, com bibliotecas padrão do Python. Não foram executadas macros, scripts Python embutidos ou instruções encontradas no documento. Há abas `Importações`, `VIGAS`, `LAJES` e `AUXILIAR` (oculta), projeto VBA e scripts em `xl/python.xml`.

| Referência na planilha | Papel observado |
| --- | --- |
| `VIGAS!B3:B6`, `B17`, `B25` | Altura, largura, estribo, cobrimento, fck e fyk. |
| `VIGAS!I5:J7` | Quantidades e bitolas de até três camadas. |
| `VIGAS!K5:M7`, `B7:B8` | Alturas úteis, áreas por camada e ponderação da altura útil pela área de aço. |
| `VIGAS!I12:I17`, `L12:L17`, `O12:O17` | Resistência considerando sucessivamente uma, duas e três camadas. Linha 14 calcula linha neutra; linha 15, x/d; linha 16 tem rótulo `Mdresist`; linha 17, `Mkresist`. |
| `LAJES!C19:D20`, `E19:E20` | Bitolas e espaçamentos, convertidos em áreas por faixa de 100 cm. |
| `LAJES!J4:J9`, `M4:M9`, `P4:P9` | Resistência de grupos e do conjunto; `Mdresist` e `Mkresist` nas linhas 8 e 9. |
| `VIGAS!X6`, `LAJES!J20`, `xl/python.xml` | Dimensionamento em Python no Excel, com classes legadas e acesso a células via `xl(...)`. |

A resistência em `VIGAS` usa área de aço e altura útil equivalente; a linha neutra é obtida com coeficiente 0,68. O braço da linha 16 limita a contribuição de x a 0,45d por `MIN`, mas essa expressão não resolve, por si só, um novo equilíbrio quando o limite é excedido. Na região inspecionada, não há participação explícita de uma armadura comprimida nesse equilíbrio. `LAJES!P6:P8` combina forças de grupos de aço e não usa o mesmo truncamento de x presente em `VIGAS!I16`.

As resistências da planilha são convertidas para tf.m usando a aproximação 10 kN/tf; `Mkresist` divide `Mdresist` por 1,4. Essa unidade é inferida da cadeia de fórmulas e conversões, enquanto os rótulos identificam explicitamente o nível Md/Mk. Exemplos de valores **salvos, sem recálculo**: `VIGAS!I16=68,515201277770444` e `I17=48,939429484121746`; `LAJES!P8=6,0512466825380828` e `P9=4,3223190589557738`.

Há valores em cache `#VALUE!` nas chamadas Python inspecionadas, inclusive em `Importações!A2` e `VIGAS!X6`. Isso descreve o arquivo salvo; não comprova como ele se comporta no Excel com o ambiente adequado. A inspeção não validou macros, gráficos, recálculo ou equivalência numérica com o pacote. Os scripts legados não foram incorporados ao código.

**Inferência arquitetural:** a planilha é uma boa fonte de casos e contratos de uso, mas não deve ser tratada como motor idêntico ao poligonal. Área agregada e altura equivalente não contêm toda a informação necessária para representar deformações distintas de barras em várias camadas.

## 9. Dependências da interface e uso headless — fatos encontrados

Não foram encontradas dependências de GUI, Excel/COM, CAD, TQS ou serviço de IA no núcleo examinado. Os módulos usam bibliotecas padrão (`dataclasses`, `math`, `typing`) e imports internos. `pyproject.toml` declara `dependencies=[]`; setuptools e wheel são dependências de construção. `pytest` é necessário para executar a suíte, mas não está declarado nesse arquivo como dependência de desenvolvimento.

A importação de `concretopy` passa por `api.py` e também carrega aplicações de furos e detalhamento, mesmo para um cliente interessado apenas em flexão. Há acoplamento por importação, mas nenhuma exigência de interação gráfica encontrada. `TYPE_CHECKING` em `nbr6118.py` evita importar a viga em execução apenas para anotações.

A calculadora de furos produz resultado e memorial textual; `memorial_de_calculo()` imprime texto, mas essa apresentação não faz parte do fluxo isolado de flexão. A interface da planilha, seus scripts `xl(...)` e dependências do Python no Excel estão no arquivo de referência, não no núcleo Concretopy.

Limitações programáticas relevantes:

1. **Contrato invertido ausente na viga:** não existe método da viga que receba armadura detalhada e devolva resistência. Há um cálculo poligonal público sob a classe de pilar.
2. **Geometria insuficientemente validada:** barras não validam diâmetro ou posição; a seção poligonal valida apenas pelo menos três pontos. Barras vazias falham em `max(di)`; não há verificação de barras fora do contorno, duplicação, sobreposição ou contorno autointersectante. A área geométrica usa módulo, mas os primeiros momentos preservam sinal: o sentido dos vértices exige caracterização. Os testes usam contornos anti-horários.
3. **Entradas sem validação completa:** não há controle sistemático de NaN/infinito, coeficientes positivos ou `d>0`. Momento negativo não é normalizado pelo dimensionador e não troca faces de tração/compressão. Não constitui suporte explícito a detalhamento de momento negativo.
4. **Posicionamento idealizado:** `coordenadas_barras_retangulares` usa `delta_cm=0.8` e não lê a bitola do estribo. O passo vertical e o x inicial usam a bitola da primeira camada; uma barra única fica em x inicial, não no centro da largura. Não recebe espaçamento vertical real. Portanto, só deve representar um detalhamento existente quando essas hipóteses coincidirem com ele.
5. **Resultados sem contrato de transporte:** retornos são dataclasses, não mensagens JSON com unidades, origem dos dados e hipóteses. Não há ferramenta do engineering-assistant, REST ou MCP encontrada.
6. **Diagnóstico parcial:** há exceções de domínio, `ValueError` e possíveis erros aritméticos. `convergiu` confirma apenas o critério axial do resolvedor; não a conformidade do detalhamento. Não há relatório de cada verificação normativa no retorno resistente.
7. **Configuração desigual:** coeficientes configuráveis na função retangular, fixos na fachada da viga e no motor poligonal; tolerâncias configuráveis no motor, não na fachada do pilar.
8. **Custo e precisão:** grade densa por ângulo, sem cache ou operação em lote; residual admitido pode ser relevante em flexão pura. O algoritmo não busca sozinho a orientação de equilíbrio de uma demanda biaxial nem o maior momento em todas as direções.
9. **Lajes:** não há classe ou verificador específico de lajes encontrado. Uma faixa retangular de 100 cm é uma possível representação geométrica futura, mas não implementa automaticamente verificações específicas de lajes.

## 10. Testes existentes e verificação desta análise

| Arquivo | Cobertura observada | Limite |
| --- | --- | --- |
| `tests/test_viga.py` | Um caso de flexão/cortante; área positiva e domínio em 2, 3 ou 4. | Não compara numericamente o dimensionamento com referência; não cobre armadura dupla, limites ou inversão. |
| `tests/test_flexocompressao.py` | Cinco referências numéricas para nd/ângulo; simetria 0°/180°; componente próxima de zero a 90°; caso 60°; convergência/residual. | Retângulo com quatro barras simétricas e concreto C30; não é validação normativa independente. Referências de momentos e x usam tolerância absoluta de 1e-9; residual aceita até 20 kN. |
| `tests/test_unidades.py` | Conversões aproximadas tf/kN e tf.m/kN.cm. | Não cobre modo exato nem entradas incompatíveis. |
| `tests/test_api_publica.py` | Nomes essenciais exportados e imports básicos. | Não congela todas as assinaturas nem um contrato de verificação resistente de vigas. |
| `tests/test_arranjos.py` | Área, quantidade, uma camada, escolha compatível e falha em seção inviável. | Não verifica resistência nem posicionamento real das barras. |
| `tests/test_furos.py` | Caso básico, conversão de unidades, geometria inválida e zona comprimida. | Cobertura de aplicação adjacente; não demonstra equivalência dos motores de flexão. |
| `tests/conftest.py` | Adiciona a raiz ao caminho de imports. | Apoio ao ambiente de testes. |

Não há arquivo dedicado `test_flexao.py` neste checkout. Não foram encontrados testes de equivalência com a planilha, resistência de vigas assimétricas/multicamadas, taxas mínimas/máximas do fluxo resistente, alta resistência, geometria de layouts ou contrato JSON do assistente.

**Execução realizada:** `python -m pytest -q -p no:cacheprovider` não pôde iniciar porque o Python 3.10.11 disponível não tem `pytest` instalado. Não foi instalada dependência nem alterado o ambiente para esta análise. Como verificação complementar, foram carregados via `runpy.run_path` os arquivos de viga, unidades, API pública e flexo-compressão e executadas diretamente suas oito funções `test_*`; todas passaram, incluindo os cinco casos de regressão dentro de uma dessas funções. Isso não equivale à execução da suíte completa ou de seus mecanismos de fixtures. Arranjos e furos não foram executados dessa maneira porque dependem de `pytest`.

## 11. Proposta mínima futura — sugestões, não implementação

### 11.1 Primeiro: confirmar o contrato de resistência

Usar os objetos existentes (`Concreto`, `Aco`, `BarraPosicionada`, `SecaoPoligonalArmada`) para representar uma seção e sua armadura real. Avaliar o motor existente com `nd=0` e orientações 0°/180°, preservando componentes, sinais, coeficientes e tolerâncias. `PilarPoligonal` permite experimentar isso hoje pela API pública, embora seu nome não comunique bem o caso de viga.

Confrontar casos rastreáveis da planilha: uma camada dentro do limite, várias camadas, seção assimétrica, armadura comprimida, momento positivo/negativo e proximidade/excesso do limite de ductilidade. Comparar separadamente o nível de cálculo, as unidades, os parâmetros do bloco, as posições de barras e o residual. Os valores salvos da planilha devem ser confirmados por recálculo antes de serem usados como referência aceita.

Se a necessidade for reproduzir exatamente o modelo simplificado da planilha, definir esse requisito antes de escolher o motor. Se a necessidade for resistência da seção detalhada por compatibilidade, avaliar o motor poligonal existente. Divergências devem ser explicadas e registradas; não alterar constantes para fazer coincidir valores nesta fase.

### 11.2 Depois: um adaptador pequeno

No engineering-assistant, prever apenas tradução de dados externos para objetos Concretopy, conversão por `unidades.py`, chamada ao cálculo existente e transformação da dataclass em resposta estruturada. Leitura de CAD/Excel, extração de detalhamento, interação com usuário e transporte REST/MCP pertencem à integração. As fórmulas e verificações de engenharia devem continuar no pacote.

O contrato futuro deverá explicitar geometria, coordenadas e faces, materiais, esforço normal de cálculo, sentido de flexão, unidades e origem do detalhamento. A saída deverá preservar os campos resistentes e o residual, identificando o motor e as hipóteses usados. Não converter uma exceção ou não convergência em resistência zero ou aprovação. Comparação com solicitação deve ser feita no mesmo nível de cálculo.

Preferir coordenadas reais quando disponíveis. Só reutilizar o gerador de layouts quando suas hipóteses de espaçamento e posição estiverem explicitamente aceitas. Não chamar seleção de armaduras para substituir um detalhamento já pronto.

### 11.3 Eventual mudança mínima no pacote

Após validação, considerar uma fachada com semântica de seção armada/viga que **delegue** ao motor resistente existente, sem duplicar `funcao_linha_neutra`, os diagramas, a geometria ou o resolvedor. A escolha de nome, assinatura e exportação fica para a próxima etapa. O núcleo já é headless; não há razão encontrada para refatorá-lo para retirar uma GUI.

Separar capacidade calculada de verificações de detalhamento e ductilidade. Reutilizar a tabela e os auxiliares normativos já existentes onde forem aplicáveis. Qualquer adequação de parâmetros do motor à hipótese de vigas deve ser uma alteração técnica posterior, com referências e regressões próprias, porque pode mudar números.

Não obter a resistência por busca em `dimensionar_flexao` até atingir a área fornecida: a imposição de mínimo cria um trecho sem inversão única, a armadura dupla envolve duas áreas, e a altura útil atual não descreve multicamadas. Essa estratégia não aproveita corretamente a informação do detalhamento.

Há cálculos de área de barra repetidos no próprio código (`Barra`, `BarraPosicionada`, `area_barra_cm2` e motor poligonal). Este relatório registra a duplicação existente, mas não propõe reproduzi-la no adaptador nem a consolida nesta etapa. Reutilizar propriedades e funções existentes para novos consumidores.

### 11.4 Critério sugerido para avançar

Antes de expor uma ferramenta de verificação ao assistente: definir o modelo de resistência pretendido, confirmar sinais/unidades, caracterizar o residual em `nd=0`, validar casos do escritório e distinguir mensagens de capacidade, convergência e conformidade normativa. Criar testes de referência para esse contrato numa etapa autorizada posterior, preservando a regressão do dimensionador atual. Não são necessários agora servidor, nova hierarquia de classes ou refatoração ampla.
