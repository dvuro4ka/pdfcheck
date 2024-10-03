# Используем официальный образ Python 3.10
FROM python:3.11.4-slim

# Устанавливаем необходимые системные зависимости (включая exiftool)
RUN apt-get update && apt-get install -y \
    libimage-exiftool-perl \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код бота в контейнер
COPY . .

# Запускаем бота
CMD ["python", "bot.py"]
