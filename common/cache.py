import redis


class MyRedis(object):
    def __init__(self, db, default_expire, long_expire):
        self.redis = redis.Redis(host="47.100.26.65", port=6379, decode_responses=True, db=db)
        self.default_expire = default_expire
        self.long_expire = long_expire

    def _expire_key(self, name, permanent=False):
        """
        如果time有值，设置key的过期时间为time，否则为默认值self.expire_time
        :param name:
        :param time:
        :return:
        """
        if not permanent:
            self.redis.expire(name, self.default_expire)
        else:
            self.redis.expire(name, self.long_expire)

    def set(self, name, val, permanent=False):
        """
        :param name:
        :param val:
        :param permanent:
        :return: 插入成功返回true
        """
        res = self.redis.hmset(name, val)
        self._expire_key(name, permanent)
        return res

    def set_pointed(self, name, key, value, permanent=False):
        """
        :param name:
        :param key:
        :param value:
        :param permanent:
        :return: 如果返回的为0，说明只单纯修改了值，而没有新增值，如果大于零，说明新增了值
        """
        res = self.redis.hset(name, key, value)
        self._expire_key(name, permanent)
        return res

    def get(self, name):
        return self.redis.hgetall(name)

    def get_pointed(self, name, *args):
        return self.redis.hmget(name=name, keys=args)

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


if __name__ == '__main__':
    r = MyRedis(0, 86400)
    a = {"name": "menmensaa", "age": 16, "length": 18, "token": "12345667", "c": "d"}
    print(r.set("a", a))
    print(r.get_pointed("a", "age", "length", "aaa"))
    print(r.set_pointed("a", "age", 100))
    print(r.get("a"))
    print(r.delete_pointed("a", "c", "token"))
    print(r.delete("a"))

