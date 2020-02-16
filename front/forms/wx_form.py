from wtforms import StringField
from wtforms.validators import InputRequired
from common.baseform import BaseForm


class WXLoginForm(BaseForm):
    code = StringField(validators=[InputRequired("请输入微信申请到的code值")])


class WXUserInfoForm(BaseForm):
    encryptedData = StringField(validators=[InputRequired("请输入加密数据encrypted data的值")])
    iv = StringField(validators=[InputRequired("请输入解密向量iv的值")])
