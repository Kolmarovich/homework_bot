class IncorrectResponseCode(Exception):
    """Не удалось получить ответ от API."""

    pass


class UndocumentedStatus(Exception):
    """Недокументированный статус домашней работы."""

    pass


class EmptyResponse(Exception):
    """Пустой ответ API."""

    pass


class MessageError(Exception):
    """Не удалось отправить сообщение."""

    pass
