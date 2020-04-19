from .user_view import user_bp
from .common_view import common_bp
from .article_view import article_bp
from .board_view import board_bp
from .comment_view import comment_bp

FRONT_BPS = [user_bp, common_bp, article_bp, board_bp, comment_bp]
