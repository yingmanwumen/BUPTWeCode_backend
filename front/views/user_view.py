from flask import Blueprint, request, g
from flask_restful import Resource, Api, fields, marshal_with
from common.restful import *
from common.token import generate_token, login_required, Permission
from common.hooks import hook_front
from common.cache import notify_cache, like_cache
from common.models import Article
from ..forms import *
from sqlalchemy import func
from ..models import FrontUser, Notification, Report, FeedBack
from .article_view import QueryView as ArticleQueryView
from exts import db

import common.wxapi as wxapi

user_bp = Blueprint("user", __name__, url_prefix="/api/user")
api = Api(user_bp)


class WXLoginView(Resource):
    """
    小程序初始化的时候会请求这个接口，用于返回一个有效的token
    """
    resource_fields = {
        "code": fields.Integer,  # 状态码
        "message": fields.String,  # 状态描述
        "data": fields.Nested({
            "token": fields.String,
            "new": fields.Boolean,
            "info": fields.Nested({
                "avatar": fields.String,
                "username": fields.String,
                "signature": fields.String,
                "gender": fields.Integer,
                "uid": fields.String,
                "permission": fields.Integer
            }),
        })
    }

    def get(self):
        # 如果当前登陆状态还有效，直接返回token
        if g.login:
            # data.token = request.headers.get("Z-Token")
            # return Response.success(data=data)
            return self._generate_response(token=request.headers.get("Z-Token"))

        # 如果参数中没有code，返回参数错误
        code = request.args.get("code")
        if not code:
            return params_error(message="code错误")

        # 通过wxapi加code获取用户的open_id与session_key
        flag, resp = wxapi.get_user_session(code)

        # 如果wxapi请求失败，返回微信服务器错误, 否则拿到open_id和session_key
        if not flag:
            return server_error(message=resp.message)
        open_id, session_key = resp["openid"], resp["session_key"]

        # 通过open_id获取用户, 如果用户表中没有说明是新用户, 并且添加这个新用户
        user = FrontUser.query.filter_by(open_id=open_id).first()
        new_user = user is None
        if not user:
            user = FrontUser(open_id=open_id)
            db.session.add(user)
            db.session.commit()

        # 通过uid生成token
        token = generate_token(user.id)

        # 将uid, open_id, session_key存到缓存中
        cache_data = {
            "open_id": open_id,
            "session_key": session_key,
            "uid": user.id
        }
        res = g.cache.set(name=token, value=cache_data)

        # 如果缓存失败，返回缓存错误
        if not res:
            return server_error(message="缓存过程中发生错误")

        # 返回token值
        return self._generate_response(token, user, new_user)

    @marshal_with(resource_fields)
    def _generate_response(self, token, user, new_user):
        resp = Data()
        resp.token = token
        resp.new = new_user
        resp.info = Data()
        resp.info.permission = user.permission
        resp.info.avatar = user.avatar
        resp.info.username = user.username
        resp.info.signature = user.signature
        resp.info.gender = user.gender
        resp.info.uid = user.id
        return Response.success(data=resp)


