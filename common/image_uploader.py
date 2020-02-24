from conf import QINIU_ACCESS_KEY, QINIU_SECRET_KEY
import qiniu


q = qiniu.Auth(access_key=QINIU_ACCESS_KEY, secret_key=QINIU_SECRET_KEY)
bucket = "bupt-wecode"


def generate_uptoken():
    return q.upload_token(bucket=bucket)
