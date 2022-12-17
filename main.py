import logging
import calendar
from datetime import datetime, timedelta
from mongo_app import get_user, insert_user, get_top_investors
from df_process import make_recommendation, make_portfel
########################################################################################################################
# Проверки модуля телеграм и импортирование
try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"Загружена не 20 версия"
    )
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, \
    ConversationHandler, MessageHandler, filters, CallbackQueryHandler

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO,
    # filename=os.path.join(os.path.dirname(__file__), 'bot{}.log'.format(datetime.today().strftime('%Y-%m-%d:%H-%M'))),
    filemode='w'
)

########################################################################################################################
# Глобальные переменные (словари с ключом - ид беседы(уникален))
_poll_strings: [str] = []  # Массив массивов для вопросов-ответов опроса
_poll_points: [float] = []  # Массив баллов за вопрос
_poll_risk_amount = 0  # Количество вопросов про риски для нормировки
_poll_rating_amount = 0  # Количество вопросов про рейтинг для нормировки

_current_question: {int: int} = {}  # chat_id: index of current question
_current_points: {int: [float, float]} = {}  # chat_id: [rating, risk]
_current_stock: {int: [{str: str}]} = {}  # chat_id: [Name, When_Bought, When_sold]

_user_categories = ['Физическое лицо', 'Юридическое лицо', 'ИП']
_main_menu = [
    ["Рекомендации"],
    ["Оптимальный портфель"],
    ["Лидеры приложения"]
]

# Состояние беседы
(ASK_CATEGORY, RESPONSE, ASK_STOCK_NAME, ASK_STOCK_BOUGHT, ASK_STOCK_SOLD, ASK_STOCK_END, MAIN_MENU) = range(7)
(RATING, RISK) = range(2)

MY_CHAT_ID = 463559149
_special_char = '#'

########################################################################################################################
# Функции календаря
CALENDAR_CALLBACK = "CALENDAR"


def separate_callback_data(data):
    """ Separate the callback data"""
    return data.split(";")


def create_callback_data(action, year, month, day):
    """ Create the callback data associated to each button"""
    return CALENDAR_CALLBACK + ";" + ";".join([action, str(year), str(month), str(day)])


def create_calendar(year=None, month=None):
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    data_ignore = create_callback_data("IGNORE", year, month, 0)
    keyboard = []
    # First row - Month and Year
    row = [InlineKeyboardButton(calendar.month_name[month] + " " + str(year), callback_data=data_ignore)]
    keyboard.append(row)
    # Second row - Week Days
    row = []
    for day in ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]:
        row.append(InlineKeyboardButton(day, callback_data=data_ignore))
    keyboard.append(row)

    my_calendar = calendar.monthcalendar(year, month)
    for week in my_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data=data_ignore))
            else:
                row.append(InlineKeyboardButton(str(day), callback_data=create_callback_data("DAY", year, month, day)))
        keyboard.append(row)
    # Last row - Buttons
    row = [InlineKeyboardButton("<", callback_data=create_callback_data("PREV-MONTH", year, month, day)),
           InlineKeyboardButton(" ", callback_data=data_ignore),
           InlineKeyboardButton(">", callback_data=create_callback_data("NEXT-MONTH", year, month, day))]
    keyboard.append(row)

    return InlineKeyboardMarkup(keyboard)


async def process_calendar_selection(update, context):
    ret_data = (False, None)
    query = update.callback_query
    # print(query)
    (_, action, year, month, day) = separate_callback_data(query.data)
    curr = datetime(int(year), int(month), 1)
    if action == "IGNORE":
        await context.bot.answer_callback_query(callback_query_id=query.id)
    elif action == "DAY":
        await context.bot.edit_message_text(
            text=query.message.text,
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )
        ret_data = True, datetime(int(year), int(month), int(day))
    elif action == "PREV-MONTH":
        pre = curr - timedelta(days=1)
        await context.bot.edit_message_text(
            text=query.message.text,
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            reply_markup=create_calendar(int(pre.year), int(pre.month))
        )
    elif action == "NEXT-MONTH":
        ne = curr + timedelta(days=31)
        await context.bot.edit_message_text(
            text=query.message.text,
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            reply_markup=create_calendar(int(ne.year), int(ne.month))
        )
    else:
        context.bot.answer_callback_query(callback_query_id=query.id, text="Something went wrong!")
        # UNKNOWN
    return ret_data


########################################################################################################################
# Загрузка опроса из файла
def load_poll():
    with open('Poll_strings.txt', 'r', encoding='utf-8') as fd:
        lines = fd.read().splitlines()
        is_text = True

        for line in lines:
            if is_text:
                entry = []
                strings = line.split(_special_char)

                for string in strings:
                    entry.append([string])

                _poll_strings.append(entry)
            else:
                splitted = line.split(' ')
                keyword = splitted[0]

                if keyword == 'risk':
                    global _poll_risk_amount
                    _poll_risk_amount += 1
                else:
                    global _poll_rating_amount
                    _poll_rating_amount += 1

                points = [float(point) for point in splitted[1:]]
                points.append(RISK if keyword == 'risk' else RATING)
                _poll_points.append(points)

            is_text = not is_text


