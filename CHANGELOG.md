# Changelog

## 1.0.0 - 2026-04-04

Primeira versão estável do pacote `concretopy`.

### Adicionado
- Estrutura oficial de pacote Python com `pyproject.toml`.
- API pública estável em `concretopy.api` e reexportação em `concretopy`.
- Modelos de materiais, seções, armaduras e elementos estruturais.
- Verificações de flexão, cortante e flexo-compressão.
- Utilitários de detalhamento e layouts de barras.
- Conversões de unidades com suporte oficial a kN/kN.cm e compatibilidade com tf/tf.m.
- Calculadora de reforço de furos em vigas.
- Exceptions próprias e resultados tipados.
- Testes automatizados e documentação inicial.

### Ajustado
- Convenção oficial de unidades do pacote:
  - tensões em MPa
  - geometria em cm
  - bitolas em mm
  - forças em kN
  - momentos em kN.cm
- Solver de linha neutra revisado para maior robustez em flexo-compressão.

### Documentação
- README expandido com escopo, unidades, exemplos e estado da biblioteca.
- Documentos de hipóteses, limites, checklist de release, validação da flexo-compressão e API pública.

### Observação
- Apesar da estrutura e da API estarem estabilizadas, ainda é recomendável manter validação contínua com casos reais do escritório antes de adoção externa ampla.
