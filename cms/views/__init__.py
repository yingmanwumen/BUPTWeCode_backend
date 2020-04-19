from .common_view import cms_common_bp
from .manage_view import cms_manager_bp
from .user_view import cms_user_bp

CMS_BPS = [cms_user_bp, cms_manager_bp, cms_common_bp]
