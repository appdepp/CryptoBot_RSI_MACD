import os
import logging
from dotenv import load_dotenv
from binance.client import Client
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler
from telegram.constants import ParseMode
import matplotlib.pyplot as plt
from io import BytesIO


# Загружаем переменные окружения из файла .env
load_dotenv()

# Получаем API ключи из переменных окружения
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')
TELEGRAM_API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем клиента для Binance
binance_client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)

# Топ-10 криптовалютных пар
TOP_CRYPTO_PAIRS = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT', 'LTCUSDT',
    'XRPUSDT', 'DOGEUSDT', 'DOTUSDT', 'TRXUSDT', 'AVAXUSDT'
]

# Обновленный список Топ-20 криптовалют
# TOP_CRYPTO_PAIRS = [
#     'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT',
#     'XRPUSDT', 'DOGEUSDT', 'MATICUSDT', 'DOTUSDT', 'ATOMUSDT',
#     'LTCUSDT', 'AVAXUSDT', 'LINKUSDT', 'SHIBUSDT', 'TRXUSDT',
#     'MKRUSDT', 'FLOKIUSDT', 'SANDUSDT', 'AAVEUSDT', 'CRVUSDT'


# Периоды для анализа
PERIODS = ['5m', '15m', '30m', '1h', '6h', '12h', '1d', '3d', '1w', '1M']

# Словарь для хранения данных пользователей
user_data = {}

# Инициализация клавиатуры (основное меню)
main_keyboard = [
    [InlineKeyboardButton("📊 Топ криптовалют", callback_data="top_pairs")],
    [InlineKeyboardButton("💬 Помощь", callback_data="help")],
]


# # Функция для вычисления RSI

def calculate_rsi(prices, period=14):
    if len(prices) < period:
        raise ValueError("Недостаточно данных для расчета RSI")

    gains = []
    losses = []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        elif change < 0:
            gains.append(0)
            losses.append(-change)
        else:
            gains.append(0)
            losses.append(0)

    # Вычисляем первые средние значения
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # Динамическое обновление средних (EMA)
    for i in range(period, len(prices)):
        change = prices[i] - prices[i - 1]
        gain = max(change, 0)
        loss = -min(change, 0)

        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100  # Если нет убытков, RSI = 100

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Функция для вычисления MACD

def calculate_macd(prices, short_period=12, long_period=26, signal_period=9):
    # Функция для вычисления EMA
    def ema(prices, period):
        multiplier = 2 / (period + 1)
        ema_values = [sum(prices[:period]) / period]  # Начальное значение EMA = SMA
        for price in prices[period:]:
            ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
        return ema_values

    # Рассчитываем EMA с коротким и длинным периодом
    short_ema = ema(prices, short_period)
    long_ema = ema(prices, long_period)

    # MACD: разность короткой и длинной EMA (начиная с точки, где обе EMA определены)
    macd_start = len(prices) - len(short_ema)
    macd = [s - l for s, l in zip(short_ema[macd_start:], long_ema)]

    # Вычисляем сигнальную линию как EMA на основе MACD
    signal_line = ema(macd, signal_period)

    return macd[-1], signal_line[-1]  # Возвращаем последние значения MACD и сигнальной линии


# Команда старта
async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    # Если пользователя нет в данных, это первый запуск
    if user_id not in user_data:
        user_data[user_id] = {'selected_pair': 'BTCUSDT'}
        message = await update.message.reply_text(
            "Привет! Я бот для анализа криптовалют.\n"
            "Вы можете выбрать криптовалютную пару для анализа, а также получить информацию о RSI.\n"
            "Для начала выберите одну из команд ниже:",
            reply_markup=InlineKeyboardMarkup(main_keyboard)
        )

        # Закрепляем сообщение при первом запуске
        try:
            await update.message.pin()
        except Exception as e:
            logger.error(f"Ошибка при попытке закрепить сообщение: {str(e)}")

    else:
        # Если пользователь уже был в системе, просто отправляем приветствие
        await update.message.reply_text(
            "Вы уже запустили бота. Используйте команды для анализа.",
            reply_markup=InlineKeyboardMarkup(main_keyboard)
        )

