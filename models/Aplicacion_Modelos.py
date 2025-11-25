import pandas as pd
import os
import argparse
from Aplicacion_utils import *

parser = argparse.ArgumentParser()
parser.add_argument("--date", required=True, type=str, help="Fecha del producto a descargar (YYYY-MM-DD)")
parser.add_argument("--input", required=True, help="Directorio donde está el .tif procesado por SNAP")
parser.add_argument("--models", required=True, help="Directorio donde están los modelos para cada profundidad")
parser.add_argument("--pred", required=True, help="Directorio dondese guarda el csv con las predicciones")
parser.add_argument("--geojson", required=True, help="Fichero con geojson del Mar Menor")
args = parser.parse_args()

folder_path =args.input
polygon_path=args.geojson
# Hacer las fechas de una en una porque pesan mucho
date_str = str(args.date)
target_dates = [
    date_str
]

groupings = ["5x5", "9x9"]
net_set = ["C2X-Complex"]

for grouping in groupings:
    for net in net_set:
        df_tiffs = extract_pixels_in_marmenor(folder_path, target_dates, grouping, net, polygon_path)
        df_tiffs["Date"] = pd.to_datetime(df_tiffs["Date"])
        df_tiffs.to_csv(f"{folder_path}/df_tifs_{net}_{grouping}_{target_dates[0]}.csv", index=False)

print("DataFrames con reflectancias cargados")

# Cargamos los csv de los tifs
path = folder_path
dfs_tifs = {}
for archivo in os.listdir(path):
    if archivo.startswith("df_tifs_") and archivo.endswith(f"{target_dates[0]}.csv") and "planet" not in archivo:
        nombre_sin_extension = os.path.splitext(archivo)[0]  # sin .csv
        ruta_completa = os.path.join(path, archivo)
        # Guardamos el nombre del archivo sin la fecha
        dfs_tifs[nombre_sin_extension[:-11]] = pd.read_csv(ruta_completa)

# Limpiamos nulos
for nombre_df, df in dfs_tifs.items():
    for band_set in ["rhow", "rhown","rtoa"]:
        dfs_tifs[nombre_df] = df.dropna()

        # Dataframes con procesado C2X 5x5, C2X 9x9 y TOA 9x9
dfs_tifs_all = create_processed_dfs(dfs_tifs)

dfs = add_band_combinations(dfs_tifs_all)

for nombre_df, df in dfs.items():
    dfs[nombre_df] = compactar_prefijos_columnas(df)

dfs = add_season(dfs)

print("Dataframes con combinaciones de bandas y procesados")

carpeta_modelos = args.models

selection = {
    'C2X-Complex_rhow_9x9_depth_in_0_1': 'XGB',
    'C2X-Complex_rhow_9x9_depth_in_1_2': 'CAT',
    #'TOA_9x9_depth_in_2_3': 'KNN',
    'C2X-Complex_rhow_5x5_depth_in_2_3': 'CAT',
    'C2X-Complex_rhow_5x5_depth_in_3_4': 'RF',
}


df_out = pd.DataFrame(dfs["df_tifs_C2X-Complex_rhow_9x9"].loc[:, ["Date", "Latitude", "Longitude"]])

for dataset, model_name in selection.items():
    if model_name == "XGB":
        df_in = dfs["df_tifs_C2X-Complex_rhow_9x9"]
    
    elif model_name == "CAT" and dataset == "C2X-Complex_rhow_5x5_depth_in_2_3":
        df_in = dfs["df_tifs_C2X-Complex_rhow_5x5"]

    elif model_name == "CAT" and dataset == "C2X-Complex_rhow_9x9_depth_in_1_2":
        df_in = dfs["df_tifs_C2X-Complex_rhow_9x9"]

    elif model_name == "KNN":
        df_in = dfs["df_tifs_TOA_9x9"]

    elif model_name == "RF":
        df_in = dfs["df_tifs_C2X-Complex_rhow_5x5"]

    print(dataset, model_name)
    depth = dataset[-3:]
    df_out[f"Chl_pred_{depth}"] = predict_with_model(
                                    df=df_in,
                                    models_dir=carpeta_modelos,
                                    dataset_name=dataset,
                                    model_name=model_name,
                                    clip_min=0.2,
                                    strict=True
                                )
    
df_out.loc[:,["Date", "Latitude", "Longitude", "Chl_pred_0_1", "Chl_pred_1_2", "Chl_pred_2_3", "Chl_pred_3_4"]].to_csv(f"{args.pred}/{target_dates[0]}_pred.csv", index = False)