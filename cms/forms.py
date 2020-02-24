from wtforms import StringField, BooleanField, IntegerField
from wtforms.validators import InputRequired, Length, URL, NumberRange
from common.baseform import BaseForm


class LoginForm(BaseForm):
    username = StringField(validators=[InputRequired(message="请输入用户名")])
    password = StringField(validators=[InputRequired(message="请输入密码")])
    remember = BooleanField(validators=[InputRequired(message="是否需要记住您？")])


class ProfileForm(BaseForm):
    displayName = StringField(validators=[Length(max=8, min=0, message="最大长度为8")])
    desc = StringField(validators=[Length(max=100, min=0, message="最大长度为100")])


class BoardForm(BaseForm):
    name = StringField(validators=[Length(max=20, message="最大长度为20"), InputRequired(message="请输入板块名称")])
    desc = StringField(validators=[Length(max=200, message="最大长度为200"), InputRequired(message="请输入板块描述")])
    avatar_url = StringField(validators=[URL(message="请输入正确格式的图片地址")])
    board_id = IntegerField(validators=[NumberRange(min=0), InputRequired(message="请输入板块id")])
    status = IntegerField(validators=[InputRequired(message="请输入板块status"), NumberRange(min=0, max=1)])
