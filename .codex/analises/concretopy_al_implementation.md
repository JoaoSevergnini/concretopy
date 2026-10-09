# Implementacao de al no Concretopy

Data: 2026-10-05.

## 1. Escopo e arquitetura

Primitiva pura `calcular_al`, em `concretopy/verificacoes/decalagem.py`,
exportada pela raiz, api e verificacoes. ResultadoDecalagemAl imutavel em
resultados.py. Nenhuma dependencia de elementos, TQS ou diagramas.
Inclui a fachada VigaRetangular.calcular_decalagem, sem inferencia de d.
O metodo encaminha concreto/bw da viga e os argumentos para a primitiva.
Nao refatora cortante nem altera ancoragem, materiais ou regras existentes.

## 2. Equacao e origem

Vsd=gamma_f*Vk; Vc0=0.6*(fctd*0.1)*b*d.
Se Vsd<=Vc0, al_base=d; senao al_base=0.5*d*Vsd/(Vsd-Vc0).
Origem: regra expressamente confirmada pelo engenheiro, auditoria
longitudinal_anchorage_audit.md (VIGAS!R26/I21) e imagem normativa fornecida.
A imagem mostra a expressao geral com cotg(alfa), sem numero completo de item.
Escopo adotado: estribos verticais (alfa=90 graus), Vc=Vc0. Nao generaliza
para estribos inclinados nem modifica Vc por esforco normal.

## 3. Unidades

b/d/al em cm; fctd em MPa; Vk/Vsd/Vc0 em kN; gammas adimensionais.
Conversao explicita 1 MPa=0.1 kN/cm2. Reutiliza Concreto.fctd(gamma_c).
Nao duplica fctm/fctk_inf. Nenhuma conversao tf no codigo da primitiva.

## 4. Contrato de Vk e d

vk_abs_kn e magnitude caracteristica nao negativa escolhida pelo chamador.
Negativos sao rejeitados; nao usa abs(). Vk=0 e valido. d_cm e obrigatorio
e usado sem inferir camadas, centroides ou altura global em todas as etapas.
Valida tipos, finitude, b/d/gammas positivos, dominio 20<=fck<=90 MPa e
resultados numericos representaveis. Usa TypeError/ValueError.

## 5. al_base e al

Preserva base e valor limitado separadamente. Branch registra vsd_le_vc0
ou vsd_gt_vc0. Resultado inclui Vk, gamma_f, gamma_c, Vsd, b, d, fctd, Vc0,
al_base, al_min, al_max, al. Base pode exceder d sem alterar o limite final.

## 6. Limites

al=max(min(al_base,d),0.5*d), portanto 0.5*d<=al<=d.
Na igualdade Vsd=Vc0 nao divide. Entre Vc0 e 2Vc0 a base supera d,
mas al=d. Para 3Vc0, al=0.75d; para Vsd elevado tende a 0.5d por cima
(na precisao finita pode arredondar ao piso). Calcula a razao antes do
produto para evitar overflow desnecessario; rejeita resultados nao finitos.

## 7. Regressao Excel

b=19 cm, d=67.5625 cm, fck=40 MPa, gamma_f=gamma_c=1.4.
Teste converte explicitamente 5.64 tf * 10=56.4 kN, apenas para reproduzir
a aproximacao documental da planilha. Vsd=78.96 kN;
Vc0 aproximadamente 135.12690073160 kN; al_base=al=67.5625 cm.

## 8. Regra de workflow confirmada

Registrada no engineering-assistant em
`tools/reinforcement_checks/al_shear_selection.md`, com link no README:
`engineer_confirmed_al_shear_selection_v1`.
Escalonamento no vao: maximo |Vk| de todo o vao fisico.
Ancoragem em apoio: maximo |Vk| apenas da regiao do apoio analisado.
A definicao espacial da regiao do apoio permanece pendente, sem inventar
dominio. E regra confirmada de workflow, nao exigencia normativa inferida.
Nenhuma selecao automatica ou verificacao completa da N3 implementada.

## 9. Testes e preservacao

Python 3.11, pytest 9.1.1, ambiente temporario concretopy-ancoragem-venv.
Comando de cada suite: python -B -m pytest -q -p no:cacheprovider.
- Antes: Concretopy 154 passed.
- Novos testes de decalagem: 74 passed (tests/test_decalagem.py).
- Primitiva inicial: Concretopy 228 passed, incluindo os 78 de ancoragem anteriores.
- Com a fachada na viga: Concretopy 237 passed; 9 testes adicionais em
  tests/test_viga.py cobrem equivalencia, coeficientes, golden, d obrigatorio
  e validacoes. Suite completa executada; git diff --check sem erros.
- Complemento da fachada: elementos/viga.py, tests/test_viga.py,
  docs/ancoragem.md, docs/api_publica.md e este relatorio atualizados.
  Nenhum arquivo do engineering-assistant alterado neste complemento.
- engineering-assistant: suite completa 181 passed, incluindo V501,
  V1001, regioes de flexao e interpolacao (test_moment_diagram.py).
- git diff --check sem erros nos dois repositorios.

Hashes SHA256 iguais antes/depois comprovam preservacao dos arquivos:
- verificacoes/ancoragem.py: 0FBC85483AECCA1119C23051764C80C6B016BB7B9319A081FFA6A6B14BEED20A
- verificacoes/cortante.py: 5DA3FDAE24ECA677CC8E6BCCEA6760F156EEFAADB4A0F6255C7928FDDE24B757
- materiais.py: F259B71928F85C61792A32B3303B902F2FF66136470981839D3EE0C528F4100F

Criados nesta etapa: verificacoes/decalagem.py, tests/test_decalagem.py,
este relatorio; no engineering-assistant, al_shear_selection.md.
Atualizados nesta etapa: resultados.py, api.py, __init__.py da raiz e de
verificacoes, docs/ancoragem.md, docs/api_publica.md; no engineering-assistant,
tools/reinforcement_checks/README.md. Alteracoes de ancoragem preexistentes
no working tree foram preservadas; nao confundir com mudancas desta etapa.

## 10. Limitacoes

Sem verificacao Vrd2/resistencia, escolha de cortante, apoio, cortes, grampos,
TQS, interpolacao, classificacao de aderencia ou desenho. Nao soma al a lb,
lb_nec ou comprimento disponivel. calcular_ancoragem.atende continua sendo
apenas comprimento_disponivel>=lb_nec. Nao certifica aplicabilidade do
modelo a estribos inclinados ou a regimes com Vc diferente de Vc0.

## 11. Proximo passo

Formalizar a regiao de apoio e a composicao operacional dos comprimentos
antes de implementar verificacao de apoio/N3 no engineering-assistant.
A futura selecao de Vk pertence ao chamador; a primitiva permanece fisica.


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
