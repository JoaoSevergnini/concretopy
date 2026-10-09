"""18.3.3.2 branch selection; defect confirmed/authorized by engineer 2026-10-07."""
from types import SimpleNamespace
import pytest
from concretopy.normas import espacamento_max_estribo_vigas_cm

@pytest.mark.parametrize('vd,d,expected',[(0,50,30),(66.999,50,30),(67,50,30),(67.001,50,15),(90,50,15),(67,100,30),(90,100,20),(20,30,18)])
def test_spacing_branch_and_absolute_limit(vd,d,expected):
    viga=SimpleNamespace(vrd2_kn=100,secao=SimpleNamespace(d=lambda phi:d))
    assert espacamento_max_estribo_vigas_cm(viga,vd,16)==pytest.approx(expected)
