from ..hooks import connect_wrapper


@connect_wrapper
def get_user_likes(cache, user):
    """
    从缓存中获取用户的点赞文章列表，如果没有获得到，会从数据库中将其数据放到缓存中
    :param cache:
    :param user:
    :return:
    """
    user_likes = cache.list_get(user.id)
    if not user_likes:
        orm_user_likes = user.likes.all()
        user_likes = [like.article_id for like in orm_user_likes]
        if user_likes:
            cache.list_push(user.id, *user_likes)
    return user_likes
