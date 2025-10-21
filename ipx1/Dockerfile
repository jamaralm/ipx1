# Use uma imagem base oficial do Python
FROM python:3.10-slim-buster

# Defina variáveis de ambiente para o Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Crie o diretório de trabalho
WORKDIR /app

# Instale as dependências
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copie seu projeto para dentro do container
COPY . .