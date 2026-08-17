import numpy as np
import pandas as pd

CP_AIR = 1013 #J/kg/K specific heat of moist air at constant pressure
R_DRY = 287.05 #J/kg/K gas constant for dry air
VON_KARMA = 0.41 # von Karman onstatn
GRAV = 9.81 #m/s2
STEFAN_BOLTZMANN = 5.670374e-8
#coefficients taken from Tetens formula
ES_0 = 0.6108 #kPa saturation vapour pressure at 0 degrees Celsius
ES_A = 17.27 #empirical fit coefficient
ES_B = 237.3 #degrees Celsius, empirical coefficient

def saturation_vapour_pressure(Ta_C):
    Ta_C = np.asarray(Ta_C)
    svp = ES_0 * np.exp(ES_A * Ta_C / (Ta_C + ES_B)) #from Tetens formula from that one slide deck sent in 2024
    return svp

def actual_vapour_pressure(Ta_C, RH_pct):
    avp = saturation_vapour_pressure(Ta_C) * np.asarray(RH_pct) / 100
    return avp

def get_air_properties(Ta_C, RH_pct, P_hPa):
    P_kPa = np.asarray(P_hPa) / 10
    Ta_C = np.asarray(Ta_C)

    es = saturation_vapour_pressure(Ta_C)
    ea = actual_vapour_pressure(Ta_C, RH_pct)
    vpd = es - ea
    delta = (ES_A * ES_B) * es / (Ta_C + ES_B) ** 2
    lam = (2.501 - 0.002361 * Ta_C) * 1e6
    gamma = CP_AIR * P_kPa / (0.622 * lam)

    #moist air is lighter than dry air at equal P, T
    Tv = (Ta_C + 273.15) / (1 - 0.378 * ea / P_kPa)
    rho = P_kPa * 1000 / (R_DRY * Tv)

    properties = {"es": es, "ea": ea, "vpd": vpd, "delta": delta, "lam": lam,
                  "gamma": gamma, "rho": rho, "rho_cp": rho * CP_AIR, "Ta_K": Ta_C + 273.15}
    return properties

def bowen_ratio(T_low, RH_low, T_high, RH_high, gamma):
    """
    Bowen ratio from two-height gradients.

        beta = gamma * dT / de

    gamma must be in kPa/K and match vapour pressures
    """
    e_low = actual_vapour_pressure(T_low, RH_low)
    e_high = actual_vapour_pressure(T_high, RH_high)

    dT = np.asarray(T_high, float) - np.asarray(T_low, float)
    de = e_high - e_low

    beta = np.asarray(gamma, float) * dT / de
    guard_my_denominator = ((np.abs(de) < 0.01) | ((beta > -1.2) & (beta < -0.8)))

    beta = np.where(guard_my_denominator, np.nan, beta)

    bowen_ratio_result = {"beta": beta, "dT": dT, "de": de}
    return bowen_ratio_result

def breb_fluxes(beta, Rn, G):
    """
    Split measured available energy using the Bowen ratio.
    """
    energy = np.asarray(Rn) - np.asarray(G)
    beta = np.asarray(beta, float)

    LE = energy / (1 + beta)
    H = energy - LE
    EF = 1 / (1 + beta)        
    
    breb_fluxes = {"H": H, "LE": LE, "EF": EF, "energy": energy}
    return breb_fluxes

def bowen_from_meteo(met, t_low='rvt81_temp_0_3m', rh_low='rvt81_rh_0_3m', t_high='rvt81_temp_2m', rh_high='rvt81_rh_2m',
                     p_col='air_pressure', rn_col='nr_lite2_net_radiation', g_col='hukseflux_heat_flux', **kwargs):
    """
    Bowen ratio and BREB fluxes for a whole weather station DataFrame.

    gamma is recomputed per record from that record's Ta and P rather than
    held at a flight-mean value, because both drift through the day

    Returns a DataFrame.
    """
    air = get_air_properties(met[t_high], met[rh_high], met[p_col])
    b = bowen_ratio(met[t_low], met[rh_low], met[t_high], met[rh_high], air['gamma'], **kwargs)
    f = breb_fluxes(b['beta'], met[rn_col], met[g_col])

    bowen = pd.DataFrame({'beta': b['beta'], 'dT': b['dT'], 'de': b['de'], 'H_breb': f['H'], 'LE_breb': f['LE'],
                         'energy': f['energy'], 'gamma': air['gamma']}, index=met.index)
    return bowen

def psi_m(zeta):
    zeta = np.asarray(zeta)
    x = (1 - 16 * np.clip(zeta, None, 0)) ** 0.25
    unstable = (2 * np.log((1 + x) / 2) + np.log((1 + x**2) / 2) - 2 * np.arctan(x) + np.pi / 2)
    psi_m = np.where(zeta < 0, unstable, -5 * zeta)
    return psi_m

def obukhov_from_station(H, u, Ta_K, rho_cp, z_u=2, h_c=0.15, n_iter=5, ustar_min=0.01):
    """
    Obukhov length from the weather stations's measured sensible heat flux.

        L = -rho_cp * ustar^3 * Ta_K / (k * g * H)

    Normally L and H must be solved together and the iteration is fragile,
    because each depends on the other. Here H comes from the Bowen
    measurement and is fixed, so only ustar (wind speed) iterates.
    """
    H = np.asarray(H)
    d0, z0m = 0.65 * h_c, 0.1 * h_c
    log_z = np.log((z_u - d0) / z0m)

    ustar = np.maximum(VON_KARMA * u / log_z, ustar_min) # neutral guess
    L = np.full(np.shape(ustar), np.inf, dtype=float)

    for _ in range(n_iter):
        L = -rho_cp * ustar**3 * Ta_K / (VON_KARMA * GRAV * H)
    L = np.where(np.abs(H) < 1, np.inf, L)
    zeta = (z_u - d0) / L
    ustar = np.maximum(VON_KARMA * u / (log_z - psi_m(zeta) + psi_m(z0m / L)), ustar_min)
    
    return L, ustar