class WXUserInfoView(Resource):
    resource_fields = {
        "code": fields.Integer,
        "message": fields.String,
        "data": fields.Nested({
            "avatar": fields.String,
            "username": fields.String,
            "signature": fields.String,
            "gender": fields.Integer,
            "uid": fields.String
        })
    }

    method_decorators = [login_required(Permission.VISITOR)]

    @marshal_with(resource_fields)
    def get(self):
        # 如果没有登陆信息，返回登陆错误
        if not g.login:
            return Response.auth_error(message="没有登陆或者登陆信息已经失效")

        data = Data()
        data.avatar = g.user.avatar
        data.username = g.user.username
        data.signature = g.user.signature
        data.gender = g.user.gender
        data.uid = g.user.id
        return Response.success(data=data)

    def post(self):
        # 如果没有登陆信息，返回登陆错误
        if not g.login:
            return auth_error(message="没有登陆或者登陆信息已经失效")

        form = WXUserInfoForm(request.form)
        data = Data()

        # 如果表单验证失败，返回表单验证失败错误
        if not form.validate():
            return params_error(message=form.get_error())

        # # 获取表单的加密数据, 并且通过wxapi获得解密数据
        # encrypted_data = form.encryptedData.data
        # iv = form.iv.data
        # session_key, = g.cache.get_pointed(g.token, "session_key")
        # res = wxapi.get_user_info(session_key=session_key, encrypted_data=encrypted_data, iv=iv)
        # # print(res)
        # username, avatar_url, gender = res["nickName"], res["avatarUrl"], res["gender"]
        # 由于出错，暂时不用解密验证数据

        username = form.nickName.data
        avatar = form.avatarUrl.data
        gender = form.gender.data % 2   # 不设置性别默认女性

        # 通过新的解密数据, 更新用户信息
        user = g.user
        user.username = username
        user.avatar = avatar
        user.gender = gender
        db.session.commit()

        return self.generate_response(user)

    @marshal_with(resource_fields)
    def generate_response(self, user):
        resp = Data()
        resp.avatar = user.avatar
        resp.username = user.username
        resp.signature = user.signature
        resp.gender = user.gender
        resp.uid = user.id
        return Response.success(data=resp)


class ProfileView(Resource):

    method_decorators = [login_required(Permission.VISITOR)]

    def post(self):
        """
        修改用户信息
        """
        form = UserDataForm(request.form)
        if not form.validate():
            return params_error(message=form.get_error())

        username = form.username.data
        signature = form.signature.data
        gender = form.gender.data
        avatar = form.avatar.data.split("?imageView2")[0]

        g.user.username = username
        g.user.signature = signature
        # 对用户头像做预处理
        g.user.avatar = avatar + g.IMAGE_ICON
        g.user.gender = gender

        db.session.commit()
        return success()


class FollowView(Resource):

    method_decorators = [login_required(Permission.VISITOR)]

    def get(self):
        user_id = request.args.get("user_id")
        if not user_id:
            return params_error(message="缺失用户id")
        user = FrontUser.query.get(user_id)
        if not user:
            return source_error(message="用户不存在")
        g.user.follow(user)
        return success()


class UnFollowView(Resource):

    method_decorators = [login_required(Permission.VISITOR)]

    def get(self):
        user_id = request.args.get("user_id")
        if not user_id:
            return params_error(message="缺失用户id")
        user = FrontUser.query.get(user_id)
        if not user:
            return source_error(message="用户不存在")
        g.user.unfollow(user)
        return success()


class LikesView(Resource):

    method_decorators = [login_required(Permission.VISITOR)]

    def get(self):
        user_likes = g.user.get_all_appreciation(cache=like_cache, attr="likes")
        article_ids = [article_id for article_id in user_likes.keys() if user_likes[article_id]["status"]]
        articles = Article.query.filter(Article.id.in_(article_ids), Article.status == 1)
        total = articles.with_entities(func.count(Article.id)).scalar()
        articles = articles.order_by(Article.created.desc())
        return ArticleQueryView.generate_response(articles, total)


class PostsView(Resource):

    method_decorators = [login_required(Permission.VISITOR)]

    def get(self):
        offset = request.args.get("offset", 0, type=int)
        limit = request.args.get("limit", 10, type=int)
        articles = g.user.articles.filter_by(status=1)
        total = articles.with_entities(func.count(Article.id)).scalar()
        articles = articles.order_by(Article.created.desc())[offset: offset + limit]
        return ArticleQueryView.generate_response(articles, total)


