from flask import request


def get_client_ip():
    # behind a proxy? fall back to remote_addr
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if ip:
        return ip.split(",")[0].strip()
    return None


def get_country():
    return request.cookies.get("country", "")
