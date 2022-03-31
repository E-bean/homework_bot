class HTTPStatusCodeIncorrect(Exception):
    def __str__(self):
        return 'Status code is not 200'


class EmptyList(Exception):
    def __str__(self):
        return 'The list is empty'


class NeedToken(Exception):
    def __str__(self):
        return 'I need a token, token a token is what I need'
