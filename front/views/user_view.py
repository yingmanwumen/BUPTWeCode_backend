from flask import Blueprint, request, g
from flask_restful import Resource, Api, fields, marshal_with
from common.restful import *
from common.token import generate_token, login_required, Permission
from common.hooks import hook_front
from ..forms import WXUserInfoForm, WXLoginForm
from sqlalchemy import func
from ..models import FrontUser, Notification
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
            "token": fields.String
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
        return self._generate_response(token)

    @marshal_with(resource_fields)
    def _generate_response(self, token):
        resp = Data()
        resp.token = token
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
        gender = form.gender.data

        # 通过新的解密数据, 更新用户信息
        user = g.user
        user.username = username
        user.avatar = avatar
        user.gender = gender
        db.session.commit()

        return self._generate_response(user)

    @marshal_with(resource_fields)
    def _generate_response(self, user):
        resp = Data()
        resp.avatar = user.avatar
        resp.username = user.username
        resp.signature = user.signature
        resp.gender = user.gender
        resp.uid = user.id
        return Response.success(data=resp)


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
                "link_id": fields.String
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
        new = 0
        for notification in notifications:
            data = Data()
            data.visited = notification.visited == 1
            data.sender_content = notification.sender_content
            data.acceptor_content = notification.acceptor_content
            data.link_id = notification.link_id
            data.category = notification.category
            if not notification.visited:
                notification.visited = 1
                new += 1

            data.sender = Data()
            data.sender.username = notification.sender.username
            data.sender.sender_id = notification.sender.id
            data.sender.avatar = notification.sender.avatar
            data.sender.username = notification.sender.username

            resp.notifications.append(data)
        resp.new = new
        db.session.commit()
        return Response.success(data=resp)


class RotationView(Resource):

    method_decorators = [login_required(Permission.VISITOR)]

    def get(self):
        return success()


api.add_resource(WXLoginView, "/login/", endpoint="front_user_login_vx")
api.add_resource(WXUserInfoView, "/user/", endpoint="wx_user")
api.add_resource(FollowView, "/follow/", endpoint="front_user_follow")
api.add_resource(UnFollowView, "/unfollow/", endpoint="front_user_unfollow")
api.add_resource(NotifyView, "/notify/", endpoint="front_user_notify")
api.add_resource(RotationView, "/rotation/", endpoint="front_user_rotation")


@user_bp.before_request
def before_request():
    hook_front()

