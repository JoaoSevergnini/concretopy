# Auditoria de al, lb e ancoragem longitudinal de vigas

Data: 04/10/2026. Entrega: documentação, sem alterações no Concretopy ou na planilha.

## Fonte, método e alcance

Arquivo inspecionado: `C:\Users\João Severgnini\Desktop\corrigir em casa\corrigir em casa\Verificação - VIGAS E LAJES - R07 - EM REVISÃO.xlsm`, aba **VIGAS**. SHA-256: `f97b7acb3ce1cc34008cd5d1e1abab0ee949368018060102bc4a66c1bfdc040f`.

O Excel não foi aberto nem recalculado pelo aplicativo: foram extraídos valores, fórmulas, rótulos, formatação condicional e dependências do XML do XLSM, em leitura somente. As equações foram reproduzidas matematicamente com Python padrão, sem executar macros ou scripts embutidos. Portanto, a auditoria cobre a lógica das células, não efeitos eventuais de VBA, eventos de edição ou renderização no Excel. Não foram encontrados comentários no arquivo nem referências textuais a al/lb/fbd/ancoragem nos scripts de `xl/python.xml` inspecionados; isso não comprova ausência de lógica no projeto VBA, que não foi analisado.

**Atenção à versão dos dados:** o arquivo atualmente salvo apresenta h=72 cm, b=19 cm e duas camadas com bitola 12,5 mm. Esses dados diferem daqueles inspecionados nos relatórios anteriores, embora o nome do arquivo permaneça igual. Os valores deste relatório se referem à versão identificada pelo hash acima.

