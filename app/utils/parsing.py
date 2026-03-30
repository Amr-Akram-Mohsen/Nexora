from app.constants import TargetType, INTERACTION_TYPE
def parse_target_type(value: str) -> str:
    if value not in (TargetType.ARTICLE, TargetType.PRODUCT):
        raise ValueError("Invalid target type")
    return value

def parse_interaction_type(value: str) -> str:
    if value not in (INTERACTION_TYPE.REACT, INTERACTION_TYPE.SAVE, INTERACTION_TYPE.COMMENT):
        raise ValueError("Invalid interaction type")
    return value

