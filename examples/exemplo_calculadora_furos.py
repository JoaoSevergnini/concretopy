from concretopy import CalculadoraReforcoFuros

calc = CalculadoraReforcoFuros.from_tf_tfm(
    h=60,
    b=20,
    h_furo=10,
    b_furo=12,
    fck=30,
    C=15,
    Mk_tfm=-12,
    Vk_tf=12,
    cobrimento=3,
    armadura_superior=[(2, 20)],
    armadura_inferior=[(2, 12.5)],
)

resultado = calc.calcular_reforco(metodo_solicitacoes='FUSCO')
print(resultado.memorial)
