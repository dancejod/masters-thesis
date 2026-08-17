import numpy as np
import rasterio as rio
import json

STEFAN_BOLTZMANN = 5.670374e-8

def incoming_longwave(Ta_K, ea_kPa):
    """
    Downwelling longwave [W/m2] from air temperature and humidity.
    Sky emissivity taken from Brutsaert (1975) emis_sky = 1.24*(ea/Ta)^(1/7)
    where ea is in hPa. Returns a scalar.
    """
    ea_hPa = np.asarray(ea_kPa) * 10
    emis_sky = 1.24 * (ea_hPa / Ta_K) ** (1/7)
    Rl_down = emis_sky * STEFAN_BOLTZMANN * (Ta_K **4)
    return Rl_down

def net_radiation(Ts_C, albedo, emis, incoming_shortwave, incoming_longwave):
    """
    Net radiation [W/m2].
    Rn = (1-a)*incoming_shortwave + e*incoming_longwave - e*sigma*Ts^4

    Terms:
        - (1-a)*Rs_down: absorbed shortwave
        - e*Rl_down:     absorbed longwave from the sky
        - e*sigma*Ts^4   emitted longwave, sigma is Stefan Boltzmann constant
    """
    Ts_K = np.asarray(Ts_C) + 273.15
    net_radiation = (1 - albedo) * incoming_shortwave + emis * incoming_longwave - emis * STEFAN_BOLTZMANN * Ts_K ** 4
    return net_radiation

def ground_heat(Rn, water, c_land=0.15, c_water=0.3):
    """
    Soil heat flux [W/m2] as a fraction of net radiation.

    G = c * Rn

    Not exactly proper for peatlads?, TODO: investigate this (the use of constant)
    """
    G = np.where(water, c_water, c_land) * Rn
    return G

def calc_c_land(G_measured, Rn_station):
    """
    Anchor the land G fraction to the weather station.
    """
    c = float(G_measured) / float(Rn_station)

    return c

def sensible_heat(Ts_C, Ta_C, ra, rho_cp):
    """
    Sensible heat flux [W/m2].

    H = rho_cp * (Ts - Ta) / ra
    """
    H = rho_cp * (np.asarray(Ts_C) - np.asarray(Ta_C)) / np.asarray(ra)
    return H

def run_oseb(lst, surface, air_properties, air_temp, energy_fluxes):
    """
    Run OSEB model.
    """
    Rn = net_radiation(lst, surface['albedo'], surface['emis'], energy_fluxes['Rs'], energy_fluxes['Rl'])
    G = ground_heat(Rn, surface['water'], c_land=calc_c_land(energy_fluxes['G_station'], energy_fluxes['Rn_station']))
    H = sensible_heat(lst, air_temp, surface['ra'], air_properties['rho_cp'])
    LE = Rn - G - H
    LE = np.where(surface['valid'], LE, np.nan)
    oseb_stack = {"Rn":Rn, "G":G, "H":H, "LE":LE, "ET":LE/air_properties['lam']*3600}

    return oseb_stack

def save_et_stack(path, layers, profile, context=None):
    prof = profile.copy()
    prof.update(count=len(layers), dtype='float32', nodata=np.nan, compress='deflate')
    with rio.open(path, 'w', **prof) as dst:
        for i, (n, a) in enumerate(layers.items(), 1):
            dst.write(np.asarray(a, dtype='float32'), i)
            dst.set_band_description(i, n)
        if context:
            dst.update_tags(ET_CONTEXT=json.dumps(context))
    return path