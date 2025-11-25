import pandas as pd
import numpy as np
import rasterio
from rasterio.transform import from_origin
import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--date", required=True, type=str, help="Fecha del producto a descargar (YYYY-MM-DD)")
parser.add_argument("--input", required=True, help="Directorio donde están las predicciones para la fecha de interés")
parser.add_argument("--output", required=True, help="Directorio donde se guardan los TIFFs")
args = parser.parse_args()

path = args.input
date = args.date
filename = f"{date}_pred.csv"
df = pd.read_csv(os.path.join(path, filename))

depths = ["0_1", "1_2", "2_3", "3_4"]
for depth in depths:

    print(f"Generating TIFF file for {date} in depth {depth}")
    value_column = f'Chl_pred_{depth}'

    lats = np.sort(df['Latitude'].unique())[::-1]
    lons = np.sort(df['Longitude'].unique()) 

    data = np.full((len(lats), len(lons)), np.nan, dtype=np.float32)

    lat_idx = {lat: i for i, lat in enumerate(lats)}
    lon_idx = {lon: i for i, lon in enumerate(lons)}
    for _, row in df.iterrows():
        i = lat_idx[row['Latitude']]
        j = lon_idx[row['Longitude']]
        data[i, j] = row[value_column]

    pixel_size_lat = abs(lats[1] - lats[0]) if len(lats) > 1 else 0.01
    pixel_size_lon = abs(lons[1] - lons[0]) if len(lons) > 1 else 0.01
    transform = from_origin(lons[0] - pixel_size_lon/2, lats[0] + pixel_size_lat/2, pixel_size_lon, pixel_size_lat)

    with rasterio.open(
        f'{args.output}{date}_chl_map_{depth}.tif',
        'w',
        driver='GTiff',
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype='float32',
        crs='EPSG:32630',
        transform=transform,
        nodata=np.nan
    ) as dst:
        dst.write(data, 1)