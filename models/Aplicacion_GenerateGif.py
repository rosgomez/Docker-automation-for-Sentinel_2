import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.colors import ListedColormap, BoundaryNorm
from PIL import Image
import rasterio
import os
from matplotlib.colorbar import ColorbarBase
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--date", required=True, type=str, help="Fecha del producto a descargar (YYYY-MM-DD)")
parser.add_argument("--input", required=True, help="Directorio donde están los TIFFs generados a partir de CSVs")
parser.add_argument("--output", required=True, help="Directorio donde se guarda el gif generado")
parser.add_argument("--colormap", required=True, help="Fichero con el colormap a utilizar")
args = parser.parse_args()

date = args.date

# === Archivos tif a animar ===
tif_paths = [
    f'{args.input}{date}_chl_map_0_1.tif',
    f'{args.input}{date}_chl_map_1_2.tif',
    f'{args.input}{date}_chl_map_2_3.tif',
    f'{args.input}{date}_chl_map_3_4.tif'
]

# === Función para leer .tif como array ===
def read_tif_as_array(path):
    with rasterio.open(path) as src:
        return src.read(1)

# === Leer colormap personalizado desde .txt ===
def load_qgis_colormap(colormap_path):
    colors = []
    boundaries = []

    with open(colormap_path, "r") as f:
        for line in f:
            if line.startswith("#") or "INTERPOLATION" in line:
                continue
            parts = line.strip().split(",")
            if len(parts) < 6:
                continue
            value = float(parts[0])
            r, g, b, a = [int(p) for p in parts[1:5]]
            #label = parts[5].strip()
            boundaries.append(value)
            colors.append((r / 255, g / 255, b / 255, a / 255))

    cmap = ListedColormap(colors)
    norm = BoundaryNorm(boundaries, ncolors=len(colors))
    return cmap, norm, boundaries


# === Cargar datos ===
data_list = [read_tif_as_array(p) for p in tif_paths]

# === Cargar colormap personalizado ===
cmap, norm, boundaries = load_qgis_colormap(args.colormap)


# Ticks y etiquetas
tick_locs = [(boundaries[i] + boundaries[i+1]) / 2 for i in range(len(boundaries)-1)]
labels = ["0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9", "1.0", "1.2", "1.4", "1.6", "1.8", "2.0", "2.4", "2.8", "3.2", "3.6", "4.0", "4.5", "5.0", "6.0", "8.0", "10.0", "12.0", "15.0", "18.0", "24.0", "30.0"]
tick_labels = labels[:-1]

frames = []
for path, data in zip(tif_paths, data_list):
    depth_str = path.replace(f"{args.input}{date}_chl_map_", "").replace(".tif", "").replace("_", "-")

    fig, ax = plt.subplots(figsize=(8, 6))  # más ancho para que quepa la leyenda
    im = ax.imshow(data, cmap=cmap, norm=norm)
    ax.axis('off')

    # Texto con profundidad
    ax.text(-0.3, 0.9, f'Depth {depth_str}', color='white', fontsize=24, fontweight='bold',
            ha='left', va='top', transform=ax.transAxes,
            bbox=dict(facecolor='black', alpha=0.5, boxstyle='round,pad=0.3'))

    # Colorbar personalizado (leyenda)
    cbar_ax = fig.add_axes([0.75, 0.15, 0.03, 0.75])  # [left, bottom, width, height]
    cb = ColorbarBase(cbar_ax, cmap=cmap, norm=norm, boundaries=boundaries, ticks=tick_locs)
    cb.set_ticklabels(tick_labels)
    cb.ax.tick_params(labelsize=8)
    #cb.set_label("Chl mg/m³", fontsize=8, labelpad=5)
    cb.ax.text(0.5, 1.02, "Chl mg/m³", fontsize=10, ha='center', va='bottom', transform=cb.ax.transAxes)

    # Convertir a imagen
    #plt.tight_layout()
    canvas = FigureCanvas(fig)
    canvas.draw()
    img = np.frombuffer(canvas.buffer_rgba(), dtype=np.uint8)
    img = img.reshape(fig.canvas.get_width_height()[::-1] + (4,))
    img_rgb = img[..., :3]
    frames.append(Image.fromarray(img_rgb))
    plt.close(fig)

# Guardar el gif
frames[0].save(
    f'{args.output}{date}_chl_pred_loop.gif',
    save_all=True,
    append_images=frames[1:],
    duration=1000,
    loop=0
)