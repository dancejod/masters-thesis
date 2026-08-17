"""
This script contains functions for handling weather station data.
"""
import pandas as pd
import requests
import numpy as np
import json
from modules.utils import load_flight_window, select_flight_records

def load_meteo_data(date, meteo_dir):
    path = f"{meteo_dir}/{date}.parquet"
    df = pd.read_parquet(path)
    if 'timestamp' in df.columns and 'datetime' not in df.columns:
        df = df.rename(columns={'timestamp': 'datetime'})
    
    #if 'ws200_wind_speed' in df.columns:
    #    df['ws200_wind_speed'] = df['ws200_wind_speed'].where(
    #        df['ws200_wind_speed'] < 50)
    return df

def download_chmu_metadata(yyyymm):
    #month = str(yyyymm)[4:6]
    url = f"https://opendata.chmi.cz/meteorology/climate/historical/metadata/meta1.json"
    r = requests.get(url)
    js = r.json()

    d = js["data"]["data"]
    meta = pd.DataFrame(d["values"], columns=d["header"].split(","))
    return meta
    
def get_chmu_station_wsi(station_id, yyyymm):
    meta = download_chmu_metadata(yyyymm)
    matches = meta[meta["FULL_NAME"] == station_id]
    if matches.empty:
        raise ValueError(f"Station {station_id} not found in CHMU metadata for {yyyymm}, reconsider your pitiful efforts")
    
    match = matches["WSI"].values[0]
    return match

def download_chmu_10min(yyyymm, wsi='0-203-0-11633', date_filter=None): #hardcoded the Lucni Bouda WSI here
    year = str(yyyymm)[:4]
    url = f"https://opendata.chmi.cz/meteorology/climate/historical/data/10min/{year}/10m-{wsi}-{yyyymm}.json"
    print(url)
    r = requests.get(url)
    js = json.loads(r.content.decode("utf-8-sig")) #utf-8-sig is important here because I had issues with BOM
    sd = pd.DataFrame(js["data"]["data"]["values"],
                      columns=js["data"]["data"]["header"].split(","))
    sd["DT"] = pd.to_datetime(sd["DT"]).dt.tz_localize(None)
    if date_filter:
        sd = sd[sd["DT"].dt.strftime('%Y%m%d') == str(date_filter)]
    a = sd.pivot(index="DT", columns="ELEMENT", values="VAL")
    a.columns.name = None
    for col in a.columns:
        a[col] = pd.to_numeric(a[col], errors='coerce')
    return a

def get_flight_tamb(date, meteo_dir="data/ancillary/weather", buffer_min=10, temp_col="rvt81_temp_2m"):

    t_start, t_end = load_flight_window(date)

    weather_data = load_meteo_data(date, meteo_dir)
    weather_start = select_flight_records(weather_data, t_start, t_end, buffer_min=buffer_min)

    if weather_start.empty:
        raise ValueError(f"No weather records within +-{buffer_min} min of flight {t_start} - {t_end} in {meteo_dir}/{date}.parquet")

    t_amb_celsius = float(weather_start[temp_col].mean())
    t_amb_kelvin  = t_amb_celsius + 273.15
    return t_amb_celsius, t_amb_kelvin, t_start, t_end

def weather_station_buffer_median(arr, x, y, radius=8):
    median_from_buffer = np.nanmedian(arr[y-radius:y+radius-1, x-radius:x+radius+1])
    return median_from_buffer