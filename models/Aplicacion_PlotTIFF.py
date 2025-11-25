import rasterio
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--date", required=True, type=str, help="Fecha del producto a descargar (YYYY-MM-DD)")
parser.add_argument("--input", required=True, help="Directorio donde están los TIFFs generados a partir de CSVs")
parser.add_argument("--output", required=True, help="Directorio donde se guardan los png generados")
parser.add_argument("--colormap", required=True, help="Fichero con el colormap a utulizar")
args = parser.parse_args()

date = args.date

# Leer y parsear el archivo del colormap
colormap_path = args.colormap

depths = ["0_1", "1_2", "2_3", "3_4"]
for depth in depths:

    colors = []
    boundaries = []
    labels = ["0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9", "1.0", "1.2", "1.4", "1.6", "1.8", "2.0", "2.4", "2.8", "3.2", "3.6", "4.0", "4.5", "5.0", "6.0", "8.0", "10.0", "12.0", "15.0", "18.0", "24.0", "30.0"]

    with open(colormap_path, "r") as f:
        for line in f:
            if line.startswith("#") or "INTERPOLATION" in line:
                continue

            parts = line.strip().split(",")
            if len(parts) < 6:
                continue

            value = float(parts[0])
            r, g, b, a = [int(p) for p in parts[1:5]]
            label = parts[5].strip()

            boundaries.append(value)
            colors.append((r / 255, g / 255, b / 255, a / 255))
            #labels.append(label)

    # Crear colormap y norm
    custom_cmap = ListedColormap(colors)
    norm = BoundaryNorm(boundaries, custom_cmap.N)

    # Calcular ubicación de los ticks como puntos medios entre boundaries
    tick_locs = [(boundaries[i] + boundaries[i + 1]) / 2 for i in range(len(boundaries) - 1)]
    tick_labels = labels[:-1]  # Último valor ("inf") normalmente no se etiqueta
    # print(tick_locs)
    # print(tick_labels)

    with rasterio.open(f'{args.input}{date}_chl_map_{depth}.tif') as src:
        data = src.read(1)

    # === Crear figura ===
    fig, ax = plt.subplots(figsize=(8, 6))  # Tamaño ajustado para un solo plot

    # === Mostrar la imagen con colormap personalizado ===
    im = ax.imshow(data, cmap=custom_cmap, norm=norm)
    #ax.set_title('chl_pred_0_1')

    # Para que el colorbar solamente se vea en la última figura y no se repita cuatro veces
    if depth == "3_4":
        # === Añadir colorbar ===
        cb = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cb.set_ticks(tick_locs)
        cb.set_ticklabels(tick_labels)
        cb.ax.tick_params(labelsize=13)

        # === Título encima del colorbar ===
        cb.ax.text(0.5, 1.02, "Chl mg/m³", fontsize=14, ha='center', va='bottom', transform=cb.ax.transAxes)

    # === Ocultar ejes ===
    ax.axis('off')

    # === Mostrar y guardar ===
    plt.tight_layout()
    plt.savefig(f'{args.output}{date}_chl_map_{depth}.png', dpi=300, bbox_inches='tight')
    plt.show()
