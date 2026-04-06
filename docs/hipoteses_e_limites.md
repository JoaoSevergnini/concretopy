# Hipóteses e limites atuais do pacote

## Convenções de unidades

O pacote assume como unidades públicas oficiais:

- tensões em MPa;
- geometria em cm;
- bitolas em mm;
- forças em kN;
- momentos em kN.cm.

Entradas em tf e tf.m são aceitas apenas como conveniência, com conversão explícita para as
unidades oficiais do núcleo.

## Escopo técnico atual

O pacote já cobre:

- materiais de concreto e aço;
- viga retangular em flexão e cortante;
- apoio ao detalhamento de armaduras;
- geometria de seções poligonais;
- base para flexo-compressão;
- calculadora de reforço de furos em vigas.

## Limites atuais

### Flexo-compressão

O módulo de flexo-compressão já foi migrado para o pacote, mas ainda deve ser tratado como
um núcleo técnico em consolidação. Antes de uso oficial em produção, recomenda-se validação
com casos de referência do escritório e exemplos independentes.

### Calculadora de furos

A calculadora de furos já está operacional e adequada para integração e testes de escritório.
Ainda assim, antes de chamá-la de versão final normativa, recomenda-se:

- regressão contra o notebook legado;
- conferência de casos limite;
- revisão das hipóteses geométricas adotadas;
- comparação com exemplos aceitos internamente.

## Responsabilidade de integração

O `concretopy` é um pacote de cálculo. Desenho, detalhamento gráfico e integração com TQS devem
ficar fora deste repositório.