A análise distingue: **fatos das células/código**, **interpretação física** e **questões pendentes**. Não é certificação normativa. O [catálogo oficial da ABNT](https://abntcatalogo.com.br/) foi consultado, mas o conteúdo das cláusulas de ancoragem não foi obtido nesta auditoria; não se afirma que as constantes locais atendem à edição normativa aplicável.

## Conclusões principais

- Existem três conjuntos relacionados: quadro geral de comprimentos por grupos de camadas, cálculo de armadura necessária no apoio de extremidade e cálculo de complemento por grampos.
- `al` tem interpretação de deslocamento/decalagem longitudinal do diagrama de tração associado ao cortante; não é o comprimento de aderência `lb`. As células somam os dois, mas não definem graficamente a origem da medida.
- O quadro geral calcula lb básico com aço em fyd e apresenta boa e má aderência. Sua opção “com dobra” usa redução fixa 0,7, sem validar a dobra ou sua geometria.
- O apoio de extremidade usa outro fluxo: boa aderência e redução 0,7 já embutidas, multiplicadas pela razão As necessária/As fornecida. Não há ligação automática entre esses dois conjuntos para escolher um comprimento final.
- Há uma área do vão escrita como constante (`C39=7.18/3`), uma resistência do aço escrita como constante (`C36=B36/4.35`) e nenhuma escolha automática documentada de regime de aderência.
- No estado atual, o bloco de grampos produz área adicional e quantidades negativas. Não há tratamento expresso de complemento desnecessário.
- O Concretopy contém materiais, áreas, posições e cálculo de cortante reutilizáveis, mas não implementa al, fbd, lb, comprimento necessário/disponível ou verificação física de ancoragem longitudinal.

## 1. Entradas e cadeia de dependências

Todas as referências desta seção pertencem à aba VIGAS.

| Células | Dados / unidades | Valor salvo atual / natureza |
| --- | --- | --- |
| `B3`, `B4` | h e b, cm | 72 e 19; entradas |
| `B5`, `B6` | Bitola de estribo, mm; cobrimento, cm | 5 e 2,5; entradas |
| `I5:I7`, `J5:J7` | Quantidade e bitola longitudinal por camada, mm | (3;12,5), (1;12,5), (0;0); entradas |
| `B17`, `B25` | fck e fyk, MPa | 40 e 500; entradas |
| `B31` | Vk característico, tf | 5,64; entrada |
| `B32`, `B33` | Mk característico, tf.m; esforço normal rotulado N, tf | 0 e 0; entradas. B33 recebe majoração no bloco de tração, mas seu rótulo não explicita nível característico ou convenção de sinal. |
| `B46`, `B47` | Quantidade e bitola das barras no apoio, mm | 4 e 16; entradas independentes de I5:J7 |
| `C39` | Um terço de área do vão, cm² | Fórmula `7.18/3`: o 7,18 é literal, sem referência a uma célula de área |
| `B54` | Comprimento do apoio, cm | 19; entrada |
| `A58:A62` | Catálogo de bitolas de grampos, mm | 5; 6,3; 8; 10; 12,5 |

Coeficientes embutidos: gamma_f=1,4; gamma_c=1,4; gamma_s=1,15; fator de aderência 2,25; fator de má aderência 0,7; fator de boa aderência 1; fator de redução de lb da opção “com dobra” 0,7. Os dois usos de 0,7 têm papéis distintos.

Fluxo observado:

```text
geometria + quantidades/bitolas → d_i, As_i → d global e d dos grupos
fck → fctm → fctk,inf → fctd → Vc0 e fbd
Vk → Vsd → al base → al de cada grupo
bitola da camada + fyd + fbd → lb → quadros al+lb / al+0,7lb / al+10φ
Mk + N + Vk/al + área do vão literal → As necessária no apoio
barras do apoio → As fornecida → comprimento necessário
comprimento disponível no apoio → As corrigida → déficit → grampos
```

## 2. Geometria, materiais e unidades intermediárias

| Célula / região | Fórmula literal do Excel | Equação e significado |
| --- | --- | --- |
| `K5` | `B3-B5/10-B6-J5/20` | d₁=h−φt/10−c−φ₁/20, cm, distância da face comprimida ao centro da primeira camada |
| `K6` | `IF(J6>=25,K5-J6/10-J5/20-J6/20,K5-2-J5/20-J6/20)` | d₂=d₁−vão livre−raios. Vão livre depende da bitola atual: φ₂/10 cm se φ₂≥25 mm; 2 cm nos demais casos |
| `K7` | `IF(J7>=25,K6-J7/10-J6/20-J7/20,K6-2-J6/20-J7/20)` | Mesma regra para a terceira camada |
| `L5` (análogas L6/L7) | `(J5/10)^2*PI()/4*I5` | Asᵢ=nᵢπ(φᵢ/10)²/4, cm² |
| `M5` (análogas M6/M7) | `K5*L5` | Primeiro momento de área de aço, cm³ |
| `B7` | `SUM(M5:M7)/SUM(L5:L7)` | d global ponderado pela área de aço, cm |
| `I13` | `K5` | d do grupo de uma camada, cm |
| `L13` | `SUM(M5:M6)/SUM(L5:L6)` | d do grupo de duas camadas, cm |
| `O13` | `SUM(M5:M7)/SUM(L5:L7)` | d do grupo de três camadas, cm |
| `B18` | `B17/1.4` | fcd=fck/gamma_c, MPa |
| `B19` | `0.3*B17^(2/3)` | fctm, MPa. Expressão usada independentemente da classe de concreto nessa célula |
| `B20` | `0.7*B19` | fctk,inf=0,7fctm, MPa |
| `B26` | `B25/1.15` | fyd=fyk/gamma_s, MPa |
| `R7` | `0.6*B20/1.4*B4*B7/100` | Vc0=0,6 fctd b d global, em tf; fctd=B20/1,4 em MPa |
| `R27` | `B20/1.4*2.25*0.7` | fbd de má aderência=2,25×0,7×fctd, MPa |
| `R28` | `B20/1.4*2.25*1` | fbd de boa aderência=2,25×1×fctd, MPa |

Conversões: 1 MPa=0,1 kN/cm²; 1 tf é tratado como 10 kN; portanto 1 MPa=0,01 tf/cm². Em R7, dividir o produto MPa×cm² por 100 transforma-o em tf. As razões fyd/fbd são adimensionais porque ambas as tensões são MPa. Bitolas em mm são divididas por 10 para comprimentos em cm.

**Hipóteses interpretadas, não escolhas verificadas:** o fator 2,25 é compatível com uma classificação de superfície de barras aderentes/nervuradas; o arquivo não contém seleção de superfície nesse bloco. Boa/má aderência são apresentadas simultaneamente: não há classificação automática pela posição de concretagem. Não há fator variável por diâmetro nesse fbd. Não se pode concluir sua aplicabilidade a todas as bitolas e condições apenas pelo nome dos rótulos.

## 3. al: equação, limites e uso

### Fórmulas exatas

`R26 = IF(B31*1.4<=R7,B7,0.5*(B7*B31*1.4)/(B31*1.4-R7))`.

Definindo Vsd=1,4Vk, Vc0=R7 e d=d global:

```text
al_base = d                                     se Vsd ≤ Vc0
al_base = 0,5 d Vsd / (Vsd−Vc0)                  se Vsd > Vc0
```

al_base em cm; forças na mesma unidade tf. A condição protege a divisão por zero na igualdade Vsd=Vc0, mas não há conversão para módulo de Vk nem diagnóstico de entrada negativa ou geometria inválida.

O quadro por grupos aplica:

| Regime | Uma camada | Duas camadas | Três camadas |
| --- | --- | --- | --- |
| Má aderência | `I21=MAX(MIN($R$26,I13),0.5*I$13)` | `L21=MAX(MIN($R$26,L13),0.5*L13)` | `O21=MAX(MIN($R$26,O13),0.5*O13)` |
| Boa aderência | `I29=MAX(MIN($R$26,I13),0.5*I$13)` | `L29=MAX(MIN($R$26,L13),0.5*L$13)` | `O29=MAX(MIN($R$26,O13),0.5*O$13)` |

Fisicamente, al_grupo=min/max de al_base para o intervalo [0,5d_grupo; d_grupo]. A aderência não altera al. **L13 e O13 são centroides cumulativos**, não as alturas individuais K6/K7. Assim, o quadro mistura al do grupo cumulativo com lb da bitola da camada correspondente, descrito na próxima seção.

Interpretação: a expressão de al depende da contribuição do concreto ao cortante e da parcela excedente, com forma compatível com uma idealização de decalagem da resultante de tração. Não há ângulo de estribo, ângulo de biela ou escolha de modelo de treliça nas entradas. Não há cálculo de diagramas ao longo da viga nem posicionamento real de pontos de corte. A origem de medição de al+lb não está documentada por estas células.

Para forças positivas e d_grupo=d_global, a expressão limitada fica em d até Vsd=2Vc0. Entre Vc0 e 2Vc0, a base ultrapassa d e o limite superior a reduz; para Vsd=3Vc0 resulta em 0,75d. Imediatamente acima de Vc0 a base tende a um valor muito grande, embora o quadro limitado permaneça finito. Não usar R26 e I21 como se fossem sempre a mesma grandeza.

## 4. lb e combinações do quadro geral

Equilíbrio físico interpretado para barra reta com tensão uniforme de aderência:

```text
As_barra × fyd = perímetro_barra × lb × fbd
lb = (φ/4) × fyd/fbd
```

φ e lb na mesma unidade de comprimento. A planilha usa φ em mm e divide por 10 ao final para lb em cm.

| Saída | Coluna I (φ=J5, al=I21/I29) | Coluna L (φ=J6, al=L21/L29) | Coluna O (φ=J7, al=O21/O29) |
| --- | --- | --- | --- |
| lb má aderência | `I22=(J5/4)*($B$26/$R$27)/10` | `L22=(J6/4)*($B$26/$R$27)/10` | `O22=(J7/4)*($B$26/$R$27)/10` |
| Redução 0,7 | `I23=I22*0.7` | `L23=L22*0.7` | `O23=O22*0.7` |
| al+lb | `I24=I22+I21` | `L24=L22+L21` | `O24=O21+O22` |
| al+lb com dobra | `I25=I21+I23` | `L25=L21+L23` | `O25=O21+O23` |
| al+10φ | `I26=I21+10*J5/10` | `L26=L21+10*J6/10` | `O26=O21+10*J7/10` |
| lb boa aderência | `I30=(J5/4)*($B$26/$R$28)/10` | `L30=(J6/4)*($B$26/$R$28)/10` | `O30=(J7/4)*($B$26/$R$28)/10` |
| Redução 0,7 | `I31=I30*0.7` | `L31=L30*0.7` | `O31=O30*0.7` |
| al+lb | `I32=I30+I29` | `L32=L30+L29` | `O32=O30+O29` |
| al+lb com dobra | `I33=I29+I31` | `L33=L29+L31` | `O33=O29+O31` |
| al+10φ | `I34=I29+10*J5/10` | `L34=L29+10*J6/10` | `O34=O29+10*J7/10` |

Todas essas saídas são cm. Embora L22/O22 sejam rotuladas `lb nec`, suas expressões são lb básico à tensão fyd: não contêm razão As necessária/fornecida. Não existe MAX entre lb, 0,7lb e 10φ nesse quadro: são alternativas apresentadas, sem regra automática de seleção. Não há verificação de comprimento disponível ou limitação inferior explicitamente aplicada a essas alternativas.

O fator 0,7 da dobra não é dedutível do equilíbrio da barra reta. É uma hipótese de redução adicional, dependente de condições que a planilha não verifica neste bloco. Forma, ângulo, raio de dobramento, prolongamento, confinamento e posição no apoio não são inputs dessa seleção.

**Camada vazia:** J7=0 no arquivo atual faz lb₃=0 e al+lb₃=al do grupo. Não há guarda que oculte essas saídas quando I7=0. Quantidade de barras não participa diretamente do lb básico.

## 5. Área longitudinal necessária no apoio

| Célula | Fórmula literal | Significado e unidade |
| --- | --- | --- |
| `O14` | `(O12*$B$26/10)/(0.68*($B$18/10)*$B$4)` | Linha neutra x da resistência das áreas fornecidas, cm; O12=SUM(L5:L7) |
| `B12` | `B7-O14/2` | Braço Z=d_global−x/2, cm |
| `B35` | `B32*1.4/(B12/100)` | Força de tração por momento: Ft,M=1,4Mk/Z, tf, Z convertido para m |
| `C35` | `B35/(B25/100/1.15)` | As,M=Ft,M/fyd, cm²; fyd convertido para tf/cm² |
| `B36` | `B33*1.4` | Parcela de força axial majorada, tf, tratada como tração pela soma |
| `C36` | `B36/4.35` | Área axial, cm², usando tensão constante 4,35 tf/cm² |
| `B37` | `B31*I21*1.4/B7` | Ft,V=Vsd al_grupo1/d_global, tf |
| `C37` | `B37/(B25/100/1.15)` | As,V=Ft,V/fyd, cm² |
| `C38` | `SUM(C35:C37)` | Área necessária pela soma das três parcelas, cm² |
| `C39` | `7.18/3` | Área mínima por fração de área do vão literal, cm² |

Questões documentadas:

- B12 usa x/2, enquanto a expressão resistente da planilha usa centro do bloco a 0,4x (com truncamento no braço quando excedido 0,45d). São braços diferentes. Não se demonstrou qual justificativa pretende fundamentar B12 para o cálculo do apoio; não foi substituído por outro braço.
- O x de B12 vem da **resistência das barras fornecidas**, não de uma resolução da solicitação Mk do apoio. A cadeia usa dois estados de cálculo distintos.
- C36 fixa 4,35 tf/cm², aproximadamente o fyd de CA50, em vez de referenciar B25/B26. Ao mudar o aço, C35/C37 mudam, mas C36 não acompanha essa mudança.
- C39 não referencia As do vão nem a armadura atual. A origem e a atualização manual de 7,18 cm² são pendentes. O rótulo “1/3 As Vão” não transforma esse literal em entrada rastreável.
- B33 e B32 não usam módulo nem descartam contribuição compressiva. Uma entrada negativa pode reduzir C38; a convenção de sinal e o tratamento físico não são certificados pela soma existente.
- B37 usa al do **grupo de uma camada**, mas d global de todas as camadas. Não é automaticamente uma força por camada.

## 6. Apoio de extremidade e grampos

Defina As_req=max(C38,C39). A planilha não cria célula nomeada para essa área, mas repete a operação.

| Célula | Fórmula literal | Equação / unidade |
| --- | --- | --- |
| `B48` | `(B47/10)^2*PI()/4*B46` | As_fornecida=nπ(φ/10)²/4, cm² |
| `B49` | `(IF(B47<20,2.5*B47,4*B47)+5.5*B47)/10+B6` | Apoio mínimo=c+(k+5,5)φ_cm; k=2,5 para φ<20 mm e 4 para φ≥20 mm; cm |
| `B50` | `(B47/4)*(B26/(B20/1.4*2.25*1))/10*0.7` | lb de boa aderência **já reduzido por 0,7**, cm |
| `B51` | `B50*MAX(C38:C39)/B48` | l_necessário=lb_reduzido As_req/As_fornecida, cm |
| `B55` | `B54-B6-(B47/20)` | l_disponível=l_apoio−c−φ/2, cm |
| `B56` | `B50*MAX(C38:C39)/B55` | As_corrigida=lb_reduzido As_req/l_disponível, cm² |
| `B57` | `B56-B48` | Déficit de área para grampo, cm²; pode ser negativo |
| `B58` | `ROUNDUP($B$57/((A58/10)^2*PI()/4)/2,0)` | Quantidade arredondada de grampos de φ=A58, com divisor 2 |
| `B59:B62` | Mesma expressão de B58 com a respectiva célula A59/A60/A61/A62 | Quantidade para cada bitola; ROUNDUP arredonda para longe de zero, inclusive números negativos |

Interpretação física de B51/B56: para uma hipótese de resistência de aderência linear com área fornecida, aumentar As pode compensar um comprimento disponível menor. B56 é a inversão algébrica de B51 para As_fornecida; não demonstra, isoladamente, que um grampo separado possa ser somado às barras longitudinais para transferir a mesma força. O `/2` é compatível com duas pernas resistentes por grampo, mas sua forma, ligação às barras e caminho de forças não estão demonstrados nas células.

B49 é uma regra geométrica local. O salto em φ=20 mm e os fatores 2,5/4/5,5 são fatos do arquivo; sem desenho ou referência do detalhe, não se determina inequivocamente se cada parcela corresponde a raio, trecho reto, gancho ou outra dimensão. Sua aplicabilidade normativa permanece pendente.

Não há comparação automática entre B54 e B49, B55 e B51, nem diagnóstico de comprimento nulo/negativo em B55. B49 não entra na fórmula de B51. Não há soma de al a B51: o apoio tem um cálculo distinto do quadro geral. B50 fixa boa aderência e redução da dobra, independentemente das duas opções do quadro superior.

As únicas regras de formatação condicional encontradas em VIGAS se referem a x/d em I15/L15/O15; não foi encontrada aprovação por formatação condicional para os comprimentos/grampos examinados. Nenhuma validação de dados foi encontrada nessa aba. Isso não exclui decisões manuais ou procedimentos externos ao arquivo.

## 7. Reprodução numérica do arquivo atual

Valores calculados novamente a partir das entradas e equações, e não adotados diretamente do cache como referência normativa. Conferidas 100 células numéricas entre entradas e resultados desta cadeia: maior diferença absoluta em relação ao cache aproximadamente 1,42e-14 nas unidades de cada célula. Isso confirma a reprodução matemática do arquivo salvo, não sua correção normativa ou comportamento de recálculo no Excel.

| Grandeza | Resultado reproduzido |
| --- | --- |
| d₁; d₂; d global | 68,375; 65,125; 67,5625 cm |
| Vc0; Vsd | 13,512690073160; 7,896 tf |
| al_base; al₁/al₂/al₃ | 67,5625 cm para todos neste caso |
| fbd má; fbd boa | 2,763196762611; 3,947423946587 MPa |
| lb má φ12,5; lb boa φ12,5 | 49,171150985642; 34,419805689950 cm |
| al+lb má; al+0,7lb má | 116,733650985642; 101,982305689950 cm |
| al+lb boa; al+0,7lb boa | 101,982305689950; 91,656363982965 cm |
| al+10φ, φ12,5 | 80,0625 cm |
| C38; C39; As_req | 1,81608; 2,393333333333; 2,393333333333 cm² |
| As fornecida no apoio, 4φ16 | 8,042477193190 cm² |
| Apoio mínimo B49 | 15,3 cm |
| lb reduzido B50; l necessário B51 | 30,840145898195; 9,177613738900 cm |
| Comprimento disponível B55 | 15,7 cm |
| As corrigida B56 | 4,701321604014 cm² |
| Déficit B57 | −3,341155589176 cm² |
| Grampos B58:B62 | −9; −6; −4; −3; −2 |

O apoio fornecido supera a área corrigida calculada, mas a planilha retorna números negativos no complemento. Isso evidencia ausência de representação explícita de “nenhum grampo necessário” na cadeia atual. Não se converteu esses números em zero, porque a tarefa é auditar o procedimento existente.

Verificação algébrica adicional de al, com d_grupo=d global: Vsd/Vc0 de 1; 1,000001; 1,5; 2; 3 produz al_base/d de 1; aproximadamente 500000,5; 1,5; 1; 0,75. Depois dos limites, al_grupo/d é 1; 1; 1; 1; 0,75. Essa distinção importa se futuramente alguém reutilizar apenas R26.

## 8. Confronto com o Concretopy

| Componente existente | Correspondência reutilizável | Diferença / ausência |
| --- | --- | --- |
| `materiais.py:Concreto.fctm`, `fctk_inf`, `fctd` | fctm, fctk,inf e minoração por gamma_c | Acima de 50 MPa o objeto usa outra expressão para fctm; B19 mantém 0,3fck^(2/3). Não supor equivalência para alta resistência |
| `materiais.py:Aco.fyd` | fyd configurável por gamma_s | Não possui fbd, fator de aderência, classificação de superfície ou comprimento de ancoragem |
| `armaduras.py:Barra`, `CamadaArmaduraLongitudinal`, `Armadura` | Áreas de barra e de conjuntos conhecidos | Não representam detalhe físico de gancho, grampo ou ancoragem disponível |
| `verificacoes/flexao.py:calcular_alturas_uteis_camadas` | Mesmo critério K5:K7 para d omitido | Valida e omite camadas vazias, em vez de representar uma terceira bitola zero |
| `ResultadoVerificacaoFlexao` | Áreas, d individuais/d equivalente e x | Não retorna al, lb, fbd, As_req de apoio ou aprovação de ancoragem |
| `verificacoes/cortante.py:dimensionar_cortante_viga` | Para flexão simples/N=0, `vc=0.6*fctd*b*d`, equivalente à família de R7 | Usa d de uma bitola, não automaticamente d ponderado das camadas. Com esforço normal pode alterar vc. Não retorna al; retorna forças em kN e também rejeita rompimento de biela |
| `elementos/viga.py:dimensionar_cortante` | Fachada do cálculo de cortante | Não implementa decalagem ou ancoragem; coeficientes da função interna não são todos expostos pela fachada |
| `normas/nbr6118.py` | Taxa mínima e espaçamentos | Nenhuma função de al, fbd, lb ou detalhe de ancoragem encontrada |
| `unidades.py` | Conversões aproximadas/exatas tf/kN e tf.m/kN.cm | A reprodução exata da planilha exige opção aproximada; mudar para 9,80665 altera números |
| `detalhamento/arranjos.py` | Área/quantidades de barras | Não verifica comprimento de ancoragem ou grampos. Não substituir a armadura existente por um novo arranjo numa futura auditoria |
| `aplicacoes/calculadora_furos.py:_calcular_solicitacoes_metodo2` | Já usa braço `d−x/2` em cálculo específico de banzos | É outra aplicação, não implementação de B12/B35 para ancoragem de extremidade. Não justifica normativamente importar essa hipótese |

A busca em `concretopy`, `docs` e `tests` não encontrou implementação/testes físicos de ancoragem ou decalagem longitudinal. “Ancora a próxima camada” na rotina de alturas úteis descreve uma referência geométrica de posição, não aderência aço–concreto. O cortante existente pode fornecer parcelas necessárias a um estudo posterior; sua resistência não equivale à verificação de ancoragem.

## 9. Hipóteses e dúvidas a resolver antes de implementar

1. Confirmar a interpretação e origem de medição de al+lb no detalhe, e se a limitação por d dos grupos cumulativos é o procedimento pretendido.
2. Identificar a regra de escolha de boa/má aderência, superfície das barras e eventual dependência de diâmetro. O arquivo não efetua essa classificação.
3. Identificar as condições que permitem a redução 0,7 por dobra. B50 aplica essa redução sem entrada de forma/confinamento e sem seleção de regime.
4. Distinguir lb básico, lb necessário por área fornecida e comprimentos mínimos. Os rótulos L22/O22 não correspondem a um cálculo por razão de áreas.
5. Definir se al+10φ é alternativa, limite ou caso específico. Não há seleção matemática no arquivo.
6. Esclarecer o braço B12=d−x/2 e a utilização de x da resistência fornecida no apoio, em vez de estado derivado da solicitação.
7. Transformar a origem manual de As do vão em dado rastreável num eventual contrato futuro; não presumir que 7,18 seja B8 ou As necessária.
8. Confirmar a intenção de C36 com fyd fixo, a convenção de N e Mk e o tratamento de sinais.
9. Documentar o desenho que fundamenta B49 e o modelo de transferência de força dos grampos; área equivalente de duas pernas não comprova ancoragem das barras principais.
10. Definir diagnóstico para camada vazia, As fornecida zero, comprimento disponível nulo/negativo e déficit negativo. A planilha não trata esses casos de forma uniforme.
11. Validar o procedimento contra a edição normativa adotada no escritório e referências independentes. A coincidência numérica do cache não resolve essas dúvidas.

**Sugestão futura, não implementada:** manter separados geometria das camadas, materiais/aderência, decalagem, comprimento básico, comprimento necessário por área e verificação do detalhe no apoio. Reutilizar propriedades e conversões do Concretopy, sem incorporar constantes manuais silenciosamente e sem chamar uma verificação parcial de “detalhamento aprovado”.

Nenhum arquivo de código, teste ou workbook foi alterado nesta auditoria. Este relatório é a única nova entrega.
