"""
This script contains functions that work with emissivity.
"""
import numpy as np
import scipy.ndimage as ndimage

def calculate_emissivity(ndvi_arr, eps_soil=0.96, eps_veg=0.98, ndvi_s=0.5, ndvi_v=0.9):
    ems = np.full(ndvi_arr.shape, np.nan, dtype="float32")
    bare = ndvi_arr < ndvi_s
    full = ndvi_arr >= ndvi_v
    mix = ~bare & ~full & ~np.isnan(ndvi_arr)

    ems[bare] = eps_soil
    ems[full] = eps_veg

    pv = np.clip((ndvi_arr[mix] - ndvi_s) / (ndvi_v - ndvi_s), 0, 1) ** 2
    d_eps = 0.0038 * pv * (1 - pv) * 4
    ems[mix] = eps_soil * (1 - pv) + eps_veg * pv + d_eps

    return ems

def water_mask_from_bnr(multispectral_arr, blue_band=2, red_band=0, #band order specific for Altum-PT
                         threshold=-0.05, erode=True):
    B = multispectral_arr[blue_band].astype("float32")
    R = multispectral_arr[red_band].astype("float32")

    bnr = ((B - R) / (B + R + 1e-6)).astype("float32")

    water_mask = bnr > threshold
    if erode:
        water_mask = ndimage.binary_erosion(water_mask, structure=np.ones((5, 5)))

    return water_mask.astype(bool), bnr

def correct_brightness_to_lst(tb_celsius, emissivity_arr, t_amb_k):
    tb_k = tb_celsius + 273.15
    ts_k = ((tb_k ** 4 - (1 - emissivity_arr) * t_amb_k ** 4) / emissivity_arr) ** 0.25
    return ts_k - 273.15 #degrees C