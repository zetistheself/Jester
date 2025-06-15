import datetime
import payment
import server_manager
import database
import dotenv
import os

from telebot import TeleBot, types
from database import setup_database, get_user_tariffs, add_payment, check_config_was_generated, add_user_tariff

dotenv.load_dotenv()

TOKEN = os.getenv("TOKEN")
bot = TeleBot(TOKEN)

engine = setup_database()

month_tariff = datetime.datetime.now() + datetime.timedelta(days=30)


# 📲 Главное меню
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('🛍 Купить VPN', '📦 Мой тариф')
    markup.row('💬 Поддержка', '📚 FAQ')
    return markup


# 🎫 Меню тарифов
def tariff_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('50 мбит/сек', '100 мбит/сек', '300 мбит/сек')
    markup.row('🔙 Назад')
    return markup


def payment_menu(payment_url, payment_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text='Оплатить', url=payment_url))
    markup.add(types.InlineKeyboardButton(text='Проверить платеж и получить VPN', callback_data=payment_id))
    return markup


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "Добро пожаловать! Выберите действие:", reply_markup=main_menu())


@bot.message_handler(func=lambda msg: msg.text == '🛍 Купить VPN')
def buy_vpn(message):
    with open('static/tariffs.jpg', 'rb') as photo:
        bot.send_photo(message.chat.id, photo, caption="Выберите тариф:", reply_markup=tariff_menu())


@bot.message_handler(func=lambda msg: msg.text in ['50 мбит/сек', '100 мбит/сек', '300 мбит/сек'])
def choose_tariff(message):
    try:
        speed = int(message.text[:-8])
        value = payment.payment_tariff[message.text]
    except (KeyError, ValueError):
        bot.send_message(message.chat.id, "❌ Ошибка: выбран неверный тариф.", reply_markup=main_menu())
        return

    payment_info = payment.get_payment(value, f"Оплата тарифа {message.text}")
    if not payment_info:
        bot.send_message(message.chat.id, "❌ Не удалось создать платёж. Попробуйте позже.", reply_markup=main_menu())
        return

    # Проверка доступности сервера
    if not server_manager.check_config_availability(speed, payment_info.id):
        bot.send_message(
            message.chat.id,
            "🚫 К сожалению, нет доступных серверов для выбранного тарифа.\n"
            "Попробуйте позже или выберите другой тариф.",
            reply_markup=main_menu()
        )
        return

    # Сохраняем платёж
    add_payment(message.from_user.id, payment_info.id, str(value), speed)

    # Отправка пользователю информации о платеже
    bot.send_message(
        message.chat.id,
        f"💳 Идентификатор платежа: `{payment_info.id}`\n"
        f"Вы выбрали тариф: *{message.text}*",
        reply_markup=payment_menu(payment_info.confirmation.confirmation_url, payment_info.id),
        parse_mode='Markdown'
    )


@bot.callback_query_handler()
def check_payment(call):
    payment_id = call.data

    # Проверяем, уже ли был сгенерирован конфиг
    if check_config_was_generated(payment_id):
        bot.send_message(
            call.message.chat.id,
            "ℹ️ Платёж уже был подтверждён ранее.\n"
            "Ваш тариф уже активирован.",
            reply_markup=main_menu()
        )
        return

    success, payment_info = payment.check_payment(payment_id)

    with database.Session() as session:
        payment_record = session.query(database.Payments).filter(
            database.Payments.payment_id == payment_id
        ).first()

        if not payment_record:
            bot.send_message(
                call.message.chat.id,
                "❌ Ошибка: платеж не найден в базе данных.",
                reply_markup=main_menu()
            )
            return

        speed = payment_record.speed

        if success:
            bot.send_message(
                call.message.chat.id,
                "✅ Платеж успешно подтвержден!\n"
                "Создаём вашу конфигурацию, пожалуйста подождите немного...",
                reply_markup=main_menu()
            )
            status, key = add_user_tariff(call.from_user.id, speed, payment_id)

            if status != "OK":
                if status == "Operation blocked":
                    bot.send_message(
                        call.message.chat.id,
                        "🛠️ Сервер сейчас занят созданием конфигурации для другого пользователя. Подождите немного и попробуйте снова.\nСпасибо за понимание",
                        reply_markup=main_menu()
                    )
                    return

                bot.send_message(
                    call.message.chat.id,
                    f"⚠️ Произошла ошибка при создании конфигурации:\n`{status}`\n"
                    "Пожалуйста, обратитесь в поддержку.",
                    reply_markup=main_menu(),
                    parse_mode='Markdown'
                )
                return

            bot.send_message(
                call.message.chat.id,
                f"🎉 Конфигурация успешно создана!\n\n"
                f"🔑 Ваш ключ:\n`{key}`\n\n"
                "Инструкция: https://telegra.ph/Kak-podklyuchit-vpn-na-IPHONEANDROID-06-03",
                reply_markup=main_menu(),
                parse_mode='Markdown'
            )

        else:
            bot.send_message(
                call.message.chat.id,
                "❗ Платеж не подтвержден или не найден.\n"
                "Попробуйте позже или свяжитесь с поддержкой.",
                reply_markup=main_menu()
            )


@bot.message_handler(func=lambda msg: msg.text == '📦 Мой тариф')
def my_tariff(message):
    tariffs = get_user_tariffs(message.from_user.id)

    if not tariffs:
        bot.send_message(message.chat.id, "У вас пока нет активных тарифов.", reply_markup=main_menu())
        return

    text = "🧾 Ваши активные тарифы:\n\n"
    now = datetime.datetime.utcnow()

    for tariff in tariffs:
        days_left = (tariff.expires_at - now).days
        text += (
            f"💨 Тариф: {tariff.speed} мбит/сек\n"
            f"🔑 Ключ: `{tariff.vpn_key}`\n"
            f"📅 Осталось: {days_left} дней\n"
            f"— — — — —\n"
        )

    bot.send_message(message.chat.id, text, reply_markup=main_menu(), parse_mode='Markdown')


@bot.message_handler(func=lambda msg: msg.text == '💬 Поддержка')
def support(message):
    bot.send_message(message.chat.id, "По всем вопросам обращайтесь: @jestervpn_support", reply_markup=main_menu())


@bot.message_handler(func=lambda msg: msg.text == '📚 FAQ')
def faq(message):
    bot.send_message(
        message.chat.id,
        "https://telegra.ph/Kak-podklyuchit-vpn-na-IPHONEANDROID-06-03",
        reply_markup=main_menu()
    )


@bot.message_handler(func=lambda msg: msg.text == '🔙 Назад')
def go_back(message):
    bot.send_message(message.chat.id, "Возвращаюсь в главное меню", reply_markup=main_menu())


bot.infinity_polling()