# Команда помощи
async def help_command(update: Update, context: CallbackContext) -> None:
    await update.callback_query.message.reply_text(
        "📌 *Как пользоваться ботом:*\n\n"
        "1️⃣ **Выберите криптовалютную пару:**\n"
        "   Нажмите кнопку \"📊 Топ криптовалют\", чтобы выбрать одну из криптовалютных пар (например, BTC/USDT или введите вручную).\n\n"
        "2️⃣ **Получите анализ:**\n"
        "   После выбора пары бот проведет анализ по всем доступным периодам (5m, 15m, 1h, 1d и другие). Вы получите:\n"
        "   - Текущую цену криптовалюты.\n"
        "   - Индикатор **RSI** (Relative Strength Index), который помогает определить текущую силу тренда.\n"
        "   - Торговый сигнал: покупка, продажа или нейтральная зона.\n\n"
        "📊 *Пример использования:*\n"
        "   - Вы выбрали пару **BTCUSDT**.\n"
        "   - Бот покажет анализ по нескольким временным периодам, например, 5 минут, 1 час, 1 день и т.д.\n\n"
        "💡 *Полезные советы:*\n"
        "- **RSI < 40** = **Сигнал на покупку** 🟢. Это означает, что криптовалюта может быть перепродана, и существует вероятность роста.\n"
        "- **RSI > 70** = **Сигнал на продажу** 🔴. Это означает, что криптовалюта может быть перекуплена, и существует вероятность падения.\n"
        "- **RSI между 40 и 70** = **Нейтральная зона** 🔷. На рынке нет явной перепроданности или перекупленности.\n\n"
        "🔄 *Примечания:*\n"
        "- RSI — это лишь один из индикаторов, и его следует использовать в сочетании с другими методами анализа для более точных результатов.\n"
        "- Если что-то не работает, используйте команду **/start** для перезапуска бота.",
        parse_mode=ParseMode.MARKDOWN
    )

# Обработчик команды вручную
async def set_pair(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    # Проверяем, ввел ли пользователь пару
    if len(context.args) != 1:
        await update.message.reply_text(
            "⚠️ Использование команды: /setpair <пара>\nПример: /setpair BTCUSDT"
        )
        return

    pair = context.args[0].upper()

    # Проверяем, существует ли такая пара на Binance
    try:
        binance_client.get_symbol_ticker(symbol=pair)
        user_data[user_id] = {"selected_pair": pair}
        await update.message.reply_text(
            f"✅ Валютная пара установлена: {pair}\nТеперь вы можете провести анализ.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"📊 Анализ по всем периодам для {pair}", callback_data="analyze_all_periods")]
            ])
        )
    except Exception as e:
        logger.error(f"Ошибка проверки пары {pair}: {str(e)}")
        await update.message.reply_text(f"⚠️ Валютная пара {pair} не найдена. Проверьте ввод.")


