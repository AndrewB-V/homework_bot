import os
import time
import logging

import requests
import telegram
import dotenv

dotenv.load_dotenv()

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_TIME = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f'OAuth {PRACTICUM_TOKEN}'}

VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания."
}


logging.basicConfig(
    level=logging.DEBUG,
    filename='logger.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s'
)
logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler()
)


class MessageError:
    """Ошибка отправки сообщения."""

    pass


class TokenError:
    """Ошибка в переменных окружения."""

    pass


class UndocumentedStatusError(Exception):
    """Недокументированный статус."""

    pass


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        logger.info("Сообщение отправлено")
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logger.error(f'Ошибка {error} при отправке сообщения')
        raise MessageError("Ошибка при отправке сообщения")


def get_api_answer(current_timestamp):
    """Получение данных с API YP."""
    timestamp = current_timestamp or int(time.time())
    params = {"from_date": timestamp}
    try:
        logger.info("отправляем api-запрос")
        response = requests.get(
            ENDPOINT, params=params, headers=HEADERS
        )

    except ValueError as error:
        logger.error(f'{error}: не получили api-ответ')
        raise error
    error_message = (
        f'Проблемы соединения с сервером'
        f'ошибка {response.status_code}'
    )
    if response.status_code == requests.codes.ok:
        return response.json()
    logger.error(error_message)
    raise TypeError(error_message)


homework_error = "Домашняя работа не найдена!"
dict_error = "dict KeyError"


def check_response(response):
    """Проверка данные api."""
    if isinstance(response, dict) is False:
        raise TypeError("api answer is not dict")
    try:
        homework_list = response["homeworks"]
    except KeyError:
        logger.error(dict_error)
        raise KeyError(dict_error)
    try:
        homework_list[0]
    except IndexError:
        logger.error(homework_error)
        raise IndexError(homework_error)
    return homework_list


def parse_status(homework):
    """Выделяет статут домашней работы."""
    homework_name = homework.get("homework_name")
    homework_status = homework.get("status")
    if homework_status is not None:
        verdict = VERDICTS[homework_status]
    else:
        raise KeyError("Ошибка словаря")
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка наличия токенов."""
    variables_data = {
        "PRACTICUM_TOKEN": PRACTICUM_TOKEN,
        "TELEGRAM_TOKEN": TELEGRAM_TOKEN,
        "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID
    }
    no_value = [
        var_name for var_name, value in variables_data.items() if not value
    ]
    if no_value:
        logger.critical(
            f'Отсутствует обязательная/ые переменная/ые окружения: {no_value}.'
            'Программа принудительно остановлена.'
        )
        return False
    logger.info("Необходимые переменные окружения доступны.")
    return True


env_error = "Ошибка в переменных окружения"


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical(env_error)
        raise TokenError(env_error)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time() - 6048000)
    tmp_status = None
    errors = True
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            homework_status = homework.get("status")
            if homework_status != tmp_status:
                tmp_status = homework_status
                message = parse_status(homework)
                send_message(bot, message)
            else:
                logger.debug("Статус ДЗ не изменился")
                current_timestamp = homework.get("current timestamp")
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if str(error) != errors:
                send_message(bot, error)
                errors = str(error)
            logger.error(error)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
