from .cache import like_cache, article_cache, rate_cache, comment_cache, notify_cache
from .models import Article, Comment
from front.models import FrontUser, Rate, Like, Notification
from exts import db, scheduler
from functools import wraps
import json
import time


class logger():
    def __init__(self, info):
        self.info = info

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwargs):
            print("*" * 10)
            print("开始【{}】...".format(self.info))
            t1 = time.time()
            with scheduler.app.app_context():
                count = func(*args, **kwargs)
            t2 = time.time()
            print("【{}】执行完毕...总耗时【{:.2f}】s...一共更新了【{}】条数据...".format(self.info, t2-t1, count))
            print("*" * 10)
        return inner


@logger(info="保存文章浏览量数据")
def save_views():
    count = 0
    views = article_cache.get("views")
    article_cache.delete("views")
    for article_id, view in views.items():
        article = Article.query.get(article_id)
        if article:
            article.views += int(view)
            count += 1
    db.session.commit()
    return count


@logger(info="保存文章点赞数据")
def save_likes():
    queue = like_cache.get("queue")
    like_cache.delete("queue")
    count = 0
    for like_id, value in queue.items():
        value = json.loads(value)
        like = Like.query.get(like_id)
        if like:
            like.status = value["status"]
            count += 1
        elif value["status"]:
            article_id, user_id = value["id"], value["user_id"]
            article = Article.query.get(article_id)
            if article:
                user = FrontUser.query.get(user_id)
                if user:
                    like = Like()
                    like.user = user
                    like.article = article

                    if user.id != article.author_id:
                        notification = Notification(category=1, link_id=article_id,
                                                    sender_content="赞了你的帖子", acceptor_content=article.title)
                        notification.acceptor = article.author
                        notification.sender = user
                        db.session.add(notification)
                        article.author.add_new_notification(notify_cache)

                    db.session.add(like)
                    count += 1
    db.session.commit()
    return count


@logger(info="保存评论点赞数据")
def save_rates():
    queue = rate_cache.get("queue")
    rate_cache.delete("queue")
    count = 0
    for rate_id, value in queue.items():
        value = json.loads(value)
        rate = Rate.query.get(rate_id)
        if rate:
            rate.status = value["status"]
            count += 1
        elif value["status"]:
            comment_id, user_id = value["id"], value["user_id"]
            comment = Comment.query.get(comment_id)
            if comment:
                user = FrontUser.query.get(user_id)
                if user:
                    rate = Rate()
                    rate.user = user
                    rate.comment = comment

                    if user.id != comment.author_id:
                        notification = Notification(category=2, link_id=comment_id,
                                                    sender_content="赞了你的评论", acceptor_content=comment.content)
                        notification.acceptor = comment.author
                        notification.sender = user
                        db.session.add(notification)
                        comment.author.add_new_notification(notify_cache)

                    db.session.add(rate)
                    count += 1
    db.session.commit()
    return count

