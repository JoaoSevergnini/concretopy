# Refatoracao do apoio e ancoragem positiva de extremidade

Data: 2026-10-06.

## Escopo e arquitetura

A demanda de apoio permanece em verificacoes/armadura_apoio.py, reutilizando
analise resistente das camadas, centroide/linha neutra e dimensionamento de
flexao. A verificacao de ancoragem e uma nova funcao de nivel superior em
verificacoes/ancoragem.py. Resultados imutaveis permanecem em resultados.py;
o coeficiente elementar alpha fica em normas/nbr6118.py.
Nao ha importacao de elementos por verificacoes nem integracao TQS.

## Alteracao deliberada da API recente

calcular_armadura_positiva_apoio recebe somente mk_apoio_kncm e vk_apoio_kn,
um par caracteristico nao negativo por chamada. Foram removidos os argumentos
mk_positivo_apoio_kncm, vk_max_abs_apoio_kn e vk_min_abs_apoio_kn, a dataclass
EstadoBArmaduraApoio e os campos estados/governantes internos da condicao B.
CondicaoBArmaduraApoio preserva apenas aplicabilidade, decalagem, Fsd e As.
Nao ha adaptador para a API recente corrigida. Nenhum consumidor dessa API
foi encontrado nos arquivos pesquisados do engineering-assistant.

A: dimensionamento do momento positivo recebido, incluindo minimo; zero
nao aplica A. B: somente extremo, Md=gamma_f*Mk, Vd=gamma_f*Vk,
Fsd=Md/z+(al/d)*Vd+Nd; As_b=Fsd/(fyd_mpa*0.1). Nd e tracao ja de calculo.
al e calculado com o Vk exato recebido. d/x vem da configuracao real das
camadas. z=d-x/2 continua simplificacao de engenharia, nao identidade geral.
C: dimensiona o maximo positivo do vao, incluindo minimo; razao <=0.5
(incluindo momento negativo nulo) usa 1/3, acima usa 1/4.
O momento negativo serve exclusivamente a essa fracao. Secao/d do vao
continuam independentes. Resultado global e max(A,B,C), preservando empates
exatos e os diagnosticos existentes, sem aprovacao do detalhamento.

O chamador seleciona os pares, realiza chamadas independentes e compara
as demandas. A biblioteca nao possui selecao interna de estados de envoltoria.

## Ancoragem e diagnosticos

Nova API publica: verificar_ancoragem_positiva_apoio e
ResultadoVerificacaoAncoragemApoio, na raiz e concretopy.api.
Reutiliza calcular_ancoragem com areas iguais apenas para obter propriedades,
lb e lb_min. Depois aplica as areas reais, inclusive area efetiva insuficiente.
Nao duplica formulas de fbd/lb/lb_min nem modifica a primitiva legada.

```text
alpha = 0.7 com gancho valido informado; 1.0 caso contrario
lb_nec_sem_min = alpha*lb*As_calculada/As_efetiva
lb_nec = max(lb_nec_sem_min, lb_min)
As_corr_matematica = alpha*lb*As_calculada/comprimento_disponivel
As_corr = max(As_calculada, As_corr_matematica)
As_adicional = max(0, As_corr-As_efetiva)
atende = area_suficiente AND comprimento_suficiente AND NOT comprimento_menor_lb_min
```

As_calculada e a demanda a ancorar; As_efetiva e a area real participante.
Falta de area, falta de comprimento e comprimento abaixo do minimo possuem
diagnosticos separados. Comprimento positivo abaixo de lb_min nao interrompe
calculos; retorna as tres areas inversas e aviso de que somente aumentar area
nao resolve o minimo. As_adicional nao significa area de grampo.

Comprimento e areas devem ser positivos e finitos. Zero no comprimento da
nova verificacao e rejeitado pois a inversao e indefinida. calcular_ancoragem
continua aceitando comprimento zero e rejeitando As_efetiva < As_calculada,
como antes. Mudancas de bitola/gancho/aderencia exigem recalculo da alternativa.

O chamador fornece comprimento diretamente e valida geometria/condicoes do
gancho. Nao se calcula comprimento de apoio menos cobrimento, nao se aplica
tabela de dobra e nao se soma decalagem automaticamente.

