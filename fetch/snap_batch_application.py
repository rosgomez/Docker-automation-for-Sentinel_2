#!/usr/bin/env python3
import os
import sys
import yaml
import subprocess

# ========================
# === Argumentos ========
# ========================

if len(sys.argv) != 4:
    print("Uso: python snap_batch_application.py <fecha> <input_dir> <output_dir>")
    sys.exit(1)

FECHA = sys.argv[1]
INPUT_DIR = sys.argv[2]
OUTPUT_DIR = sys.argv[3]

# ================================
# === Cargar config.yaml ========
# ================================

CONFIG_FILE = "/app/config.yaml"

with open(CONFIG_FILE, "r") as f:
    cfg = yaml.safe_load(f)

GRAPH_XML = cfg["batch_template"]["graph_xml"]
TEMPLATE_PARAMS = cfg["batch_template"]["template_params"]
GPT = cfg["batch_template"]["gpt_bin"]
output_format = cfg["batch_template"]["output_format"]
resample_resolution = cfg["batch_template"]["resampleResolution"]
geo_region = cfg["batch_template"]["geoRegion"]
salinity = cfg["batch_template"]["salinity"]
temperature = cfg["batch_template"]["temperature"]
net = cfg["batch_template"]["netSet"]
output_rtoa = cfg["batch_template"]["outputRtoa"]
output_ac_reflectance = cfg["batch_template"]["outputAcReflectance"]
output_rhown = cfg["batch_template"]["outputRhown"]
band_subset = cfg["batch_template"]["bandSubset"]



# ========================
# === Validaciones ======
# ========================

if not os.path.isdir(INPUT_DIR):
    print(f"No se encuentra el directorio de entrada: {INPUT_DIR}")
    sys.exit(1)

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ================================
# === Información inicial ========
# ================================

print(f"=== Ejecutando SNAP para la fecha: {FECHA} ===")
print(f"Input:  {INPUT_DIR}")
print(f"Output: {OUTPUT_DIR}")
print(f"Usando GPT en: {GPT}")

# ================================
# === Filtrado de productos ======
# ================================

FILTER_DATE = FECHA.replace("-", "")  # 2022-07-14 -> 20220714
FILTER_DATES = [FILTER_DATE]

if FILTER_DATES:
    print(f"Procesando las fechas: {FILTER_DATES}")
else:
    print("Procesando todos los archivos disponibles")

# ===============================
# === Procesar archivos SAFE ====
# ===============================

for filename in sorted(os.listdir(INPUT_DIR)):

    if not filename.endswith(".SAFE.zip"):
        continue
    print(f"Nombre: {filename}")
    input_file = os.path.join(INPUT_DIR, filename)

    parts = filename.split("_")
    if len(parts) < 3:
        print(f"Formato inesperado: {filename}, saltando...")
        continue

    datecode = parts[2][:8]
    base_name = filename.replace(".SAFE.zip", "")

    print(f"\n\n{filename}\n")

    # Filtrar por fecha
    if FILTER_DATES and datecode not in FILTER_DATES:
        print(f"Saltando {filename} (fecha {datecode} no en filtro)")
        continue

    # Selección de red
    if net == "C2X-COMPLEX-Nets":
        suffix = "C2XComplexNets"
    elif net == "C2X-Nets":
        suffix = "C2XNets"
    else:
        suffix = "C2RCCNets"

    output_file = os.path.join(
        OUTPUT_DIR,
        f"{base_name}_{suffix}_10m.{output_format}"
    )

    # ===========================
    # === Crear param file ======
    # ===========================

    param_file = f"/tmp/params_{datecode}.params"

    with open(TEMPLATE_PARAMS, "r") as f:
        template_lines = f.readlines()

    new_lines = []
    for line in template_lines:
        if line.startswith("inputFile="):
            new_lines.append(f"inputFile={input_file}\n")
            
        elif line.startswith("outputFile="):
            new_lines.append(f"outputFile={output_file}\n")
            
        elif line.startswith("outputFormat="):
            new_lines.append(f"outputFormat={output_format}\n")
            
        elif line.startswith("resampleResolution="):
            new_lines.append(f"resampleResolution={resample_resolution}\n")
            
        elif line.startswith("geoRegion="):
            new_lines.append(f"geoRegion={geo_region}\n")
            
        elif line.startswith("salinity="):
            new_lines.append(f"salinity={salinity}\n")
            
        elif line.startswith("temperature="):
            new_lines.append(f"temperature={temperature}\n")
            
        elif line.startswith("netSet="):
            new_lines.append(f"netSet={net}\n")
            
        elif line.startswith("outputRtoa="):
            new_lines.append(f"outputRtoa={output_rtoa}\n")
            
        elif line.startswith("outputAcReflectance="):
            new_lines.append(f"outputAcReflectance={output_ac_reflectance}\n")
            
        elif line.startswith("outputRhown="):
            new_lines.append(f"outputRhown={output_rhown}\n")
            
        elif line.startswith("bandSubset="):
            new_lines.append(f"bandSubset={band_subset}\n")
        
        else:
            new_lines.append(line)

    with open(param_file, "w") as f:
        f.writelines(new_lines)

    # ===========================
    # === Ejecutar GPT ==========
    # ===========================

    print(f"Procesando {filename} → {output_file}")
    print(f"param_file")
    print(f"GPT")
    print(f"GRAPH_XML")

    subprocess.run(
        [GPT, GRAPH_XML, "-p", param_file],
        check=True
    )

