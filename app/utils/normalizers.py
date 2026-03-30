def normalize_attributes(attrs):
    if not attrs:
        return {}

    return {
        str(k).strip().lower(): str(v).strip().lower()
        for k, v in attrs.items()
    }
