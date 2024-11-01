from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
import logging

from config import producers, REFERENCE_METADATA_MAP
from utils import sanitize_filename, extract_metadata_exiftool, check_metadata
from database import update_user_checks, get_user_info, get_all_users, get_user_without_zero, \
    get_id_users, get_active_users_today, get_active_users_yesterday, get_active_users_week, calculate_all_user


# Обработчик для отправки клавиатуры пользователю
def send_menu(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    # Выводим информацию о пользователе
    # user_info = get_user_info(user_id)
    # update.message.reply_text(
    #    f"ID: {user_info[0]}\nUsername: {user_info[1]}\nКоличество проверок: {user_info[2]}\nДата первого запуска: {user_info[3]}\nДата последней проверки: {user_info[4]}")

    # Создаём клавиатуру
    keyboard = [
        [KeyboardButton("Проверить чек"), KeyboardButton("Узнать метаданные")],
        [KeyboardButton("Обратиться в поддержку")],[KeyboardButton("Использовать зеркало")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text("Выбери действие:", reply_markup=reply_markup)
    logging.info(f"Пользователь {user_id} открыл меню.")


def get_stats(update: Update, context: CallbackContext):
    keyboard = [
        [KeyboardButton("За сегодня"), KeyboardButton("За Вчера")],
        [KeyboardButton("Все пользователи")],
        [KeyboardButton("Назад")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    username = update.message.from_user.username
    update.message.reply_text(f"Выбери действие: \n\nЗа сегодня - выгружает статистику использования бота за сегодня\n\nЗа Вчера - выгружает статистику бота за вчерашний день\n\nВсе пользователи - показывает всех пользователей, кто хотя бы раз проверил чек", reply_markup=reply_markup)
    json_dump = get_user_without_zero()
    result_string = "\n".join(item.strip("' \n") for item in json_dump)
    today = get_active_users_today()
    yesterday = get_active_users_yesterday()
    week = get_active_users_week()
    all = calculate_all_user()
    update.message.reply_text(f"За сегодня - {today}")
    update.message.reply_text(f"За вчера - {yesterday}")
    update.message.reply_text(f"За неделю - {week}")
    update.message.reply_text(f"Всего пользователей в боте - {all}")
    # print(result_string)
    logging.info(f"Пользователь {username} Выгрузил стату.")


# Функция для рассылки сообщений всем пользователям
def send_broadcast_message(context: CallbackContext, message: str):
    users = get_id_users()
    for user_id in users:
        print(user_id)
        try:
            context.bot.send_message(chat_id=user_id, text=message)
            logging.info(f"Сообщение отправлено пользователю {user_id}")
        except Exception as e:
            logging.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")


# Обработчик выбора действия пользователем
def handle_action(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = update.message.text

    if text == "Проверить чек":
        context.user_data['action'] = 'check'
        keyboard = [
            [KeyboardButton("Назад")],
            [KeyboardButton("Обратиться в поддержку")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        update.message.reply_text("Отправьте PDF-чек для проверки.", reply_markup=reply_markup)
        logging.info(f"Пользователь {user_id} выбрал проверку чека.")

    elif text == "Узнать метаданные":
        keyboard = [
            [KeyboardButton("Назад")],
            [KeyboardButton("Обратиться в поддержку")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        update.message.reply_text("Отправьте PDF-файл для извлечения метаданных.", reply_markup=reply_markup)
        context.user_data['action'] = 'get_metadata'

        logging.info(f"Пользователь {user_id} выбрал получение метаданных.")

    elif text == "Назад":
        # Создаём клавиатуру
        keyboard = [
            [KeyboardButton("Проверить чек"), KeyboardButton("Узнать метаданные")],
            [KeyboardButton("Обратиться в поддержку")], [KeyboardButton("Использовать зеркало")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        update.message.reply_text("Выбери действие:", reply_markup=reply_markup)
        logging.info(f"Пользователь {user_id} вернулся в меню.")

    elif text == "Обратиться в поддержку":
        keyboard = [
            [KeyboardButton("Назад")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        update.message.reply_text(
            "Готов выслушать ваше предложение / проблему.\nНапишите прямо тут и получите ответ в ближайшее время!",
            reply_markup=reply_markup)
        logging.info(f"Пользователь {user_id} выбрал меню поддержка.")

    elif text == "Пришли статистику всех пользователей":
        get_stats(update, context)

    elif text == "Использовать зеркало":
        context.user_data['action'] = 'glasses'
        keyboard = [
            [KeyboardButton("Назад")],
            [KeyboardButton("Обратиться в поддержку")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        update.message.reply_text("Отправьте PDF-чек для проверки.", reply_markup=reply_markup)
        logging.info(f"Пользователь {user_id} выбрал проверку чека через зеркало.")


# Обработчик сообщений с PDF
def handle_pdf(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    file = update.message.document
    if file.mime_type == 'application/pdf':
        try:
            file_obj = file.get_file()
            safe_file_name = sanitize_filename(file.file_name)
            file_path = f"./check/{safe_file_name}"
            file_obj.download(file_path)

            logging.info(f"Получен файл: {safe_file_name} от пользователя {user_id}")
            exiftool_metadata = extract_metadata_exiftool(file_path)
            producer = exiftool_metadata.get("Producer", "")
            action = context.user_data.get('action')
            if action == 'get_metadata':
                metadata_str = "\n".join([f"{key}: {value}" for key, value in exiftool_metadata.items()])
                update.message.reply_text(f"Метаданные PDF:\n{metadata_str}")

                logging.info(f"Отправлены метаданные для файла: {safe_file_name}")

            elif action == 'check':
                logging.info(f"будем чекать")
                if producer in producers:
                    logging.info(f"Producer '{producer}' найден в списке разрешённых., работаем дальше")
                    if producer in REFERENCE_METADATA_MAP:
                        reference_metadata = REFERENCE_METADATA_MAP[producer]
                        #print(reference_metadata)
                        #print()
                        is_valid, message = check_metadata(exiftool_metadata, reference_metadata)
                        logging.info(f"valid? - {is_valid}, msg = {message}")
                        if is_valid:
                            update.message.reply_text(f"Чек {safe_file_name} подлинный.")
                            # update.message.reply_text(f"Producer '{producer}' найден в списке разрешённых. и на первый взгляд Чек {safe_file_name} подлинный.")
                            logging.info(f"Чек подлинный: {safe_file_name}")
                        else:
                            update.message.reply_text(f"Чек {safe_file_name} поддельный. Причины:\n{message}")
                            logging.warning(f"Чек поддельный: {safe_file_name}. Причины: {message}")
                else:
                    update.message.reply_text(f"Чек {safe_file_name} поддельный. Причины:Слишком плохо сделан")
                    logging.warning(f"Чек поддельный: {safe_file_name}. Причины: Producer '{producer}' не найден в списке разрешённых.")
                # Обновляем количество проверок пользователя
                update_user_checks(user_id)

            elif action =='glasses':
                logging.info(f"Используется зеркало")


        except Exception as e:
            update.message.reply_text("Произошла ошибка при обработке файла.")
            logging.error(f"Ошибка при обработке файла {safe_file_name}: {e}")
    else:
        update.message.reply_text("Пожалуйста, отправьте PDF-файл.")
        logging.warning(f"Получен файл неподходящего формата от пользователя {user_id}")
