from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from functools import wraps
from common.exceptions import *

db = SQLAlchemy()
mail = Mail()


def connect_wrapper(func):
    @wraps(func)
    def inner(*args, **kwargs):
        try:
            res = func(*args, **kwargs)
        except (ConnectionError, TimeoutError):
            return False, "缓存炸了"
        except OperationalError:
            return False, "数据库炸了"
        except Exception:
            return False, "未知错误"
        return True, res
    return inner
