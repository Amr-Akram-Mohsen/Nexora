"""Admin CRUD table definitions used by Jinja table shells."""

CRUD_TABLES = {
    "users": {
        "id": "users",
        "columns": ["User", "Role", "Status", "Joined", "Last Active", "Engagement Score", "Actions"],
    },
    "contents": {
        "id": "contents",
        "columns": [
            {"html": '<input type="checkbox" id="select-all-contents" />'},
            "Content Details",
            "Metadata & Health",
            "Engagement",
            "Published",
            "Actions",
        ],
    },
    "items": {
        "id": "items",
        "columns": ["Product Details", "Price", "Engagement", "Added", "Actions"],
    },
    "sources": {
        "id": "sources",
        "columns": ["Name", "Volume", "Last Crawl", "Success Rate", "Failures", "Engagement", "Status", "Actions"],
    },
    "stores": {
        "id": "stores",
        "columns": [
            "Merchant Name",
            "Affiliate Network",
            "Product Count",
            "Clicks",
            "CTR",
            "Conversions",
            "Status",
            "Actions",
        ],
    },
    "recommendations": {
        "id": "recs",
        "columns": ["Content", "Views", "Linked Item", "Clicks", "Actions"],
    },
    "categories": {
        "id": "categories",
        "columns": ["Name", "Status", "Leaf", "Actions"],
    },
    "brands": {
        "id": "brands",
        "columns": ["Name", "Status", "Actions"],
    },
    "topics": {
        "id": "topics",
        "columns": ["Name", "Status", "Actions"],
    },
    "sections": {
        "id": "sections",
        "columns": ["Name", "Description", "Status"],
    },
    "comments": {
        "id": "comments",
        "columns": ["Comment Preview", "User", "Target", "Sentiment", "Date", "Actions"],
    },
    "reactions": {
        "id": "reactions",
        "columns": ["ID", "Target", "Type", "User", "Date"],
    },
    "views": {
        "id": "views",
        "columns": ["Target", "Target Type", "Views Count", "Latest View"],
    },
    "clicks": {
        "id": "clicks",
        "columns": ["Item", "Destination", "Click Count", "Latest Click"],
    },
    "saves": {
        "id": "saves",
        "columns": ["Target", "Target Type", "User", "Save Date"],
    },
}
