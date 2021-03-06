import redis

from util.GetConfig import cf
from util.error import PoolEmptyError
from random import choice

REDIS_HOST = cf.get("REDIS", "REDIS_HOST")
REDIS_PORT = cf.get("REDIS", "REDIS_PORT")
REDIS_KEY = cf.get("REDIS", "REDIS_KEY")
REDIS_PASSWORD = None

MIN_SCORE = int(cf.get("Pool", "MIN_SCORE"))
MAX_SCORE = int(cf.get("Pool", "MAX_SCORE"))
INITIAL_SCORE = int(cf.get("Pool", "INITIAL_SCORE"))


class Singleton(type):
    """
    Singleton Metaclass
    """
    _inst = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._inst:
            cls._inst[cls] = super(Singleton, cls).__call__(*args)
        return cls._inst[cls]


class RedisClient(object):
    """
    redis client class
    """

    def __init__(self):
        """
        decode_responses True is string
        """
        self.db = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, decode_responses=True)

    def add(self, proxy, score=INITIAL_SCORE):
        """
        add proxy
        元素及其分数值加入到有序集中
        :param proxy: proxy
        :param score: score
        :return: result
        """
        if not self.db.zscore(REDIS_KEY, proxy):
            return self.db.zadd(REDIS_KEY, score, proxy)

    def random(self):
        """
        按降序优先级，没有则返回异常
        随机分数取 = zrangebyscore
        从大到小取 = zrevrange
        :return: random proxy
        """
        result = self.db.zrangebyscore(REDIS_KEY, MAX_SCORE, MAX_SCORE)  # 先取满分代理

        if len(result):
            return choice(result)
        else:
            # 没有满分代理，再按排名取
            result = self.db.zrevrange(REDIS_KEY, MIN_SCORE, MAX_SCORE)
            if len(result):
                return choice(result)
            else:
                raise PoolEmptyError
                pass

    def decrease(self, proxy):
        """
        扣分 -1 ;  <最小值 直接删除
        zincrby: 通过传递一个负数值 increment ，让分数减去相应的值
        :param proxy:
        :return: score
        """
        score = self.db.zscore(REDIS_KEY, proxy)
        if score and score > MIN_SCORE:
            print('代理', proxy, '状态评分', score, '减1')
            return self.db.zincrby(REDIS_KEY, proxy, -1)
        else:
            print(f"\033[0;37;40m 代理{proxy}当前分数{score}移除\033[0m")
            return self.db.zrem(REDIS_KEY, proxy)

    def exists(self, proxy):
        """
        是否存在
        :param proxy:
        :return: True and False
        """
        return not self.db.zscore(REDIS_KEY, proxy) is None

    def max(self, proxy):
        """
        set max score
        :param proxy:
        :return: ok
        """
        print('代理', proxy, '可用，设置为', MAX_SCORE)
        return self.db.zadd(REDIS_KEY, MAX_SCORE, proxy)

    def count(self):
        """
        get numb
        :return: 总数
        """
        return self.db.zcard(REDIS_KEY)

    def all(self):
        """
        get all proxy
        :return:
        """
        return self.db.zrangebyscore(REDIS_KEY, MIN_SCORE, MAX_SCORE)

    def batch(self, start, stop):
        """
        批量获取
        :param start: 开始索引
        :param stop: 结束索引
        :return: 代理列表
        """
        return self.db.zrevrange(REDIS_KEY, start, stop - 1)


if __name__ == '__main__':
    r = RedisClient()
    r.add("127.0.0.1:8888", 10)
