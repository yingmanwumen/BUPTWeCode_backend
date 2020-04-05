import redis
import json as js
from conf import IPHOST


class MyRedis(object):
    def __init__(self, db, expire=None):
        self.redis = redis.Redis(host=IPHOST, port=6379, decode_responses=True, db=db)
        self.expire = expire

    def _expire_key(self, name, permanent):
        if not permanent and self.expire:
            self.redis.expire(name, self.expire)

    def set(self, name, value, permanent=False, json=False):
        """
        :param name:
        :param value:
        :param permanent:
        :param json:
        :return: 插入成功返回true
        """
        if json:
            value = js.dumps(value)
        res = self.redis.hmset(name, value)
        self._expire_key(name, permanent)
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
        self._expire_key(name, permanent)
        return res

    def get(self, name, json=False):
        res = self.redis.hgetall(name)
        if json:
            res = js.loads(res)
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


if __name__ == '__main__':
    r = MyRedis(db=2)
    like_id = {
        "article_id": "aaa",
        "status": 1
    }
    r.set_pointed(name="kkk", key="like_id", value=like_id, json=True)
    # print(r.get_pointed("kkk", "like_id", json=True)[0]["status"] == 1)