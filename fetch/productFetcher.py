import boto3
import datetime
import os
import csv
import argparse
import sys
import yaml

parser = argparse.ArgumentParser()
parser.add_argument("--date", required=True, type=str, help="Fecha del producto a descargar (YYYY-MM-DD)")
parser.add_argument("--output", required=False, help="Directorio donde guardar el .SAFE")
parser.add_argument("--config", default="config.yaml")
args = parser.parse_args()

with open(args.config, "r") as f:
    cfg = yaml.safe_load(f)


# Credenciales y configuración de sesión
ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
SECRET_KEY = os.getenv("S3_SECRET_KEY")

if not ACCESS_KEY or not SECRET_KEY:
    raise EnvironmentError("No se encontraron los credenciales de S3 en el entorno o .env")

session = boto3.session.Session()
s3 = session.resource(
    's3',
    endpoint_url='https://eodata.dataspace.copernicus.eu',
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    region_name='default'
)

bucket = s3.Bucket("eodata")

date_str = str(args.date)
fechas_str = [
    date_str
]

fechas = [datetime.datetime.strptime(f, "%Y-%m-%d").date() for f in fechas_str]

# Tile ID a buscar
tile_id = cfg.get("tile")

# Prefijos base de búsqueda: L1C_N0500 o L1C
#prefixes = [f"Sentinel-2/MSI/L1C_N0500/{fecha.year}/{fecha.month:02d}/{fecha.day:02d}/" for fecha in fechas]
#prefixes = [f"Sentinel-2/MSI/L1C/{fecha.year}/{fecha.month:02d}/{fecha.day:02d}/" for fecha in fechas]

# Carpeta local destino
output_dir = args.output

prefix_patterns = [
    "Sentinel-2/MSI/L1C_N0500/{y}/{m:02d}/{d:02d}/",
    "Sentinel-2/MSI/L1C/{y}/{m:02d}/{d:02d}/"
]

def download_product(bucket, prefix: str, tile_id: str, target_root: str):
    """
    Busca y descarga un producto SAFE que contenga el tile_id en el prefijo dado.
    Devuelve el nombre del producto descargado o None si no se descarga nada.
    """
    found = False
    for obj in bucket.objects.filter(Prefix=prefix):

        # Buscar carpetas SAFE
        if obj.key.endswith('.SAFE/') and tile_id in obj.key:
            found = True
            product_prefix = obj.key
            product_name = os.path.basename(product_prefix.rstrip('/'))
            local_target = os.path.join(target_root, product_name)

            # Si ya está descargado, no repetir
            if os.path.exists(local_target):
                print(f"El producto {product_name} ya existe en {local_target}. Saltando descarga.")
                return None

            print(f"Producto encontrado: {product_prefix}")
            print(f"Descargando a {local_target}")

            # Descargar todos los archivos dentro del SAFE
            for file_obj in bucket.objects.filter(Prefix=product_prefix):
                local_path = os.path.join(local_target, os.path.relpath(file_obj.key, product_prefix))
                os.makedirs(os.path.dirname(local_path), exist_ok=True)

                # evitar carpetas virtuales
                if not file_obj.key.endswith('/'):
                    print(f"Descargando {file_obj.key} → {local_path}")
                    bucket.download_file(file_obj.key, local_path)

            return product_prefix

    if not found:
        print(f"No se encontró producto SAFE con tile {tile_id} en {prefix}")
    return None



def main():
    os.makedirs(output_dir, exist_ok=True)
    productos_encontrados = []

    for fecha in fechas:
        print(f"\nProcesando fecha {fecha.strftime('%Y-%m-%d')}")

        # probar cada patrón en orden
        for pattern in prefix_patterns:
            prefix = pattern.format(y=fecha.year, m=fecha.month, d=fecha.day)
            print(f"Buscando productos en: {prefix}")

            result = download_product(bucket, prefix, tile_id, output_dir)
            if result:
                productos_encontrados.append(result)
                break  # rompe el bucle interno si se encontró algo
        else:
            # Este else del for se ejecuta solo si NO se ejecutó 'break'
            print(f"No se encontró ningún producto para la fecha {fecha.strftime('%Y-%m-%d')} en ninguno de los prefijos.")

    if productos_encontrados:
        print(f"\nSe descargó el producto para la fecha buscada.")
        sys.exit(0)
    else:
        print("\nNo se descargó ningún producto.")
        sys.exit(1)


if __name__ == "__main__":
    main()
