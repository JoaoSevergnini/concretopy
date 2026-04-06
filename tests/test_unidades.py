from concretopy.unidades import tf_para_kn, tfm_para_kncm, kn_para_tf, kncm_para_tfm


def test_conversoes_aproximadas_tf_kn():
    assert tf_para_kn(12.0) == 120.0
    assert tfm_para_kncm(18.0) == 18000.0
    assert kn_para_tf(120.0) == 12.0
    assert kncm_para_tfm(18000.0) == 18.0
