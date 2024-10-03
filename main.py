import os
import subprocess
import logging  # Импортируем модуль для логирования
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import re  # Для очистки имени файла

# Токен вашего бота
TOKEN = '7556892045:AAE98-ycwnQ4WQHETwbuw3hPaLs-Q6l28Iw'

# Список разрешённых пользователей
ALLOWED_USERS = [6808338323, 7275931930, 7369990086, 285690209, 8044345031,
                 7552562374]  # user_id разрешённых пользователей

# Эталонные значения метаданных (эталонный чек)
REFERENCE_METADATA = {
    "ModDate": "D:20240917224511+03'00'",
    "Creator": "JasperReports Library version 6.5.1",
    "CreationDate": "D:20240917224511+03'00'",
    "Producer": "iText 2.1.7 by 1T3XT",
    "PDFVersion": "1.3",
    "FileType": "PDF",
    "FileTypeExtension": "pdf",
    "MIMEType": "application/pdf",
    "Linearized": "No",
    "TaggedPDF": "Yes",
    "PageCount": 1,
    "FileSize": (50 * 1024, 60 * 1024)  # Размер в байтах (50 - 55 кБ)
}

# Настройка логирования
logging.basicConfig(
    filename='bot_log.log',  # Запись логов в файл
    level=logging.INFO,  # Уровень логирования (INFO, WARNING, ERROR)
    format='%(asctime)s - %(levelname)s - %(message)s'  # Формат логов
)


# Функция для проверки, разрешён ли пользователь
def is_allowed_user(user_id):
    return user_id in ALLOWED_USERS


# Функция для очистки имени файла
def sanitize_filename(filename):
    # Заменяем недопустимые символы безопасными, например, дефисами
    return re.sub(r'[<>:"/\\|?*]', '-', filename)


# Функция для извлечения метаданных с помощью ExifTool
def extract_metadata_exiftool(file_path):
    result = subprocess.run(['exiftool', file_path], stdout=subprocess.PIPE)

    # Пробуем декодировать с помощью cp1251, а если ошибка, то обрабатываем как latin-1
    try:
        metadata_str = result.stdout.decode('cp1251')
    except UnicodeDecodeError:
        metadata_str = result.stdout.decode('latin-1', errors='ignore')

    metadata = {}
    for line in metadata_str.splitlines():
        if ": " in line:
            key, value = line.split(": ", 1)
            metadata[key.strip()] = value.strip()

    return metadata


# Функция проверки метаданных на соответствие эталону
def check_metadata(metadata):
    errors = []  # Список для сбора всех ошибок

    # Проверяем соответствие Creator, Producer, ModDate, CreationDate
    if metadata.get("Creator") != REFERENCE_METADATA["Creator"]:
        errors.append("Creator не совпадает.")
    if metadata.get("Producer") != REFERENCE_METADATA["Producer"]:
        errors.append("Producer не совпадает.")
    if metadata.get("ModDate") != metadata.get("CreationDate"):
        errors.append("ModDate и CreationDate не совпадают.")
    if metadata.get("PDF Version") != REFERENCE_METADATA["PDFVersion"]:
        errors.append("PDF Version не совпадает.")

    # Проверяем размер файла
    file_size = int(metadata.get("File Size", "0").split()[0]) * 1024  # Конвертируем в байты
    if not (REFERENCE_METADATA["FileSize"][0] <= file_size <= REFERENCE_METADATA["FileSize"][1]):
        errors.append("Размер файла не в пределах допустимого диапазона.")

    # Проверяем другие параметры
    if metadata.get("File Type") != REFERENCE_METADATA["FileType"]:
        errors.append("FileType не совпадает.")
    if metadata.get("File Type Extension") != REFERENCE_METADATA["FileTypeExtension"]:
        errors.append("FileTypeExtension не совпадает.")
    if metadata.get("MIME Type") != REFERENCE_METADATA["MIMEType"]:
        errors.append("MIMEType не совпадает.")
    if metadata.get("Linearized") != REFERENCE_METADATA["Linearized"]:
        errors.append("Linearized не совпадает.")
    if metadata.get("Tagged PDF") != REFERENCE_METADATA["TaggedPDF"]:
        errors.append("Tagged PDF не совпадает.")
    if int(metadata.get("Page Count", "0")) != REFERENCE_METADATA["PageCount"]:
        errors.append("Количество страниц не совпадает.")

    # Если ошибок нет, чек подлинный
    if not errors:
        return True, "Чек подлинный."
    else:
        # Возвращаем False и список ошибок
        return False, "\n".join(errors)


