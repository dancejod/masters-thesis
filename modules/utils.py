"""
This script contains general functions used across the notebooks.
"""
import pandas as pd
import numpy as np
import matplotlib as mpl
from pathlib import Path
from datetime import timedelta
from rasterio.warp import reproject, Resampling

def load_flight_window(date, csv='data/ancillary/flight_windows.csv'):
    df = pd.read_csv(csv, parse_dates=['t_start', 't_end'])
    row = df.loc[df['date'].astype(str) == str(date)].iloc[0]
    w = row['t_start'].to_pydatetime(), row['t_end'].to_pydatetime()
    return w

def select_flight_records(met, t_start, t_end, buffer_min=0):
    time_col = 'datetime' if 'datetime' in met.columns else 'timestamp'
    met = met.copy()
    met[time_col] = pd.to_datetime(met[time_col])

    buf = timedelta(minutes=buffer_min)
    window = met[(met[time_col] >= t_start - buf) & (met[time_col] <= t_end + buf)]

    if window.empty:
        return None
    return window

def load_calibration_parquet(date, data_dir, v2=False):
    path = Path(data_dir) / f"{date}_calibration_df{'' if v2 == False else '_v2'}.parquet" #v2 deprecated, for testing
    df = pd.read_parquet(path)
    return df

def aggregate_calibration_data(df):
    df_agg = (df.groupby(["tcp_name", "timestamp", "pt100_temperature"], as_index=False)
                .agg(img_temperature=("img_temperature", "mean"),
                     n_images=("img_temperature", "count")))
    df_agg["temperature_diff"] = df_agg['pt100_temperature'] - df_agg['img_temperature']
    
    return df_agg

def build_color_map(tcp_names):
    plates = sorted([t for t in tcp_names if t.endswith('_plate')])
    waters = sorted([t for t in tcp_names if t.endswith('_water')])

    cmap_plates = mpl.colormaps['Dark2']
    cmap_waters = mpl.colormaps['Blues']

    color_map = {t: cmap_plates(i % 10) for i, t in enumerate(plates)}
    color_map.update({t: cmap_waters(v) for t, v in zip(waters, np.linspace(0.4, 0.9, max(len(waters), 1)))})
    return color_map

def reproject_to_grid(source, src_transform, src_crs, ref_shape, ref_transform, ref_crs, resampling=Resampling.bilinear):
    if source.ndim == 2:
        dst = np.empty(ref_shape, dtype="float32")
    else:
        dst = np.empty((source.shape[0], *ref_shape), dtype="float32")

    reproject(
        source=source.astype("float32"),
        destination=dst,
        src_transform=src_transform,
        src_crs=src_crs,
        dst_transform=ref_transform,
        dst_crs=ref_crs,
        resampling=resampling,
    )
    return dst

def retrieve_canopy_height(dsm, dtm, hmax=1, smooth_m = 2, pixel_size=0.06):
    from scipy.ndimage import uniform_filter
    chm = np.clip(dsm - dtm, 0, hmax)
    if smooth_m:
        k = max(1, int(round(smooth_m / pixel_size)))
    chm = uniform_filter(np.nan_to_num(chm, nan=0), size=k)
    h = np.where(np.isfinite(dsm), chm, np.nan)
    return h

def read_tcp_utm(path, transform_obj, sep=';'):
    df = pd.read_csv(path, sep=sep, header=None, names=['tcp', 'x', 'y', 'z'])
    df['x'] = -df['x'].abs()
    df['y'] = -df['y'].abs()
    df['x'], df['y'] = transform_obj.transform(df['x'].values, df['y'].values)
    return df[['tcp', 'x', 'y', 'z']]

def fit_plane(pts, transform, shape, resid_reject=0.2):
    def thank_you_prof_jezek(mask):
        A = np.column_stack([np.ones(mask.sum()), x[mask] - x0, y[mask] - y0])
        coef, *_ = np.linalg.lstsq(A, z[mask])
        return coef
    x, y, z = pts['x'].values, pts['y'].values, pts['z'].values
    x0, y0 = x.mean(), y.mean()

    mask = np.ones(len(z), bool)
    for _ in range(5):
        coef = thank_you_prof_jezek(mask)
        pred = coef[0] + coef[1] * (x - x0) + coef[2] * (y - y0)
        resid = z - pred
        updated = resid < resid_reject
        if updated.sum() == mask.sum():
            break
        mask = updated

    pred = coef[0] + coef[1] * (x - x0) + coef[2] * (y - y0)
    rmse = np.sqrt(np.mean((z[mask] - pred[mask]) ** 2))
    print(f'Ground plane: 5 points used, RMSE {rmse} m') #hardcoded

    T = transform
    ny, nx = shape
    cols, rows = np.meshgrid(np.arange(nx), np.arange(ny))
    Xg = T.c + (cols + 0.5) * T.a + (rows + 0.5) * T.b
    Yg = T.f + (cols + 0.5) * T.d + (rows + 0.5) * T.e
    plane = coef[0] + coef[1] * (Xg - x0) + coef[2] * (Yg - y0)
    return plane