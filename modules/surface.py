import numpy as np
import rasterio as rio
from rasterio.enums import Resampling
VON_KARMA = 0.41 # von Karman onstatn

def load_stack(path, names=('emissivity', 'lst_cal', 'tb_uncal', 'water_mask', 'albedo', 'canopy_height'), downsample=1):
    """
    downsample > 1 averages blocks of pixels. The native grid is 6 cm.
 
    Returns (data, profile).
    """
    with rio.open(path) as src:
        h, w = src.height // downsample, src.width // downsample
        data = {}
        idx = {d: i+1 for i,d in enumerate(src.descriptions)}
        for n in names:
            data[n] = src.read(idx[n], out_shape=(h, w), resampling=Resampling.average).astype('float32')
        prof = src.profile
        prof.update(height=h, width=w, transform=src.transform * src.transform.scale(src.width / w, src.height / h))
    return data, prof

def valid_mask(data, key='lst_cal'):
    return np.isfinite(data[key])

def roughness(h_c, z0m_ratio=0.1, d_ratio=0, kB_inv=6):
    """
    Roughness lengths from canopy height.
    """
    h_c = np.asarray(h_c)
    z0m = z0m_ratio * h_c
    d = d_ratio * h_c
    z0h = z0m / np.exp(kB_inv)
    return z0m, d, z0h

def psi_m(zeta):
    """Paulson (1970) integrated stability correction for momentum."""
    zeta = np.asarray(zeta, dtype='float64')
    x = (1 - 16 * np.clip(zeta, None, 0)) ** 0.25
    unstable = (2 * np.log((1 + x) / 2) + np.log((1 + x**2) / 2) - 2 * np.arctan(x) + np.pi / 2)
    return np.where(zeta < 0, unstable, -5 * zeta)


def psi_h(zeta):
    """Paulson (1970) integrated stability correction for heat."""
    zeta = np.asarray(zeta, dtype='float64')
    x = (1 - 16 * np.clip(zeta, None, 0)) ** 0.25
    return np.where(zeta < 0, 2 * np.log((1 + x**2) / 2), -5 * zeta)

def aerodynamic_resistance(u, z0m, d, z0h, z_u=2, z_T=2, L=None,
                           ra_min=1, ra_max=500, u_min=0.5):
    """
    Aerodynamic resistance to heat transfer [s/m].

    ra = ln((z-d)/z0m) * ln((z-d)/z0h) / (k^2 * u)

    With stability, pass L from air.obukhov_from_station().
    Let's see if neutral resistance assumed will overestimate ra and
    therefore underestimate H for peatlands.

    u is padded because ra could cause stack overflow, ra is
    clipped for the same reason.
    """
    u = np.maximum(np.asarray(u, dtype='float32'), u_min)
    zm = np.maximum(z_u - d, 0.05)
    zt = np.maximum(z_T - d, 0.05)

    if L is None:
        num = np.log(zm / z0m) * np.log(zt / z0h)
    else:
        num = ((np.log(zm / z0m) - psi_m(zm / L) + psi_m(z0m / L)) * (np.log(zt / z0h) - psi_h(zt / L) + psi_h(z0h / L)))

    ra = num / (VON_KARMA ** 2 * u)
    return np.clip(ra, ra_min, ra_max)


def build_surface(data, u, z_u=2, z_T=2, L=None,  **kw):
    """
    Assemble every Ts-independent raster a flux layer needs.
    """
    valid = valid_mask(data)
    water = (data['water_mask'] > 0.5) & valid # if resampling happens, water should still be major
    land = valid & ~water

    z0m, d, z0h = roughness(data['canopy_height'], **kw)

    surf = {
        "valid":valid,
        "albedo":np.where(valid, data['albedo'], np.nan),
        "emis":np.where(valid, data['emissivity'], np.nan),
        "water":water, "land":land,
        "h_c":data['canopy_height'], "z0m":z0m, "d":d, "z0h":z0h,
        "ra":aerodynamic_resistance(u, z0m, d, z0h, z_u, z_T, L)}
    
    return surf