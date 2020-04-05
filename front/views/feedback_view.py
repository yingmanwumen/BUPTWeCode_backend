from flask import Blueprint, request, g
from flask_restful import Resource, Api
from flask_mail import Message
from exts import db, mail
from common.restful import *
from common.hooks import hook_front
from common.token import login_required, Permission
from common.models import FeedBack
from ..forms import FeedBackForm


feedback_bp = Blueprint("feedback", __name__, url_prefix="/api/feedback")
api = Api(feedback_bp)


def send_mail(subject, recipients, body):
    """
    发送邮件
    """
    if not isinstance(recipients, list):
        recipients = list(recipients)
    message = Message(subject=subject, recipients=recipients, body=body)
    mail.send(message)


class PutView(Resource):
    """
    前台接收反馈视图函数。
    post请求
    """

    method_decorators = [login_required(Permission.VISITOR)]

    def post(self):
        """
        :category   反馈类型
        :email      反馈者邮箱
        :content    反馈正文
        :images     图像，小于等于4张
        """
        form = FeedBackForm.from_json(request.json)
        if not form.validate():
            return params_error(message=form.get_error())
        category = form.category.data
        email = form.email.data
        content = form.content.data
        images = ",".join([image + g.IMAGE_PIC for image in form.images.data])

        feedback = FeedBack(category=category, content=content,
                            email=email, images=images)
        db.session.add(feedback)
        db.session.commit()

        # try:
        #     send_mail(subject="微码小窝", recipients=[email],
        #               body="微码小窝已经收到了您的反馈，我们将努力解决这个问题，"
        #                    "感谢您的使用(=^0^=)")
        # except BaseException as e:
        #     if g.debug:
        #         print(e)
        #     return server_error(message="在发送邮件或保存数据的过程中出现了错误，请您稍后重试")

        return success()


api.add_resource(PutView, "/submit/", endpoint="front_feedback_add")


@feedback_bp.before_request
def before_request():
    hook_front()
