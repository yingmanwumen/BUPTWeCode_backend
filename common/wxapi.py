from common.wxdecrypt.WXBizDataCrypt import WXBizDataCrypt
from conf import APP_ID, APP_SECRET_KEY, code2Session_URL
from common.exceptions import DIYException
import requests

wx_session = requests.session()


def get_user_info(session_key, encrypted_data, iv):
    return WXBizDataCrypt.get_info(app_id=APP_ID, session_key=session_key, encrypted_data=encrypted_data, iv=iv)


def get_user_session(code):
    try:
        wx_login_url = code2Session_URL.format(APP_ID, APP_SECRET_KEY, code)
        resp = wx_session.get(url=wx_login_url)
        data = resp.json()
        errcode = data.get("errcode", False)
        print(data)
        if not errcode:
            return True, data
        elif errcode == -1:
            raise DIYException("微信服务器繁忙，请稍后尝试")
        elif errcode == 40029:
            raise DIYException("code为无效值")
        elif errcode == 45001:
            raise DIYException("该用户请求频率过高，请稍后尝试")
        else:
            raise DIYException(data["errmsg"])
    except DIYException as e:
        return False, e
    except Exception as e:
        return False, DIYException("发生其他类型的错误")
