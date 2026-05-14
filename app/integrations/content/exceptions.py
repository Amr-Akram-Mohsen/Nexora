class PipelineError(Exception):
    """Base class for all pipeline-related errors."""
    pass

class PipelineFatalError(PipelineError):
    """
    Critical errors that should stop the entire pipeline immediately.
    Examples: Database connection failure, code bugs, schema mismatches.
    """
    pass

class PipelineTransientError(PipelineError):
    """
    Transient errors that might be retryable.
    Examples: API timeouts, temporary network issues, rate limits.
    """
    pass

class PipelineQuotaExceededError(PipelineTransientError):
    """Specific error for when an API quota is exhausted."""
    pass
