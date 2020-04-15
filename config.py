import os
from conf import *

# DEBUG = True

DB_URI = "mysql+pymysql://{username}:{pwd}@{host}:{port}/{db}?charset=utf8mb4".format(username=USERNAME, pwd=PWD, host=IPHOST, port=PORT, db=DBNAME)
SQLALCHEMY_DATABASE_URI = DB_URI
SQLALCHEMY_TRACK_MODIFICATIONS = False

# SECRET_KEY = os.urandom(24)
SECRET_KEY = b')\xf6\x7f\xb3\x82iC\xce\xc5\x18\x84\xf2\xab\x12V\x9e\x80\xabKg\xa6\x12\xdcL'

IMAGE_ICON = "?imageView2/1/w/64/h/64/q/75"
IMAGE_PIC = "?imageView2/0/q/75"

SCHEDULER_API_ENABLED = True
JOBS = [
    # {
    #     "id": "test_job_id",
    #     "func": "common.schedule:test_job",
    #     "trigger": "interval",
    #     "seconds": 10
    # },
    {
        "id": "save_views",
        "func": "common.schedule:save_views",
        "trigger": "cron",
        "minute": "0,15,30,45"
    },
    {
        "id": "save_likes",
        "func": "common.schedule:save_likes",
        "trigger": "cron",
        "minute": "5,20,35,50"
    },
    {
        "id": "save_rates",
        "func": "common.schedule:save_rates",
        "trigger": "cron",
        "minute": "10,25,40,55"
    },
]
