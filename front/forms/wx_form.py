from wtforms import StringField, IntegerField
from wtforms.validators import InputRequired, NumberRange, URL
from common.baseform import BaseForm


class WXLoginForm(BaseForm):
    code = StringField(validators=[InputRequired(message="请输入微信申请到的code值")])


class WXUserInfoForm(BaseForm):
    # 由于出错，暂时不用解密数据
    # encryptedData = StringField(validators=[InputRequired(message="请输入加密数据encrypted data的值")])
    # iv = StringField(validators=[InputRequired(message="请输入解密向量iv的值")])
    avatarUrl = StringField(validators=[InputRequired(message="请输入头像url"), URL(message="请输入正确格式的头像url")])
    gender = IntegerField(validators=[InputRequired(message="请输入性别"), NumberRange(min=0, max=2, message="性别错误")])
    nickName = StringField(validators=[InputRequired(message="请输入用户昵称")])
