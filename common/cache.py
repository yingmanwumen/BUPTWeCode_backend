import redis
from conf import IPHOST


class MyRedis(object):
    def __init__(self, db, default_expire, long_expire):
        self.redis = redis.Redis(host=IPHOST, port=6379, decode_responses=True, db=db)
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

    def list_push(self, name, *value):
        """
        往list中添加value
        :param name:
        :param value:
        :return:
        """
        return self.redis.rpush(name, *value)

    def list_delete(self, name, end):
        """
        从下标为0开始删除一个列表,删到end之前的元素
        :param name:
        :param start:
        :return:
        """
        return self.redis.ltrim(name, start=end, end=-1)

    def list_get(self, name):
        """
        获取一个list
        :param name:
        :return:
        """
        return self.redis.lrange(name, start=0, end=-1)

    def incrby(self, name, key, amount=1):
        """
        将键为name的散列表中映射的值增加amount
        name：键名
        key：映射键名
        amount：增长量
        """
        return self.redis.hincrby(name, key, amount)

    def exists(self, key):
        """
        判断某个键是否存在
        """
        return self.redis.exists(key)

    def sorted_add(self, name, mapping):
        """
        在有序集合中添加数据，若已存在则更新顺序
        name：键名
        mapping:将value和score组装成的dict{value: score}
        返回添加的数据的个数
        """
        return self.redis.zadd(name, mapping)

    def sorted_del(self, key, *values):
        """
        删除key中的元素value
        返回删除的元素的个数
        """
        return self.redis.zrem(key, *values)

    def sorted_range(self, key, start, end, withscores=False):
        """
        返回从start到end的元素（score从大到小）
        withscores：是否带有score
        """
        return self.redis.zrevrange(key, start, end, withscores)

    def sorted_card(self, key):
        """
        返回key中的元素个数
        """
        return self.redis.zcard(key)
