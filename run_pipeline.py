import argparse
import yaml
import os
import pandas as pd
import subprocess
import time
from datetime import datetime, timedelta
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--date")
parser.add_argument("--config", default="config.yaml")
parser.add_argument("-sd", "--startdate")
parser.add_argument("-ed", "--enddate")
parser.add_argument("--cloudcover", default='100.00')
parser.add_argument('-cd', '--configdates', action='store_true')
args = parser.parse_args()

with open(args.config, "r") as f:
    cfg = yaml.safe_load(f)

fecha = args.date
startdate = args.startdate
enddate = args.enddate
cloudcover = args.cloudcover
use_config_dates = args.configdates
safe_dir = cfg.get("safe_dir")
snap_dir = cfg.get("snap_dir")
model_dir = cfg.get("model_dir")
pred_dir = cfg.get("pred_dir")
map_dir = cfg.get("map_dir")
geojson_file = cfg.get("geojson_file")
colormap_file = cfg.get("colormap_file")
available_dates_dir = cfg.get("available_dates_dir")
config_dates = cfg.get("config_dates")

def get_filtered_dates(unfiltered_dates, min_cloud_cover):
    number_of_available_dates = len(unfiltered_dates)

    # Filtrar el dataframe por cloud_cover
    filtered_dates = unfiltered_dates[unfiltered_dates['cloud_cover'] <= min_cloud_cover].reset_index(drop=True)
    number_of_filtered_dates = len(filtered_dates)

    print(f"\nFechas cubiertas en un {min_cloud_cover}% o menos por las nubes:\n")
    for i, row in filtered_dates.iterrows():
        print(f"{row['date']} - Cloud cover: {row['cloud_cover']}%")
    
    # Fechas aprovechadas:
    fechas_aprovechadas = round((number_of_filtered_dates / number_of_available_dates) * 100, 2)

    # Dependiendo del porcentaje de fechas aprovechadas, el color será:
    reset = "\033[0m"
    color = ""
    if fechas_aprovechadas < 25:
        color = "\033[38;5;196m"    # ROJO
    elif fechas_aprovechadas < 50:
        color = "\033[38;5;208m"    # NARANJA
    elif fechas_aprovechadas < 75:
        color = "\033[38;5;226m"    # AMARILLO
    else:
        color = "\033[38;5;46m"     # VERDE
    

    print(f"\n{color}AVISO: {reset}está usted aprovechando {number_of_filtered_dates} de {number_of_available_dates} fechas disponibles. Es decir, un {color}{fechas_aprovechadas}%{reset} de las fechas disponibles.\n")
    
    # Devuelve la lista de fechas filtrada.
    return filtered_dates['date'].tolist()


# === [-1] Comprobación de integridad de los argumentos ===

# Si han puesto --configdates y pasan cualquier otro modo, catapúm
if use_config_dates and (fecha or startdate or enddate):
    print(use_config_dates)
    print("ERROR: Por favor, elija entre usar el modo de fecha única (--date $DATE), el modo de intervalo (--startdate $DATE --enddate $DATE) \
          o el modo de fechas concretas (--configdates)", file=sys.stderr)
    sys.exit(2)

# Si NO se están usando las fechas del config.yaml
if not use_config_dates:

    # Si han puesto --date y --startdate o --enddate a la vez, catapúm
    if fecha and (startdate or enddate):
        print("ERROR: Por favor, escoja una fecha concreta (--date $DATE) o un intervalo de fechas (--startdate $DATE --enddate $DATE), pero no ambas a la vez.", file=sys.stderr)
        sys.exit(2)

    # Si han puesto fecha de inicio pero no fecha final, y viceversa, catapúm
    if not fecha and not (startdate and enddate):
        print("ERROR: Por favor, seleccione una fecha de comienzo (--startdate $DATE) y otra de fin (--enddate $DATE) para el intervalo.", file=sys.stderr)
        sys.exit(2)

    # Si alguna de las fechas no está en formato correcto, catapúm
    if (fecha):
        try:
            datetime.strptime(fecha, "%Y-%m-%d")
        except ValueError:
            print("ERROR: La fecha está en un formato incorrecto. Use el formato YYYY-MM-DD (por ejemplo, 2022-07-15).", file=sys.stderr)
            sys.exit(2)
    else:
        try:
            datetime.strptime(startdate, "%Y-%m-%d")
        except ValueError:
            print("ERROR: La fecha de inicio está en un formato incorrecto. Use el formato YYYY-MM-DD (por ejemplo, 2022-07-15).", file=sys.stderr)
            sys.exit(2)

        try:
            datetime.strptime(enddate, "%Y-%m-%d")
        except ValueError:
            print("ERROR: La fecha de fin está en un formato incorrecto. Use el formato YYYY-MM-DD (por ejemplo, 2022-07-15).", file=sys.stderr)
            sys.exit(2)

        start = datetime.strptime(startdate, "%Y-%m-%d")
        end = datetime.strptime(enddate, "%Y-%m-%d")
        
        if end < start:
            print("ERROR: La fecha de fin debe ser posterior o igual a la fecha de inicio.", file=sys.stderr)
            sys.exit(2)

        for d in config_dates:
            try:
                datetime.strptime(d, "%Y-%m-%d")
            except ValueError:
                print(f"ERROR: la fecha {d} del archivo de configuración {args.config} está en un formato incorrecto.\
                    Use el formato YYYY-MM-DD (por ejemplo, 2022-07-15).", file=sys.stderr)
                sys.exit(2)

# Porcentaje de nubes
try:
    cloudcover = float(cloudcover)
except:
    print(f"ERROR: el valor '{cloudcover}' no es un float válido.", file=sys.stderr)
    sys.exit(2)

