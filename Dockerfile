FROM python:3.11-slim

WORKDIR /app

# Устанавливаем зависимости для Pillow


# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем приложение
COPY . .

# Создаем папки для данных
RUN mkdir -p static/uploads data

# Даем права на запись (более простой подход)
RUN chmod -R 777 static/uploads data

EXPOSE 5001


CMD ["python", "app.py"]
