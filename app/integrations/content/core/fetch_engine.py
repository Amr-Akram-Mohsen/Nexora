import requests

from ..exceptions import (
    PipelineQuotaExceededError,
    PipelineTransientError,
    PipelineFatalError,
)
from app.shared.utils.logging import log_integration_error


def safe_get_json(
    session,
    url,
    *,
    params,
    timeout,
    logger,
    source_name,
):
    try:
        resp = session.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    except requests.exceptions.RequestException as e:
        status = getattr(e.response, "status_code", None)

        if status in (403, 429) or (status is None and "429" in str(e)):
            log_integration_error(logger, source_name, e)
            raise PipelineQuotaExceededError(f"{source_name} quota exceeded")

        log_integration_error(logger, source_name, e)
        raise PipelineTransientError(f"{source_name} network error: {e}") from e
    except Exception as e:
        log_integration_error(logger, source_name, e, query=params.get("q", ""))
        raise PipelineFatalError(f"{source_name} unexpected error: {str(e)}") from e
