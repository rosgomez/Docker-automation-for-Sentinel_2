# Docker for automatic map generation

A Docker container has been created to automate the entire map generation process, requiring only a date as a parameter. The image was generated for Linux.

## User Guide

In a terminal, from the directory where the Dockerfile and folder structure are located, build the image with:
```
docker build -t chlpipeline .
```
The `-t` flag (tag) assigns a label to the image. The `.` specifies the build directory, and using the dot means it will use the current directory. The assigned label is `chlpipeline`.
 If this is the first time building the image, it will take a while because it must download all the software and Python requirements. For later builds, since Docker uses layers, only the parts of the Dockerfile that have changed will be rebuilt.

To run the container:
```
  docker run -it --rm \
  --env-file .env \
  -v "$(pwd)/data/Chl_Maps":/app/data/Chl_Maps \
  chlpipeline
```
- `docker run` creates and runs a new container from the `chlpipeline` image.
   The `-i` flag stands for *interactive*, keeping the standard input (stdin) open even if no terminal is attached. The `-t` flag allocates a terminal (tty) to the container so it can be used like a shell.  `--rm` automatically removes the container once execution is finished.
- `--env-file` loads environment variables into the container, in this case from a `.env` file.
   This file contains the credentials for [S3](https://eodata-s3keysmanager.dataspace.copernicus.eu/), used to download images from the ESA, as well as client id and secret to check cloud coverage, obtained from [Copernicus](https://shapps.dataspace.copernicus.eu/dashboard/#/account/settings), in the OAuth clients section.
   It includes the access and secret keys:
  - `S3_ACCESS_KEY=...`
  - `S3_SECRET_KEY=...`
  - `CDS_ID=...`
  - `CDS_SECRET=...`
     These variables can be accessed inside the container with `echo $VARIABLE`.
  
- `-v` mounts volumes, where `$(pwd)/data/Chl_Maps` is the path on the local machine (with `pwd` pointing to the current directory), and `/app/data/Chl_Maps` is the path inside the container.
   This links the folder inside the container with the corresponding local folder.

Once inside the container, the terminal prompt will look something like `root@5f29d3e806ac:/app#`. From there, simply run:

```
python3 run_pipeline.py --date 2022-07-14
```
The only parameter that needs to be specified is the desired date, formated as `%Y-%m-%d`.

It is recommended to check that the area of interest is not cloud-covered on that date. For that purpose, the user can use another script, also within the container, like the following:

```
python3 check_dates.py --startdate 2025-10-01 --enddate 2025-10-16
```

to check cloud coverage in a date interval. This consults the data catalog, but the properties specified there are not always accurate. Therefore, additional confirmation through visual inspection in the Copernicus Browser is also recommended.

## Description

**`Dockerfile`**
 The base image is Ubuntu 22.04. On top of it, several libraries are installed, along with Python 3.8.5 (used for all developments) and SNAP 12.0.0 (Updated from 11.0.0 on 22/10/2025 to support S2C). Then, the requirements are installed, and all scripts, configuration files, and trained models are copied into the image.

**`config.yaml`**
 Configuration file that contains the input/output paths for each script and the location of auxiliary files.

**`run_pipeline.py`**
 Script that takes the date provided by the user (via `--date`) and the parameters from `config.yaml`.
 It orchestrates the pipeline by calling several scripts:

- `productFetcher.py` and `productFetcher_tozip.py` to download the `.SAFE` product and compress it.
- `snap_batch_application.sh` to process the image with SNAP and produce a TIFF containing TOA reflectances and C2X-Complex processed data.
- `Aplicacion_Modelos.py` to perform inference on all image pixels at four depths and generate a CSV file with the predictions.
- `Aplicacion_TIFFfromCSV.py` to generate one TIFF per depth with the predicted Chl-a.
- `Aplicacion_PlotTIFF.py` to create a PNG from each TIFF and `Aplicacion_GenerateGif` to create a GIF.

​	Finally, the total execution time of the pipeline is displayed, which typically takes about 10–15 minutes per date.

**`check_dates.py`**

Script to obtain cloud cover over a date interval. Recommended to use before running the pipeline.

**`requirements.txt`**
 List of Python libraries used, installed during image creation.

**`/data`**
 Contains several folders where intermediate files generated throughout the process are stored. The final maps are located in **`/Chl_Maps`**.

**`/fetch`**
 Contains some of the scripts called by `run_pipeline.py` and other auxiliary files.

**`/models`**
 Contains the remaining scripts called by `run_pipeline.py` and the trained models used during the inference process.