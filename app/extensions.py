from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_caching import Cache
from app.utils.request import get_client_ip


mail = Mail()
csrf = CSRFProtect()
cache = Cache()

limiter = Limiter(key_func=get_client_ip)