## Unidades e proveniencia

Geometria/comprimentos cm, bitolas mm, areas cm2, tensoes MPa, forcas kN,
momentos kN.cm. Conversao de fyd para area: 1 MPa=0.1 kN/cm2.
Razoes e coeficientes adimensionais; nenhuma conversao tf nova.
As condicoes A/B/C seguem a referencia e decisoes ja validadas do item
18.3.2.4 fornecidas pelo engenheiro. Comprimentos e alpha reutilizam as
regras de 9.4.2.4/9.4.2.5 documentadas no projeto. O calculo inverso e
transformacao algebrica; z e a simplificacao de engenharia identificada.
Selecao/comparacao de pares sao procedimento do chamador, nao prescricao
implementada de selecao normativa de envoltorias.

## Validacao antes/depois

- Antes: Concretopy 341 testes aprovados.
- Depois: Concretopy 405 testes aprovados.
- Especificos de apoio + nova ancoragem + ancoragem legada: 246 aprovados,
  incluindo os 78 testes legados de ancoragem.
- Engineering-assistant antes e depois: 232 testes e 9 subtestes aprovados.
- git diff --check: aprovado, sem erros.

Comando das suites: python -B -m pytest -q -p no:cacheprovider, usando o
ambiente temporario Python 3.11 com pytest instalado. A suite do assistente
foi executada no diretorio do proprio repositorio; nenhum arquivo dele foi alterado.

Testes manuais: C20, d45, As2.72 -> x5,z42.5; Mk4250,Vk10 -> Fsd110,
As_b2.2. C50, phi25 -> lb62.5,lb_min25; demanda4/efetiva5 -> lb_nec50
(reta),35 (gancho). L25 -> As_corr10, adicional5; L10 -> As_corr25,
adicional20, mas limite minimo impede atendimento mesmo com area corrigida.
Cobertura inclui governantes A/B/C, empate, minimo de A/C, camadas reais,
secoes independentes, pares independentes, tipo intermediario, aderencia,
eta3/25phi, limites de comprimento, insuficiencia de area, imutabilidade,
serializacao e entradas invalidas.

Hashes antes/depois confirmaram flexao.py, decalagem.py e materiais.py
integralmente preservados. O hash anterior de ancoragem.py foi reproduzido
removendo somente a funcao nova, seus imports e ajustes descritivos das docstrings:
o codigo da primitiva e validacoes legadas permanece identico.
Alteracoes preexistentes do repositorio foram preservadas.

## Arquivos desta etapa

Modificados:
- concretopy/verificacoes/armadura_apoio.py
- concretopy/verificacoes/ancoragem.py
- concretopy/resultados.py
- concretopy/normas/nbr6118.py
- concretopy/api.py
- concretopy/__init__.py
- concretopy/verificacoes/__init__.py
- tests/test_armadura_apoio.py
- docs/armadura_apoio.md
- docs/ancoragem.md
- docs/api_publica.md

Criados:
- tests/test_ancoragem_apoio.py
- .codex/analises/apoio_refatoracao_ancoragem_extremidade.md

Alguns arquivos modificados nesta etapa ja eram nao rastreados por Git devido
as implementacoes anteriores; a lista acima descreve a etapa, nao o diff total
acumulado. Relatorios anteriores sao historicos; este registra a API vigente.

## Limites e proximo passo

Nao interpreta TQS/desenho, seleciona envoltorias/concomitancia, escolhe
barras/gancho, valida geometria do gancho, define comprimento disponivel,
aplica regra pratica de dobra, dimensiona grampos, otimiza ou corrige prancha.
Nao verifica Vrd2 nem ajusta Vc por Nd nesta primitiva de decalagem.
As_corr descreve alternativa matematica mantendo os parametros recebidos,
nao solucao completa de detalhamento. Atende cobre area/comprimento deste
procedimento, nao certifica todos os requisitos de detalhamento.

Proximo passo: o engineering-assistant selecionar pares e demanda governante,
fornecer comprimento/gancho interpretados e explorar alternativas mediante
chamadas independentes, em etapa separada.
