from sentinelhub import SentinelHubCatalog, DataCollection, SHConfig, CRS, BBox
from datetime import datetime, timedelta
#import configparser
import requests
import os
import argparse
import csv
import yaml



parser = argparse.ArgumentParser()
parser.add_argument("--startdate", required=True)
parser.add_argument("--enddate", required=True)
parser.add_argument("--config", default="config.yaml")
args = parser.parse_args()

start_date = datetime.strptime(args.startdate, "%Y-%m-%d")
end_date = datetime.strptime(args.enddate, "%Y-%m-%d")

with open(args.config, "r") as f:
    cfg = yaml.safe_load(f)

date_dir = cfg.get('available_dates_dir')
area_of_interest = cfg.get("area_of_interest")

## Function to retrieve access token
def get_access_token(username: str, password: str) -> str:
    data = {
        "client_id": "cdse-public",
        "username": username,
        "password": password,
        "grant_type": "password",
    }
    try:
        r = requests.post(
            "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
            data=data,
        )
        r.raise_for_status()
        access_token = r.json().get("access_token")
        if not access_token:
            raise ValueError("No access token found in response.")
        return access_token
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None


CLIENT_ID = os.getenv("CDS_ID")
CLIENT_SECRET = os.getenv("CDS_SECRET")

config = SHConfig()
config.sh_client_id = CLIENT_ID
config.sh_client_secret = CLIENT_SECRET
config.sh_token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token" # Is it required?
config.sh_base_url = "https://sh.dataspace.copernicus.eu"
config.save("cdse")
config = SHConfig("cdse")

def check_cloud_cover(time_interval, aoi, config): 
    # Definir el área de interés
    aoi_bbox = BBox(bbox=aoi, crs=CRS.WGS84)

    # Inicializar el catálogo
    catalog = SentinelHubCatalog(config=config)
    date_range = time_interval[0], time_interval[1]

    # Buscar imágenes en el intervalo de fechas
    search_iterator = catalog.search(
        DataCollection.SENTINEL2_L1C,
        bbox=aoi_bbox,
        time=date_range,
        fields={"include": ["id", "properties.eo:cloud_cover", "properties.platform"], "exclude": ["properties.datetime"]},
    )
    results = list(search_iterator)

    # Filtrar resultados únicos por ID
    unique_results = {}
    for item in results:
        acquisition_id = item['id'].split('_T')[0]
        if acquisition_id not in unique_results:
            unique_results[acquisition_id] = item


    item_data = []
    # Mostrar la nubosidad por fecha
    for item in unique_results.values():
        image_id = item['id']
        date = datetime.strptime(image_id.split('_')[2][:8], "%Y%m%d").date()
        cloud_cover = item["properties"]["eo:cloud_cover"]

        item_data.append({
            "date": date.strftime("%Y-%m-%d"),
            "cloud_cover": cloud_cover,
            "platform": item["properties"].get("platform", "UNKNOWN")

        })
    return item_data


slots = []
current_start = start_date

while current_start <= end_date:
    current_end = min(current_start + timedelta(days=1), end_date)
    slots.append((
        current_start.strftime("%Y-%m-%d"),
        current_end.strftime("%Y-%m-%d")
    ))
    current_start = current_end + timedelta(days=1)


csv_data = []
for time_interval in slots: 

    csv_data.append(check_cloud_cover(
        time_interval=time_interval,
        aoi= area_of_interest,  # Example coordinates (W, S, E, N) # Whole tile is [-1.862, 36.935, -0.645, 37.942] || Our AOI: [-0.86, 37.65, -0.74, 37.8]
        config=config
    ))

# Aplanar la lista de listas (eliminar niveles intermedios)
csv_data = [item for sublist in csv_data for item in sublist if sublist]

# Guardar los resultados en CSV
csv_path = os.path.join(date_dir, 'available_dates.csv')
os.makedirs(os.path.dirname(csv_path), exist_ok=True)

with open(csv_path, 'w', newline='') as csvfile:
    fieldnames = ['date', 'cloud_cover', 'platform']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(csv_data)

print(f"\nFechas disponibles para el periodo [{start_date.date()} - {end_date.date()}]:\n")
for d in csv_data:
    print(f"{d['date']} - Cloud cover: {d['cloud_cover']}%")