# Функция для обработки кнопки "Топ криптовалют"
async def top_pairs(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton(pair, callback_data=f"pair_{pair}")] for pair in TOP_CRYPTO_PAIRS
    ]
    keyboard.append([InlineKeyboardButton("🔢 Ввод вручную", callback_data="manual_input")])  # Кнопка для ввода вручную

    await update.callback_query.message.reply_text(
        "Выберите криптовалютную пару для анализа или введите свою вручную:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
# Функция для обработки кнопки "Ввод вручную"
async def handle_manual_input(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    await update.callback_query.message.reply_text(
        "⚠️ Пожалуйста, введите валютную пару в формате, например: BTCUSDT\n\n"
        "Используйте команду: /setpair <пара>\nПример: /setpair BTCUSDT"
    )
    user_data[user_id]["manual_input"] = True  # Отметим, что пользователь хочет ввести пару вручную


# Обработчик кнопок
async def handle_button_click(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if data == "help":
        await help_command(update, context)
    elif data == "top_pairs":
        await top_pairs(update, context)
    elif data == "manual_input":
        await handle_manual_input(update, context)  # Обработка ввода вручную
    elif data.startswith("pair_"):
        selected_pair = data.split("_")[1]
        user_data[user_id] = {"selected_pair": selected_pair}

        # Логируем выбранную пару
        logger.info(f"User {user_id} selected pair {selected_pair}")

        # Ответ пользователю
        await query.message.reply_text(f"Вы выбрали пару {selected_pair}.")

        # Добавляем кнопку для анализа по всем периодам после выбора пары
        keyboard = [
            [InlineKeyboardButton(f"📊 Анализ по всем периодам для {selected_pair}",
                                  callback_data="analyze_all_periods")]
        ]
        await query.message.reply_text("Теперь выберите анализ по всем периодам.",
                                       reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "analyze_all_periods":
        # Логируем попытку анализа
        logger.info(f"User {user_id} requested analysis for {user_data[user_id].get('selected_pair')}")

        # Проверяем, выбрал ли пользователь пару
        if user_id not in user_data or "selected_pair" not in user_data[user_id]:
            await query.message.reply_text("⚠️ Сначала выберите валютную пару.")
            return

        # Запускаем анализ
        await analyze_all_periods(update, context)



# Обновленный анализ с графиком
async def analyze_all_periods(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    pair = user_data[user_id]["selected_pair"]

    # Уведомляем пользователя, что запрос в обработке
    await update.callback_query.answer(text="🔄 Идет загрузка... Пожалуйста, подождите.", show_alert=False)

    # Обновляем сообщение на сообщение о процессе загрузки
    loading_message = await update.callback_query.message.edit_text(
        "🔄 Идет обработка данных... Пожалуйста, подождите."
    )
    # Генерируем график за последний месяц
    chart_buf = generate_chart(pair)

    # Отправляем график
    await update.callback_query.message.reply_photo(
        photo=chart_buf,
        caption="📉 График цены за месяц"
    )
    try:
        results = {}
        for period in PERIODS:
            klines = binance_client.get_klines(symbol=pair, interval=period, limit=50)
            prices = [float(candle[4]) for candle in klines]  # Закрывающие цены
            rsi = calculate_rsi(prices)



            # Рассчитываем MACD
            macd, signal_line = calculate_macd(prices)
            macd_signal = ""

            # Логика для сигналов на основе MACD
            if macd > signal_line:
                macd_signal = "🟢 Сигнал на покупку (MACD выше)"
            elif macd < signal_line:
                macd_signal = "🔴 Сигнал на продажу (MACD ниже)"
            else:
                macd_signal = "🔷 Нейтральная зона (MACD = )"

            # Логика для сигналов на основе RSI
            rsi_signal = ""
            if rsi < 40:
                rsi_signal = "🟢 Сигнал на покупку"
            elif rsi > 70:
                rsi_signal = "🔴 Сигнал на продажу"
            else:
                rsi_signal = "🔷 Нейтральная зона"

            results[period] = {
                "macd": macd,
                "signal_line": signal_line,
                "macd_signal": macd_signal,
                "rsi": rsi,
                "rsi_signal": rsi_signal,
            }



        # Получаем текущую цену и статистику за 24 часа
        try:
            price = binance_client.get_symbol_ticker(symbol=pair)
            ticker_24hr = binance_client.get_ticker(symbol=pair)

            volume = ticker_24hr['volume']
            price_change_percent = ticker_24hr['priceChangePercent']

            response = f"📊 *Анализ по всем периодам для пары {pair}:*\n\n"
            for period, data in results.items():
                response += (
                    f"🕒 Период: {period}\n"
                    f"   📊 RSI: {data['rsi']:.2f}\n"
                    f"   {data['rsi_signal']}\n"
                    f"   {data['macd_signal']}\n\n"
                )

            response += (
                f"🔹 Текущая цена {pair}: {price['price']} USDT\n"
                f"🔹 Объем за 24 часа: {volume} {pair[:3]}\n"
                f"🔹 Изменение за 24 часа: {price_change_percent}%"
            )



            # Обновляем сообщение с результатами и добавляем кнопку
            keyboard = [
                [InlineKeyboardButton("📊 Топ криптовалют", callback_data="top_pairs")],
                [InlineKeyboardButton("💬 Помощь", callback_data="help")],
            ]
            await loading_message.edit_text(response, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Ошибка при получении данных 24hr для {pair}: {str(e)}")
            await update.callback_query.message.edit_text("⚠️ Произошла ошибка при получении данных.")
            await update.callback_query.message.reply_text(f"Детали ошибки: {str(e)}")

    except Exception as e:
        logger.error(f"Ошибка при анализе по всем периодам для {pair}: {str(e)}")
        await update.callback_query.message.edit_text("⚠️ Произошла ошибка при анализе по всем периодам.")
        await update.callback_query.message.reply_text(f"Детали ошибки: {str(e)}")


# Генерация графика с максимумами и минимумами
def generate_chart(pair):
    klines = binance_client.get_klines(symbol=pair, interval='1d', limit=30)
    dates = [kline[0] for kline in klines]
    prices = [float(kline[4]) for kline in klines]

    # Преобразуем время в формат даты
    from datetime import datetime
    dates = [datetime.utcfromtimestamp(date / 1000).strftime('%Y-%m-%d') for date in dates]

    # Найдем максимумы и минимумы
    max_price = max(prices)
    min_price = min(prices)
    max_index = prices.index(max_price)
    min_index = prices.index(min_price)

    # Строим график
    plt.figure(figsize=(10, 6))
    plt.plot(dates, prices, label=f'{pair} Price', color='b', marker='o')

    # Отображаем точки для максимума и минимума
    plt.scatter(dates[max_index], max_price, color='g', label="Максимум", zorder=5)
    plt.scatter(dates[min_index], min_price, color='r', label="Минимум", zorder=5)

    # Добавляем текстовые аннотации для максимума и минимума
    plt.annotate(f"Max: {max_price:.2f}", (dates[max_index], max_price), textcoords="offset points", xytext=(0, 10),
                 ha='center', fontsize=10, color='g')
    plt.annotate(f"Min: {min_price:.2f}", (dates[min_index], min_price), textcoords="offset points", xytext=(0, -10),
                 ha='center', fontsize=10, color='r')

    plt.title(f'График цены для {pair} за последний месяц')
    plt.xlabel('Дата')
    plt.ylabel('Цена (USDT)')
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    # Сохраняем график в байтовый поток
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    return buf


if __name__ == '__main__':
    # Добавляем обработчик команды /setpair

    application = Application.builder().token(TELEGRAM_API_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setpair", set_pair))  # Новый обработчик
    application.add_handler(CallbackQueryHandler(handle_button_click))

    application.run_polling()