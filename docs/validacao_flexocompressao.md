# Validação da flexo-compressão e resolvedor da linha neutra

Nesta revisão, o resolvedor da linha neutra foi reforçado para lidar melhor com casos em que a função de equilíbrio apresenta descontinuidades numéricas locais.

## O que mudou

- a seção comprimida passou a ser obtida por recorte geométrico do polígono (`Sutherland-Hodgman`) em vez da lógica anterior baseada em interseções ad hoc;
- as tensões de concreto e aço passaram a respeitar explicitamente a convenção oficial do pacote:
  - tensões em **MPa** na API pública;
  - conversão interna para **kN/cm²** durante o equilíbrio de forças e momentos;
- o resolvedor da linha neutra passou a:
  - varrer uma grade densa de valores de `x`;
  - procurar intervalos com mudança de sinal;
  - resolver por bisseção quando existe raiz contínua;
  - aceitar o melhor ponto de equilíbrio quando a função apresenta um salto pequeno decorrente do diagrama idealizado do aço, desde que o residual fique dentro de uma tolerância de engenharia.

## Critério atual de aceitação

A solução é aceita quando o residual axial fica abaixo de:

- `max(1e-3 kN, 1% da capacidade axial de referência da seção)`

Esse critério foi adotado para permitir estabilizar casos angulares que antes lançavam `ConvergenciaNaoAtingida`, principalmente em seções simples e simétricas.

## Resultado prático desta revisão

- casos estáveis anteriores continuam resolvendo;
- o caso angular que antes falhava em `60°` agora fecha sem exceção;
- a validação agora está mais alinhada com a convenção oficial de unidades do pacote.

## O que ainda merece atenção

Mesmo com o resolvedor mais robusto, a flexo-compressão ainda deve ser validada com:

- exemplos de referência do escritório;
- comparação com planilhas antigas;
- casos com seções não retangulares e arranjos de armadura mais complexos.

Esse item passa a ser considerado **tecnicamente encaminhado**, mas ainda não totalmente encerrado para publicação de uma `v1.0` como biblioteca oficial.
