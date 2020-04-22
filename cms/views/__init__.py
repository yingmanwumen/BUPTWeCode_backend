from .common_view import cms_common_bp
from .manage_view import cms_manager_bp
from .user_view import cms_user_bp
from .block_view import cms_block_bp

CMS_BPS = [cms_user_bp, cms_manager_bp, cms_common_bp, cms_block_bp]
