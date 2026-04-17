import sys
sys.path.append('P:\\Joao Severgnini\\Simon\\concretopy')

from concretopy import CalculadoraReforcoFuros

calc = CalculadoraReforcoFuros.from_tf_tfm(
    h=80,
    b=19,
    h_furo=12,
    b_furo=22,
    fck=40,
    C=37,
    Mk_tfm=8.1,
    Vk_tf=4.4,
    cobrimento=2.5,
    armadura_superior=[(2, 6.3)],
    armadura_inferior=[(3, 12.5)],
)


resultado = calc.calcular_reforco(metodo_solicitacoes='FUSCO')
calc._verif_romp_bielas()
calc._gerar_memorial_texto()
print(resultado.memorial)
print(resultado.resistencia_biela_equivalente_kn)
print(calc.Vk*1.4*1.2)
print(resultado.resistencia_biela_equivalente_kn < calc.Vk*1.4*1.2)
print("cobrimento: ", calc.viga.cobrimento)
print("alfa_v2: ", calc.concreto.alfa_v2)