load_poll()


async def done(update: Update, _) -> int:
    # Метод для завершения беседы (Плейсхолдер из-за необходимости)
    await update.message.reply_text('Что-то пошло не так')
    return ConversationHandler.END


def is_registered(user_id) -> bool:
    actual_id = user_id.to_dict()['message']['from']['id']
    user = get_user(actual_id)
    return bool(user)


def add_user(user_obj) -> None:
    insert_user(user_obj)


# Стартовая функция отвечает на /start, начинает беседу, запрашивает категорию пользователя
async def start_command(update: Update, _) -> int:
    if is_registered(update):
        return await go_to_menu(update.message)
        # return ConversationHandler.END  # Уже не в первый раз, заканчиваем беседу,

    message = update.message

    await message.reply_text(text='Кем вы являетесь', reply_markup=ReplyKeyboardMarkup(
        [_user_categories], one_time_keyboard=True, input_field_placeholder='Выберите ответ:'
    ))

    return ASK_CATEGORY


# Функция откликается на введенную категорию и запускает функцию вывода вопроса из опроса
async def poll_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    chat_id = message.chat_id
    category = message.text

    if category not in _user_categories:
        await message.reply_text(text='Кем вы являетесь', reply_markup=ReplyKeyboardMarkup(
            [_user_categories], one_time_keyboard=True, input_field_placeholder='Выберите ответ:'
        ))

        return ASK_CATEGORY

    """"# TODO: Проработать категории"""

    _current_question.update({chat_id: 0})
    _current_points.update({chat_id: [0, 0]})

    return await poll_ask(update, context)


# Функция выводит вопросы из опроса, если вопросов не осталось, завершает опрос
async def poll_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    chat_id = update.message.chat_id
    current_index = _current_question[chat_id]

    if current_index >= len(_poll_strings):
        return await poll_done(update, context)

    poll_entry = _poll_strings[current_index]

    reply_keyboard = poll_entry[1:]

    await message.reply_text(text=poll_entry[0][0], reply_markup=ReplyKeyboardMarkup(
        reply_keyboard, one_time_keyboard=True, input_field_placeholder='Выберите ответ:'
    ))

    return RESPONSE


# Функция обрабатывает ответы на вопросы опроса, спрашивает при удачной обработке ответа следующий вопрос
async def poll_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    chat_id = message.chat_id
    answer = message.text
    current_index = _current_question[chat_id]
    available_answers = _poll_strings[current_index][1:]

    if [answer] not in available_answers:
        reply_keyboard = available_answers

        await message.reply_text(text='Попробуйте еще раз', reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Выберите ответ:'
        ))

        return RESPONSE

    answer_index = available_answers.index([answer])
    available_points = _poll_points[current_index]
    _current_points[chat_id][available_points[-1]] += available_points[answer_index]
    _current_question[chat_id] += 1

    return await poll_ask(update, context)


# Функция завершает опрос, выводит результаты и запускает функцию запроса наименования акции
async def poll_done(update: Update, _) -> int:
    message = update.message
    chat_id = message.chat_id

    rating_points = _current_points[chat_id][RATING] / _poll_risk_amount
    risk_points = _current_points[chat_id][RISK] / _poll_rating_amount

    await message.reply_text(text=f'У Вас {rating_points} очков рейтинга и {risk_points} очков риска')

    await message.reply_text(text='Теперь нам необходимы последние 5 акций, купленные Вами')

    _current_stock.update({chat_id: []})

    return await poll_stock_name(message)


# Функция запрашивает наименование акции
async def poll_stock_name(message) -> int:
    # Ask for stock's name
    await message.reply_text(text='Введите название акции')

    return ASK_STOCK_BOUGHT


# Обработка наименования акции и выводит календарь для ввода даты покупки акции
async def poll_stock_bought(update: Update, _) -> int:
    # Get name
    message = update.message
    chat_id = message.chat_id
    name = message.text
    _current_stock[chat_id].append({'name': name})

    # Ask for bought date
    now = datetime.now()
    reply_markup = create_calendar(now.year, now.month)
    await message.reply_text(text='Выберите дату покупки акции', reply_markup=reply_markup)

    return ASK_STOCK_SOLD


# Обработка состояния календаря, изменение выводимых дат или сохранение выбранной даты
async def bought_calendar_handler(update, context):
    selected, date = await process_calendar_selection(update, context)

    if selected:
        # Get bought date
        selected_date = date.strftime("%Y-%m-%d")
        chat_id = update.callback_query.message.chat_id
        _current_stock[chat_id][-1].update({'start': selected_date})

        await context.bot.send_message(
            chat_id=update.callback_query.from_user.id,
            text=f'Дата покупки: {selected_date}',
            reply_markup=ReplyKeyboardRemove()
        )

        return await poll_stock_sold(update, context)


