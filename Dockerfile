FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PATH="/opt/snap/bin:/usr/local/bin:${PATH}"

# === Dependencias de sistema ===
RUN apt-get update && apt-get install -y \
    wget curl unzip build-essential \
    libssl-dev libffi-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev \
    openjdk-11-jdk gdal-bin tk-dev liblzma-dev \
    && apt-get clean


# === Instalar Python 3.8.5 desde fuente ===
WORKDIR /tmp
RUN wget https://www.python.org/ftp/python/3.8.5/Python-3.8.5.tgz && \
    tar -xf Python-3.8.5.tgz && cd Python-3.8.5 && \
    ./configure --enable-optimizations && \
    make -j"$(nproc)" && make altinstall && \
    ln -sf /usr/local/bin/python3.8 /usr/bin/python3 && \
    ln -sf /usr/local/bin/pip3.8 /usr/bin/pip3 && \
    cd .. && rm -rf Python-3.8.5*

# === Instalar SNAP 11.0.0 ===
# RUN wget -O /tmp/snap_installer_11.sh "https://download.esa.int/step/snap/11.0/installers/esa-snap_sentinel_linux-11.0.0.sh" && \
#     chmod +x /tmp/snap_installer_11.sh && \
#     /tmp/snap_installer_11.sh -q -dir /opt/snap && \
#     rm /tmp/snap_installer_11.sh

# === Instalar SNAP 12.0.0 ===
RUN wget -O /tmp/snap_installer_12.sh "https://download.esa.int/step/snap/12.0/installers/esa-snap_all_linux-12.0.0.sh" && \
    chmod +x /tmp/snap_installer_12.sh && \
    /tmp/snap_installer_12.sh -q -dir /opt/snap && \
    rm /tmp/snap_installer_12.sh

# === SNAP auxdata: Geoid EGM96 (ww15mgh) ===
RUN mkdir -p /root/.snap/auxdata/dem/egm96 && \
    wget -q -O /root/.snap/auxdata/dem/egm96/ww15mgh_b.zip \
        http://step.esa.int/auxdata/dem/egm96/ww15mgh_b.zip && \
    unzip -o /root/.snap/auxdata/dem/egm96/ww15mgh_b.zip \
        -d /root/.snap/auxdata/dem/egm96 && \
    rm /root/.snap/auxdata/dem/egm96/ww15mgh_b.zip


# === Crear estructura del proyecto ===
WORKDIR /app
# Copiar y instalar dependencias de Python
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copiar scripts y configuración del proyecto
COPY fetch/ ./fetch/
COPY models/ ./models/
COPY run_pipeline.py .
COPY config.yaml .
COPY data/ ./data/
COPY check_dates.py .

# Carpeta en la que se guardarán los resultados
RUN mkdir -p /app/data/Chl_Maps
# Persistencia en esta carpeta
VOLUME ["/app/data/Chl_Maps"]

# Variables SNAP opcionales (por si lo usas luego)
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV SNAP_JAVA_OPTS="--add-opens java.base/java.lang=ALL-UNNAMED"
RUN mkdir -p /root/.snap

# Comando por defecto
ENTRYPOINT ["/bin/bash"]