# === Decidimos ===

print("\nSeleccionando fechas disponibles para la descarga...\n")

dates = []

if fecha:
    dates.append(fecha)
elif use_config_dates:
    unfiltered_dates = pd.DataFrame(columns=['date', 'cloud_cover', 'platform'])
    missing_dates = []
    # Un poco pocho. Deberíamos ver la manera de evitar tener que estar escribiendo en disco todo el rato.
    for con_dat in config_dates:
        # Comprueba si la fecha está, pero no saca nada por pantalla
        with open(os.devnull, 'w') as devnull:
            subprocess.run(["python3", "check_dates.py", "--startdate", con_dat, "--enddate", con_dat], check=True, stdout=devnull, stderr=devnull)
        
        # Lee csv
        df = pd.read_csv(os.path.join(available_dates_dir, 'available_dates.csv'))

        # Añade fecha al df provisional
        if len(df):
            unfiltered_dates = pd.concat([unfiltered_dates, df.iloc[[0]]], ignore_index=True)
        else:
            missing_dates.append(con_dat)
    
    dates.extend(get_filtered_dates(unfiltered_dates=unfiltered_dates, min_cloud_cover=cloudcover))

    # No se han encontado un x% de las fechas proporcionadas en config.yaml
    if len(missing_dates):
        reset = "\033[0m"
        color = "\033[38;5;196m"    # Color Rojo
        nfiltered = len(dates)
        nmissing = len(missing_dates)
        missing_perc = round((nmissing / len(config_dates)) * 100, 2)

        print(f"\n{color}AVISO: {reset}un total de {nmissing} de las {len(config_dates)} fechas porporcionadas no se encuentran en la base de datos."
                        f" Es decir, un {color}{missing_perc}%{reset} de las fechas proporcionadas no se han encontrado:\n")

        for missing in missing_dates:
            print(f"{missing} - {color}MISSING IN DATABASE{reset}\n")

        print("Compruebe o elimine estas fechas manualmente, el proceso seguirá sin tenerlas en cuenta...")


else:
    start = datetime.strptime(startdate, "%Y-%m-%d")
    end = datetime.strptime(enddate, "%Y-%m-%d")
    
    #dates = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((end - start).days + 1)]
    

    # Correr check_dates
    subprocess.run(["python3", "check_dates.py", "--startdate", startdate, "--enddate", enddate], check=True)

    # Leer las fechas de available_dates.csv
    df = pd.read_csv(os.path.join(available_dates_dir, 'available_dates.csv'))
    dates.extend(get_filtered_dates(unfiltered_dates=df, min_cloud_cover=cloudcover))


print("\nCorriendo el pipeline...\n")

for d in dates:
    print(f"\nProcesando el día {d}")
    # === [0] Inicio del pipeline ===
    t_start = time.time()
    """
    print(f"\n=== [1] Descargando producto para {d} ===")
    t1 = time.time()
    subprocess.run(["python3", "fetch/productFetcher.py", "--date", d, "--output", safe_dir], check=True)
    try:
        subprocess.run(["python3", "fetch/productFetcher.py", "--date", d, "--output", safe_dir], check=True)
    except subprocess.CalledProcessError:
        print("No se encontraron productos para esa fecha. El pipeline se detendrá.")
        sys.exit(1)
    
    subprocess.run(["python3", "fetch/productFetcher_tozip.py", "--date", d, "--input", safe_dir], check=True)
    t2 = time.time()
    print(f"Tiempo transcurrido [1]: {t2 - t1:.2f} s")
    """
    print(f"\n=== [2] Aplicando corrección atmosférica con SNAP ===")
    t3 = time.time()
    subprocess.run(["python3", "fetch/snap_batch_application.py", d, safe_dir, snap_dir], check=True)
    t4 = time.time()
    print(f"Tiempo transcurrido [2]: {t4 - t3:.2f} s")
"""    


    print(f"\n=== [3] Ejecutando modelos de predicción ===")
    t5 = time.time()
    subprocess.run(["python3", "models/Aplicacion_Modelos.py", "--date", d, "--input", snap_dir, "--models", model_dir, "--pred", pred_dir, "--geojson", geojson_file], check=True)
    t6 = time.time()
    print(f"Tiempo transcurrido [3]: {t6 - t5:.2f} s")

    print(f"\n=== [4] Generando TIFFs ===")
    t7 = time.time()
    subprocess.run(["python3", "models/Aplicacion_TIFFfromCSV.py", "--date", d, "--input", pred_dir, "--output", map_dir], check=True)
    t8 = time.time()
    print(f"Tiempo transcurrido [4]: {t8 - t7:.2f} s")

    if cfg.get("plot_individuales", False):
        print(f"\n=== [5] Generando plots individuales ===")
        t9 = time.time()
        subprocess.run(["python3", "models/Aplicacion_PlotTIFF.py", "--date", d, "--input", map_dir, "--output", map_dir, "--colormap", colormap_file], check=True)
        t10 = time.time()
        print(f"Tiempo transcurrido [5]: {t10 - t9:.2f} s")

    if cfg.get("generate_gif", False):
        print(f"\n=== [6] Generando GIF ===")
        t11 = time.time()
        subprocess.run(["python3", "models/Aplicacion_GenerateGif.py", "--date", d, "--input", map_dir, "--output", map_dir, "--colormap", colormap_file], check=True)
        t12 = time.time()
        print(f"Tiempo transcurrido [6]: {t12 - t11:.2f} s")

    t_end = time.time()
    print("\n Pipeline completado correctamente.")
    print(f"Tiempo total del pipeline: {(t_end - t_start)/60:.2f} min")
"""
