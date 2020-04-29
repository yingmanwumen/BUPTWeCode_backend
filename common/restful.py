from flask import jsonify


def raw_resp(code, message="", data={}):
    return jsonify(code=code, message=message, data=data)


def token_error(message, data={}):
    return raw_resp(code=499, message=message, data=data)


def block_error(message, data={}):
    return raw_resp(code=498, message=message, data=data)


def success(data={}):
    return raw_resp(code=200, message="OK", data=data)


def params_error(data={}, message="参数错误"):
    return raw_resp(code=400, message=message, data=data)


def auth_error(data={}, message="未授权"):
    return raw_resp(code=401, message=message, data=data)


def deny_error(data={}, message="服务器拒绝操作"):
    return raw_resp(code=403, message=message, data=data)


def source_error(data={}, message="无法定位资源"):
    return raw_resp(code=404, message=message, data=data)


def server_error(data={}, message="服务器内部错误"):
    return raw_resp(code=500, message=message, data=data)


class BaseResponse(object):
    def __init__(self, **kwargs):
        self.code = kwargs.get("code")
        self.message = kwargs.get("message") or ""
        self.data = kwargs.get("data") or {}


class Data(object):
    def __init__(self):
        pass


class Response(object):
    @staticmethod
    def raw_resp(code, message, data={}):
        return BaseResponse(code=code, message=message, data=data)

    @staticmethod
    def token_error(message="token字段错误", data={}):
        return BaseResponse(code=499, message=message, data=data)

    @staticmethod
    def success(data={}):
        return Response.raw_resp(code=200, message="OK", data=data)

    @staticmethod
    def params_error(message, data={}):
        return Response.raw_resp(code=400, message=message, data=data)

    @staticmethod
    def auth_error(message, data={}):
        return Response.raw_resp(code=401, message=message, data=data)

    @staticmethod
    def deny_error(message, data={}):
        return Response.raw_resp(code=403, message=message, data=data)

    @staticmethod
    def source_error(message, data={}):
        return Response.raw_resp(code=404, message=message, data=data)

    @staticmethod
    def server_error(message, data={}):
        return Response.raw_resp(code=500, message=message, data=data)
