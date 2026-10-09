from dataclasses import asdict
import pytest
from concretopy import SecaoRetangular,Concreto,Aco,ResultadoCortante,RompimentoBielaCompressao
from concretopy.verificacoes import dimensionar_cortante_viga

def run(vk=0,**kwargs):return dimensionar_cortante_viga(SecaoRetangular(19,52,2.5,5),Concreto(40),Aco(500),vk,**kwargs)
@pytest.mark.parametrize('vk',[0,50,100,200,350])
def test_components_preserve_governance(vk):
 r=run(vk);assert r.asw_por_s==max(r.asw_por_s_calculado,r.asw_por_s_minimo)
 assert r.asw_por_s_calculado>=0

def test_zero_shear_component_is_zero_not_negative():
 r=run(0);assert r.asw_por_s_calculado==0;assert r.asw_por_s_minimo==r.asw_por_s>0

def test_calculated_below_minimum_preserved():
 r=run(100);assert 0<r.asw_por_s_calculado<r.asw_por_s_minimo;assert r.asw_por_s==r.asw_por_s_minimo

def test_shear_governs():
 r=run(200);assert r.asw_por_s==r.asw_por_s_calculado>r.asw_por_s_minimo

def test_legacy_construction_equality():
 r=run();legacy=ResultadoCortante(r.asw_por_s,r.vc,r.vrd2)
 assert legacy==r;assert legacy.asw_por_s_calculado is None

def test_additive_serialization():
 r=run();assert set(asdict(r))=={'asw_por_s','vc','vrd2','asw_por_s_calculado','asw_por_s_minimo'}

@pytest.mark.parametrize('vk,expected',[(0,2.6667041772501334),(100,2.6667041772501334)])
def test_old_governing_reference(vk,expected):assert run(vk).asw_por_s==pytest.approx(expected)

def test_diagonal_failure_preserved():
 with pytest.raises(RompimentoBielaCompressao):run(1000)

def test_factors_pass_through():
 a,b=run(100),run(100,gamma_f=1.6,gamma_s=1.2)
 assert b.asw_por_s_calculado>a.asw_por_s_calculado;assert b.vrd2==a.vrd2
