FROM mcr.microsoft.com/devcontainers/python:3.11-bullseye

# Actualizar e instalar dependencias adicionales
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    ffmpeg \
    python3-pip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instalar yt-dlp y otras dependencias de Python
# Nota: difflib es una biblioteca estándar de Python y no necesita instalarse
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Crear directorio para almacenar datos
RUN mkdir -p /workspaces/data

# Configurar zona horaria
ENV TZ=Europe/Madrid
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
