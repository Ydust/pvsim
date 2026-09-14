"""Physical normalization invariants, independent of a nationwide simulation."""
import numpy as np
import pytest
import pvsim.spectral as sp

@pytest.mark.parametrize('gap',[1.60,1.68,1.75])
def test_reference_matching_is_collection_attenuation(gap,monkeypatch):
    monkeypatch.setattr(sp,'TANDEM_TOP_EG_REF',gap)
    sp._tandem_reference_subcell_yields.cache_clear()
    try:
        wr,er=sp.reference_am15g();rt,rb=sp._tandem_subcell_weights(wr,er,25)
        scales=np.minimum(rt,rb)/np.array([rt,rb])
        assert np.all((scales>0)&(scales<=1))
        assert np.allclose(scales*np.array([rt,rb]),min(rt,rb))
        for mode in ['reference_matched','unscaled_ratio']:
            assert sp.tandem_current_matching_factor(wr,er,25,normalization=mode)==pytest.approx(1)
            assert sp.tandem_current_matching_factor(wr,np.zeros_like(er),normalization=mode)==0
        w,e=sp.generate_spectrum(70);cur=np.array(sp._tandem_subcell_weights(w,e,60))
        G=sp._broadband(e,w);Gr=sp._broadband(er,wr)
        assert sp.tandem_current_matching_factor(w,e,60)==pytest.approx(min(scales*cur)/min(rt,rb)*Gr/G)
        assert sp.tandem_current_matching_factor(w,e,60,normalization='unscaled_ratio')==pytest.approx(min(cur)/min(rt,rb)*Gr/G)
    finally:sp._tandem_reference_subcell_yields.cache_clear()

def test_unknown_family_fails():
    w,e=sp.reference_am15g()
    with pytest.raises(ValueError):sp.tandem_current_matching_factor(w,e,normalization='unknown')
