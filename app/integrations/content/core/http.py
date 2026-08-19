import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_session = None


def get_http_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": "Nexora Content Fetcher"})

        retries = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(
            max_retries=retries,
            pool_connections=10,
            pool_maxsize=10,
        )
        _session.mount("https://", adapter)
    return _session


get_session = get_http_session
_get_session = get_http_session

