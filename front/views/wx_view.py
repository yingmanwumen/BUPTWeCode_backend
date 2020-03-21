from flask import Blueprint, request, g
from flask_restful import Resource, Api, fields, marshal_with
from common.restful import *
from common.token import generate_token, login_required, Permission
from common.hooks import hook_front
from ..forms.wx_form import WXLoginForm, WXUserInfoForm
from ..models import FrontUser
from exts import db

import common.wxapi as wxapi

wx_bp = Blueprint("wx", __name__, url_prefix="/api/wx")
api = Api(wx_bp)


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
        res = g.cache.set(name=token, val=cache_data, permanent=True)

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
            "gender": fields.Integer
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
        return Response.success(data=resp)


api.add_resource(WXLoginView, "/login/", endpoint="wx_login")
api.add_resource(WXUserInfoView, "/user/", endpoint="wx_user")


@wx_bp.before_request
def before_request():
    hook_front(no_user_msg="登陆状态已过期", no_token_msg="新用户")

