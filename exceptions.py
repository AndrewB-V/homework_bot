class MessageError(Exception):
    """Ошибка отправки сообщения."""

    pass


class TokenError(Exception):
    """Ошибка в переменных окружения."""

    pass


class UndocumentedStatusError(Exception):
    """Недокументированный статус."""

    pass