class NotifyView(Resource):
    resource_fields = {
        "code": fields.Integer,
        "message": fields.String,
        "data": fields.Nested({
            "notifications": fields.List(fields.Nested({
                "sender": fields.Nested({
                    "sender_id": fields.String,
                    "username": fields.String,
                    "avatar": fields.String,
                    "gender": fields.Integer,
                }),
                "visited": fields.Boolean,
                "sender_content": fields.String,
                "category": fields.Integer,
                "acceptor_content": fields.String,
                "link_id": fields.String,
                "notify_id": fields.String
            })),
            "new": fields.Integer,
            "total": fields.Integer
        })
    }

    method_decorators = [login_required(Permission.VISITOR)]

    def get(self):
        offset = request.args.get("offset", 0, type=int)
        limit = request.args.get("limit", 10, type=int)
        notifications = Notification.query.filter_by(acceptor_id=g.user.id).order_by(Notification.created.desc())
        total = notifications.with_entities(func.count(Notification.id)).scalar()
        notifications = notifications[offset:offset+limit]
        return self._generate_response(total, notifications)

    @marshal_with(resource_fields)
    def _generate_response(self, total, notifications):
        resp = Data()
        resp.total = total
        resp.notifications = []
        for notification in notifications:
            data = Data()
            data.visited = notification.visited == 1
            data.sender_content = notification.sender_content
            data.acceptor_content = notification.acceptor_content
            data.link_id = notification.link_id
            data.notify_id = notification.id
            data.category = notification.category

            data.sender = Data()
            data.sender.username = notification.sender.username
            data.sender.sender_id = notification.sender.id
            data.sender.avatar = notification.sender.avatar
            data.sender.username = notification.sender.username

            resp.notifications.append(data)
        resp.new = int(g.user.get_new_notifications_count(notify_cache))
        db.session.commit()
        return Response.success(data=resp)


class UnNotifyView(Resource):

    method_decorators = [login_required(Permission.VISITOR)]

    def get(self):
        notify_id = request.args.get("notify_id")
        if not notify_id:
            return params_error(message="缺失notify_id")
        notify = Notification.query.get(notify_id)

        if not notify:
            return source_error(message="消息不存在")

        if notify.acceptor_id != g.user.id:
            return auth_error(message="您无权进行此操作")

        if notify.visited:
            return deny_error(message="该消息已经读过了")

        notify.visited = 1
        g.user.notification_increase(notify_cache, amount=-1)
        db.session.commit()
        return success()


class RotationView(Resource):

    method_decorators = [login_required(Permission.VISITOR)]

    def get(self):
        res = int(g.user.get_new_notifications_count(notify_cache))
        return success(dict(new=res))


class ReportView(Resource):

    method_decorators = [login_required(Permission.VISITOR)]

    def post(self):
        form = ReportForm(request.form)
        if not form.validate():
            return params_error(message=form.get_error())

        category = form.category.data
        reason = form.reason.data
        link_id = form.link_id.data

        report = Report.query.filter_by(link_id=link_id, user_id=g.user.id).first()
        if report:
            return deny_error(message="您已经举报过了")

        report = Report(category=category, reason=reason, link_id=link_id)
        report.user = g.user
        db.session.add(report)
        db.session.commit()
        return success()


class FeedBackView(Resource):
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

        try:
            feedback.send_mail(subject="微码小窝", recipients=[email],
                               body="微码小窝已经收到了您的反馈，我们将努力解决这个问题，"
                                    "感谢您的使用(=^0^=)")
        except BaseException as e:
            print(e)
            return server_error(message="在发送邮件或保存数据的过程中出现了错误，请您稍后重试")

        return success()


api.add_resource(WXLoginView, "/login/", endpoint="front_user_login_vx")
api.add_resource(WXUserInfoView, "/user/", endpoint="wx_user")
api.add_resource(ProfileView, "/profile/", endpoint="front_user_profile")
api.add_resource(LikesView, "/likes/", endpoint="front_user_likes")
api.add_resource(PostsView, "/posts/", endpoint="front_user_posts")
# api.add_resource(FollowView, "/follow/", endpoint="front_user_follow")
# api.add_resource(UnFollowView, "/unfollow/", endpoint="front_user_unfollow")
api.add_resource(NotifyView, "/notify/", endpoint="front_user_notify")
api.add_resource(UnNotifyView, "/unnotify/", endpoint="front_user_unnotify")
api.add_resource(RotationView, "/rotation/", endpoint="front_user_rotation")
api.add_resource(ReportView, "/report/", endpoint="front_user_report")
api.add_resource(FeedBackView, "/feedback/", endpoint="front_user_feedback")


@user_bp.before_request
def before_request():
    hook_front()

