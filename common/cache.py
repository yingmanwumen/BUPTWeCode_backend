import redis
import json as js
from conf import IPHOST


class MyRedis(object):
    def __init__(self, db, expire=None):
        self.redis = redis.Redis(host=IPHOST, port=6379, decode_responses=True, db=db)
        self.expire = expire

    def expire_key(self, name, permanent):
        if not permanent and self.expire:
            self.redis.expire(name, self.expire)

    def set(self, name, value, permanent=False):
        """
        :param name:
        :param value:
        :param permanent:
        :param json:
        :return: 插入成功返回true
        """
        res = self.redis.hmset(name, value)
        self.expire_key(name, permanent)
        return res

    def set_pointed(self, name, key, value, permanent=False, json=False):
        """
        :param name:
        :param key:
        :param value:
        :param permanent:
        :param json:
        :return: 如果返回的为0，说明只单纯修改了值，而没有新增值，如果大于零，说明新增了值
        """
        if json:
            value = js.dumps(value)
        res = self.redis.hset(name, key, value)
        self.expire_key(name, permanent)
        return res

    def get(self, name, json=False):
        res = self.redis.hgetall(name)
        if json:
            for key, value in res.items():
                res[key] = js.loads(value)
        return res

    def get_pointed(self, name, *args, json=False):
        res = self.redis.hmget(name=name, keys=args)
        if json:
            res = [s and js.loads(s) for s in res]
        return res

    def delete(self, *args):
        """
        :param args:
        :return: 返回删除的数量
        """
        return self.redis.delete(*args)

    def delete_pointed(self, name, *key):
        """
        :param name:
        :param key:
        :return: 返回删除的数量
        """
        return self.redis.hdel(name, *key)

    def list_push(self, name, *value, json=False):
        """
        往list中添加value
        :param name:
        :param value:
        :param json:
        :return:
        """
        if json:
            value = [js.dumps(val) for val in value]
        return self.redis.rpush(name, *value)

    def list_delete(self, name, end):
        """
        从下标为0开始删除一个列表,删到end之前的元素
        :param name:
        :param end:
        :return:
        """
        return self.redis.ltrim(name, start=end, end=-1)

    def list_get(self, name, json=False):
        """
        获取一个list
        :param name:
        :param json:
        :return:
        """
        res = self.redis.lrange(name, start=0, end=-1)
        if json:
            res = [js.loads(s) for s in res]
        return res

    def hincrby(self, name, key, amount=1, permanent=False):
        """
        将键为name的散列表中映射的值增加amount
        name：键名
        key：映射键名
        amount：增长量
        """
        res = self.redis.hincrby(name, key, amount)
        self.expire_key(name, permanent)
        return res

    def exists(self, key):
        """
        判断某个键是否存在
        """
        return self.redis.exists(key)

    def hexists(self, name, key):
        """
        判断hash是否有某个键
        """
        return self.redis.hexists(name, key)

    def ttl(self, name):
        """
        返回某个键的保活时间
        """
        return self.redis.ttl(name)


front_cache = MyRedis(db=0, expire=86400 * 30)
article_cache = MyRedis(db=1, expire=3600)
like_cache = MyRedis(db=2, expire=3600)
comment_cache = MyRedis(db=3, expire=3600)
rate_cache = MyRedis(db=4, expire=3600)
notify_cache = MyRedis(db=5, expire=3600)
cms_cache = MyRedis(db=15, expire=86400)
