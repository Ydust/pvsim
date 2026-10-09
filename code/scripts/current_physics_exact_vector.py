"""Vectorize the original 600-point Voc/MPP grids without interpolation tables.
Binary search finds the same last nonnegative current grid point as _find_voc.
The original Lambert-W, linear zero crossing and parabolic MPP refinement remain.
"""
import numpy as np
from scipy.special import lambertw
from pvsim.materials import K_B,Q,T_REF,G_REF
from pvsim.cell import K_EV

def power(tech,G,T,E,ns,npts):
    G,T,E=np.broadcast_arrays(np.asarray(G,float),np.asarray(T,float),np.asarray(E,float))
    shape=G.shape;G=G.ravel();T=T.ravel();E=E.ravel();out=np.zeros(len(G))
    mask=G>1;ids=np.flatnonzero(mask)
    for st in range(0,len(ids),1024):
        ix=ids[st:st+1024];tk=T[ix]+273.15;ge=np.maximum(E[ix],1e-6)
        IL=ge/G_REF*(tech.I_L_ref+tech.alpha_sc*(tk-T_REF))
        I0=tech.I_o_ref*(tk/T_REF)**3*np.exp(tech.Ea_recomb/K_EV*(1/T_REF-1/tk))
        Rsh=tech.R_sh_ref*G_REF/ge*ns;Rs=tech.R_s*ns
        a=tech.n_ideality*1*K_B*tk/Q*ns;A=1+Rs/Rsh
        def current(v):
            dims=v.ndim-1
            aa=a.reshape((-1,)+(1,)*dims);AA=A.reshape((-1,)+(1,)*dims)
            il=IL.reshape((-1,)+(1,)*dims);i0=I0.reshape((-1,)+(1,)*dims)
            c=Rs*i0/(AA*aa);dd=(Rs*(il+i0)+v)/(AA*aa)
            ww=np.real(lambertw(c*np.exp(np.clip(dd,-700,700))))
            return (aa*(dd-ww)-v)/Rs
        est=a*np.log(IL/I0+1);step=1.5*est/599
        low=np.zeros(len(ix),dtype=int);high=np.full(len(ix),599,dtype=int)
        for _ in range(10):
            mid=(low+high+1)//2;positive=current(step*mid)>=0
            low=np.where(positive,mid,low);high=np.where(positive,high,mid-1)
        k=low;v0=step*k;v1=step*np.minimum(k+1,599)
        i0=current(v0);i1=current(v1)
        voc=np.divide(i0*(v1-v0),i1-i0,out=np.zeros_like(v0),where=(i1!=i0))
        voc=v0-voc;voc=np.where(k==599,v0,voc)
        v=voc[:,None]*np.linspace(0,1,npts)[None,:]
        pp=v*np.clip(current(v),0,None);km=np.argmax(pp,axis=1);ar=np.arange(len(ix))
        left=np.maximum(km-1,0);right=np.minimum(km+1,npts-1)
        x0=v[ar,left];x1=v[ar,km];x2=v[ar,right]
        y0=pp[ar,left];y1=pp[ar,km];y2=pp[ar,right];den=y0-2*y1+y2
        delta=np.divide(.5*(x2-x0)*(y2-y0),den,out=np.zeros_like(den),where=den!=0)/2
        vmp=np.where((km>0)&(km<npts-1),x1-delta,x1)
        p=vmp*current(vmp);p=np.where((voc>0)&(current(np.zeros_like(voc))>0),p,0)
        out[ix]=p
    return out.reshape(shape)

def array_dc_power(tech,irradiance,tcell_C,n_modules=1,effective_irradiance=None,mismatch_loss=.02,npts=150):
    G=np.atleast_1d(np.asarray(irradiance,float));E=G if effective_irradiance is None else effective_irradiance
    p=power(tech,G,tcell_C,E,tech.cells_in_series,npts)*n_modules*(1-mismatch_loss)
    return p if p.size>1 else float(p[0])
