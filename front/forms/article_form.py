from wtforms import StringField, IntegerField, FieldList
from wtforms.validators import InputRequired, Length
from common.baseform import BaseForm


class ArticleForm(BaseForm):
    board_id = IntegerField(validators=[InputRequired(message="缺失文章所属板块")])
    title = StringField(validators=[InputRequired(message="缺失文章标题"), Length(min=1, max=20, message="标题长度错误")])
    content = StringField(validators=[InputRequired(message="缺失文章内容")])
    imageList = StringField()

    def validate(self):
        if not super().validate():
            return False
        res = self.imageList.data.split(",")
        if len(res) > 4:
            return False
        return True
