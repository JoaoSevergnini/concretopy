# Demanda positiva no apoio - implementacao

Data: 2026-10-05.

## Escopo

Somente As necessaria pelas condicoes A/B/C. Nao verifica comprimento de
ancoragem ou aprova a armadura detalhada. A palavra ancoragem na solicitacao
final foi entendida no escopo acordado: demanda positiva no apoio.

## Arquitetura e reutilizacao

Nova funcao pura calcular_armadura_positiva_apoio em verificacoes/armadura_apoio.py.
Materiais, camadas e secoes existentes. Sem dependencia de elementos/TQS.
Reutiliza verificar_flexao_viga_retangular para d/x/areas/diagnosticos e
calcular_al separadamente em B1 e B2. Reutiliza dimensionar_flexao_viga_retangular
para A e As_span; extensao retrocompativel keyword-only d_cm/d_linha_cm.
Sem duplicar equacoes de flexao, linha neutra, centroide, materiais ou al.
Regra elementar C em normas/nbr6118.py; resultados imutaveis em resultados.py.

## Decisoes confirmadas

- B apenas em apoio extremo. B1: Mk=0/Vk maximo; B2: Mk positivo/Vk minimo.
  Selecao de estados e criterio de engenharia, nao prescricao textual da norma.
- C independente do momento positivo no apoio. Mk negativo (<=0) so escolhe
  a fracao pela razao com Mk positivo maximo do vao. Zero e igualdade 0.5:
  C1=1/3. Acima de 0.5: C2=1/4.
- d do vao explicito; secao do vao pode diferir, materiais comuns.
- x pertence ao estado resistente das barras reais, nao ao dimensionamento A.
- z=d-x/2 e simplificacao de engenharia; braco resistente legado nao alterado.
- Nd e tracao de calculo nao negativa, sem majoracao adicional. Vc=Vc0 e
  estribos verticais herdados de calcular_al; nao resolve flexo-compressao.
- Demanda de A/C preserva minimo de flexao e armadura comprimida retornada.
  Se houver compressao, exige d_linha do apoio/vao explicitamente; nao atesta
  existencia dessa armadura. Sem dado suficiente retorna ValueError.
- Hipoteses invalidas das camadas impedem uso de x candidato. Aviso de
  ductilidade nao trunca x. Empates exatos mantem todos os governantes.

## Unidades e saidas

cm, mm, cm2, MPa, kN, kN.cm. Fsd/(fyd_mpa*0.1) retorna cm2. Resultado
conserva esforcos, coeficientes, secoes, d/x/z, areas/posicoes das camadas,
A/B/C, B1/B2, al/Fsd de cada estado, demanda maxima e governantes.
Sem campo atende. Propriedades derivadas de A/C evitam repetir dados.

## Testes executados

- Baseline Concretopy: 237 passed.
- tests/test_armadura_apoio.py: 104 passed.
- Suite completa Concretopy: 341 passed.
- Suite completa engineering-assistant atual: 232 passed, 9 subtests passed.
- Comando: python -B -m pytest -q -p no:cacheprovider (ambiente temporario).
- Exemplo docs/armadura_apoio.md executado: As=3.3886407578921305 cm2,
  governante B, estado B2.
- git diff --check sem erros.
- Hashes ancoragem.py, decalagem.py, materiais.py e cortante.py identicos
  aos registrados antes desta etapa.

Referencia manual dos testes: C20, gammas=1, b=20,d=45,As=2.72 cm2;
T=136 kN, y=4 cm, x=5 cm, z=42.5 cm. Dimensionamento M=5848 kN.cm
produz As=2.72. B2 com Mk=4250 e Vk=10: Fsd=110 kN, As=2.2 cm2.
Testes adicionais cobrem todos os governantes, empates, fronteiras, sinais,
dados nao finitos, camadas multiplas, d do vao independente, compressao,
compatibilidade do dimensionador e imutabilidade/serializacao.

## Arquivos desta etapa

Criados: concretopy/verificacoes/armadura_apoio.py,
tests/test_armadura_apoio.py, docs/armadura_apoio.md e este relatorio.
Alterados: concretopy/verificacoes/flexao.py, concretopy/normas/nbr6118.py,
concretopy/resultados.py, concretopy/api.py, concretopy/__init__.py,
concretopy/verificacoes/__init__.py, docs/api_publica.md, docs/ancoragem.md.
Modificacoes preexistentes no working tree foram preservadas.
Nenhum arquivo do engineering-assistant foi editado por esta implementacao;
sua suite atual foi executada para conferir integracao.

## Limitacoes

Sem selecao TQS, interpretacao de envoltorias, verificacao de concomitancia,
arranjo de barras, comprimento disponivel, barra reta/gancho, dobras,
grampos, otimizacao ou alteracao automatica da armadura. A selecao B1/B2
nao comprova esforcos da mesma combinacao na extremidade do vao efetivo.
Permanecem os limites de taxa minima/maxima do dimensionador existente.
Proximo passo: integrar a demanda com verificacao explicita de ancoragem
quando geometria disponivel e regras de detalhamento estiverem definidas.
