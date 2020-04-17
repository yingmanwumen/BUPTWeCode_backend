from wtforms import StringField, IntegerField, FieldList, FormField
from wtforms.validators import InputRequired, Length, URL, Email, NumberRange
from common.baseform import BaseForm


class FeedBackForm(BaseForm):
    category = StringField(validators=[InputRequired(message="请填入反馈类型")])
    email = StringField(validators=[Email(message="邮箱格式错误")])
    content = StringField(validators=[InputRequired(message="请填写正文！"), Length(min=10, message="正文长度至少为10！")])
    images = FieldList(StringField(validators=[URL(message="图片地址格式不正确")]), max_entries=4)


class ReportForm(BaseForm):
    category = StringField(validators=[InputRequired(message="请填入举报类型")])
    reason = StringField(validators=[InputRequired(message="请填入举报理由")])
    link_id = StringField(validators=[InputRequired(message="缺失举报目标")])


class ArticleForm(BaseForm):
    board_id = IntegerField(validators=[InputRequired(message="缺失文章所属板块")])
    title = StringField(validators=[InputRequired(message="缺失文章标题"), Length(min=1, max=20, message="标题长度错误")])
    content = StringField(validators=[InputRequired(message="缺失文章内容"), Length(max=500, message="正文长度最多为1000")])
    images = FieldList(StringField(validators=[URL(message="图片格式不正确")]), max_entries=4)
    tags = FieldList(StringField(validators=[InputRequired(message="缺失tag标题"),
                                             Length(min=1, max=10, message="超出tag长度限制")]), max_entries=4)


class CommentForm(BaseForm):
    article_id = StringField(validators=[InputRequired(message="缺失文章id")])
    content = StringField(validators=[Length(max=500, message="评论字数不能超过500")])
    images = FieldList(StringField(validators=[URL(message="图片格式不正确")]), max_entries=4)


class SubCommentForm(BaseForm):
    comment_id = StringField(validators=[InputRequired(message="缺失评论id")])
    acceptor_id = StringField(validators=[InputRequired(message="缺失要回复的人")])
    content = StringField(validators=[InputRequired(message="缺失回复内容")])


class UserDataForm(BaseForm):
    username = StringField(validators=[InputRequired(message="请输入用户昵称"), Length(max=10)])
    gender = IntegerField(validators=[InputRequired(message="请输入性别"), NumberRange(min=0, max=2, message="性别错误")])
    avatar = StringField(validators=[InputRequired(message="请输入头像url"), URL(message="请输入正确格式的头像url")])
    signature = StringField(validators=[InputRequired(message="请输入签名"), Length(max=50)])


class WXUserInfoForm(BaseForm):
    # 由于出错，暂时不用解密数据
    # encryptedData = StringField(validators=[InputRequired(message="请输入加密数据encrypted data的值")])
    # iv = StringField(validators=[InputRequired(message="请输入解密向量iv的值")])
    avatarUrl = StringField(validators=[InputRequired(message="请输入头像url"), URL(message="请输入正确格式的头像url")])
    gender = IntegerField(validators=[InputRequired(message="请输入性别"), NumberRange(min=0, max=2, message="性别错误")])
    nickName = StringField(validators=[InputRequired(message="请输入用户昵称")])
