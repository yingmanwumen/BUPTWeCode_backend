import os
from conf import USERNAME, PWD, IPHOST, PORT, DBNAME

DEBUG = True

DB_URI = "mysql+pymysql://{username}:{pwd}@{host}:{port}/{db}?charset=utf8mb4".format(username=USERNAME, pwd=PWD, host=IPHOST, port=PORT, db=DBNAME)
SQLALCHEMY_DATABASE_URI = DB_URI
SQLALCHEMY_TRACK_MODIFICATIONS = False

# SECRET_KEY = os.urandom(24)
SECRET_KEY = b')\xf6\x7f\xb3\x82iC\xce\xc5\x18\x84\xf2\xab\x12V\x9e\x80\xabKg\xa6\x12\xdcL'

DEFAULT_EXPIRE_TIME_FOR_TOKEN = 3600  # 默认token过期时间
LONG_EXPIRE_TIME_FOR_TOKEN = 86400  # 较长的token过期时间
