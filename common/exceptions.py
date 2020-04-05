from pymysql.err import OperationalError


class DIYException(Exception):
    def __init__(self, message):
        self.message = message


class ArgumentsError(Exception):
    def __init__(self, message):
        self.message = message