# Обработчик для отправки клавиатуры пользователю
def send_menu(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if is_allowed_user(user_id):
        # Создаём клавиатуру
        keyboard = [
            [KeyboardButton("Проверить чек Сбер-Сбер")],
            [KeyboardButton("Узнать метаданные")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        update.message.reply_text("Выбери действие:", reply_markup=reply_markup)
        logging.info(f"Пользователь {user_id} открыл меню.")
    else:
        update.message.reply_text("У вас нет доступа для использования этого бота.")
        logging.warning(f"Попытка доступа от пользователя {user_id} без разрешения.")


# Обработчик выбора действия пользователем
def handle_action(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = update.message.text

    if text == "Проверить чек Сбер-Сбер":
        update.message.reply_text("Отправьте PDF-чек для проверки.")
        context.user_data['action'] = 'check_sber'
        logging.info(f"Пользователь {user_id} выбрал проверку чека Сбер-Сбер.")
    elif text == "Узнать метаданные":
        update.message.reply_text("Отправьте PDF-файл для извлечения метаданных.")
        context.user_data['action'] = 'get_metadata'
        logging.info(f"Пользователь {user_id} выбрал получение метаданных.")


# Функция для рассылки сообщений
def send_broadcast(context: CallbackContext) -> None:
    message = "Обновите бота, нажав на /start, внёс правки"

    for user_id in ALLOWED_USERS:
        try:
            context.bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")


# Команда для рассылки
def broadcast_command(update: Update, context: CallbackContext) -> None:
    send_broadcast(context)
    update.message.reply_text('Сообщение отправлено всем пользователям.')


# Обработчик сообщений, когда пользователь отправляет PDF-файл
def handle_pdf(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if is_allowed_user(user_id):
        file = update.message.document
        if file.mime_type == 'application/pdf':
            try:
                # Получаем файл через get_file()
                file_obj = file.get_file()

                # Очищаем имя файла от недопустимых символов
                safe_file_name = sanitize_filename(file.file_name)
                file_path = f"./check/{safe_file_name}"

                logging.info(f"Получен файл: {safe_file_name} от пользователя {user_id}")

                file_obj.download(file_path)

                # Извлечение метаданных с помощью ExifTool
                exiftool_metadata = extract_metadata_exiftool(file_path)

                action = context.user_data.get('action')

                if action == 'check_sber':
                    # Проверка метаданных
                    is_valid, message = check_metadata(exiftool_metadata)

                    # Ответ пользователю
                    if is_valid:
                        update.message.reply_text("Чек подлинный.")
                        logging.info(f"Чек подлинный: {safe_file_name}")
                    else:
                        update.message.reply_text(f"Чек поддельный. Причины:\n{message}")
                        logging.warning(f"Чек поддельный: {safe_file_name}. Причины: {message}")
                elif action == 'get_metadata':
                    # Отправка всех метаданных пользователю
                    metadata_str = "\n".join([f"{key}: {value}" for key, value in exiftool_metadata.items()])
                    update.message.reply_text(f"Метаданные PDF:\n{metadata_str}")
                    logging.info(f"Отправлены метаданные для файла: {safe_file_name}")

            except Exception as e:
                update.message.reply_text("Произошла ошибка при обработке файла.")
                logging.error(f"Ошибка при обработке файла {safe_file_name}: {e}")
        else:
            update.message.reply_text("Пожалуйста, отправьте PDF-файл.")
            logging.warning(f"Получен файл неподходящего формата от пользователя {user_id}")
    else:
        update.message.reply_text("У вас нет доступа для использования этого бота.")
        logging.warning(f"Доступ запрещен для пользователя {user_id}")


# Функция старта бота
def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if is_allowed_user(user_id):
        send_menu(update, context)
    else:
        update.message.reply_text("У вас нет доступа для использования этого бота.")
        logging.warning(f"Попытка доступа от пользователя {user_id} без разрешения.")


# Основная функция для запуска бота
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_action))  # Обработка выбора действия
    dp.add_handler(MessageHandler(Filters.document.mime_type("application/pdf"), handle_pdf))  # Обработка PDF
    dp.add_handler(CommandHandler("broadcast", broadcast_command))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