# Вывод календаря для запроса даты продажи акции
async def poll_stock_sold(update: Update, _) -> int:
    # Ask for sold date
    now = datetime.now()
    message = update.callback_query.message
    reply_markup = create_calendar(now.year, now.month)
    await message.reply_text(text='Выберите дату продажи акции', reply_markup=reply_markup)

    return ASK_STOCK_END


# Обработка состояния календаря, сохранение даты продажи,
async def sold_calendar_handler(update, context):
    selected, date = await process_calendar_selection(update, context)

    if selected:
        # Get bought date
        selected_date = date.strftime("%Y-%m-%d")
        chat_id = update.callback_query.message.chat_id
        _current_stock[chat_id][-1].update({'end': selected_date})

        await context.bot.send_message(
            chat_id=update.callback_query.from_user.id,
            text=f'Дата продажи: {date.strftime(selected_date)}',
            reply_markup=ReplyKeyboardRemove()
        )

        return await poll_stock_end(update, context)


# Обработка текущей акции, завершение и очищение используемого места в словарях при завершении регистрации
async def poll_stock_end(update: Update, _) -> int:
    # Get sold date
    message = update.callback_query.message
    chat_id = message.chat_id
    current_stock = _current_stock[chat_id][-1]

    await message.reply_text(text=f'''
        Операция записана:
        Наименование акции: {current_stock['name']},
        дата покупки {current_stock['start']},
        дата продажи {current_stock['end']}
    ''')

    # Ask for name if not already 5
    current_stocks = _current_stock[chat_id]
    if len(current_stocks) >= 0:
        # Конец регистрации
        stocks = _current_stock[chat_id]  # [[Имя, когда купил, когда продал], [Имя, ког..], [], [] ,[]]
        user = update.effective_user

        rating_points = _current_points[chat_id][RATING] / _poll_risk_amount
        risk_points = _current_points[chat_id][RISK] / _poll_rating_amount

        _current_points.pop(chat_id)
        _current_question.pop(chat_id)
        _current_stock.pop(chat_id)

        # JSON пользователя
        user_obj = {
            'user_id': user.id,
            'name': f'{user.first_name} {user.last_name}',
            'type_value': rating_points,
            'risk_value': risk_points
        }
        add_user(user_obj)

        # Акции в данном формате лежат в переменной (следующая строка ничего не делает)
        stocks

        return await go_to_menu(update.callback_query.message)

    return await poll_stock_name(message)


async def go_to_menu(message) -> int:
    reply_keyboard = _main_menu
    await message.reply_text(text='Главное меню', reply_markup=ReplyKeyboardMarkup(
        reply_keyboard, one_time_keyboard=True, input_field_placeholder='Выберите пункт:'
    ))

    return MAIN_MENU


async def main_menu(update: Update, _) -> int:
    message = update.message
    choice = message.text

    if [choice] not in _main_menu:
        reply_keyboard = _main_menu
        await message.reply_text(text='Главное меню', reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Выберите пункт:'
        ))

    user_id = update.effective_user.id
    button_response = ""

    if [choice] == _main_menu[0]:
        button_response = recommendations(user_id)
    elif [choice] == _main_menu[1]:
        button_response = optimalniy_portfel(user_id)
    else:
        button_response = leaderboard(user_id)

    await message.reply_text(text=button_response)

    return MAIN_MENU


########################################################################################################################
# Функции для кнопок
def optimalniy_portfel(user_id):
    risk_value = get_user(user_id)['risk_value']
    portfel = make_portfel(risk_value)
    return portfel


def recommendations(user_id):
    risk_value = get_user(user_id)['risk_value']
    rec = make_recommendation(risk_value)
    return rec


def leaderboard(user_id):
    invertors = get_top_investors(N=5)
    str_investors = '\n'.join([f'{value[0]} - {value[1]}' for value in invertors])
    return str_investors

########################################################################################################################


# Основная функция
def main() -> None:
    """Run bot."""
    # Создание объекта приложения для бота
    application = Application.builder().token("5551534877:AAEXVT8slH_z73LUvi7z-tG1vhFmlUxJ-a0").build()
    # Хендлер для беседы, действующей пошагово, для каждого состояния бот ждет ответ и запускает
    # соответствующую для текущего состояния функцию
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],  # Входная точка
        states={
            ASK_CATEGORY: [MessageHandler(filters.ALL, poll_category)],
            RESPONSE: [MessageHandler(filters.ALL, poll_response)],
            ASK_STOCK_BOUGHT: [MessageHandler(filters.ALL, poll_stock_bought)],
            ASK_STOCK_SOLD: [CallbackQueryHandler(bought_calendar_handler)],
            ASK_STOCK_END: [CallbackQueryHandler(sold_calendar_handler)],
            MAIN_MENU: [MessageHandler(filters.ALL, main_menu)],
        },
        fallbacks=[MessageHandler(filters.Regex("^Done$"), done)]
    )
    application.add_handler(conv_handler)

    # Запуск бесконечного цикла
    application.run_polling()


if __name__ == "__main__":
    main()
