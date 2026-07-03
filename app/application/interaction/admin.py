from app.domains.interaction.service.inspect import get_comment_inspect_metrics, get_link_clicks_metrics
from app.domains.interaction.serializers import serialize_comment_inspect_dto, serialize_link_clicks_dto

def get_comment_inspect_workflow(comment_id: int):
    metrics = get_comment_inspect_metrics(comment_id)
    if not metrics:
        return None
        
    dto = serialize_comment_inspect_dto(metrics)
    return {"comment_dto": dto}

def get_link_clicks_workflow(link_id: int):
    metrics = get_link_clicks_metrics(link_id)
    if not metrics:
        return None
        
    dto = serialize_link_clicks_dto(metrics)
    return {"link_clicks_dto": dto}
