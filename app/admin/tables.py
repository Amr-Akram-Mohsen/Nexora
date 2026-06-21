"""Admin CRUD table definitions used by Jinja table shells."""

CRUD_TABLES = {
    "users": {
        "id": "users",
        "preview_table": ["User", "Role", "Subscription", "Status", "Joined", "Last Active", "Engagement Score", "Actions"],
        "detailed_table": {
            "account info": ["id", "name", "email", "role", "status", "provider"],
            "security & auth": ["verified", "verified at", "password changed", "joined", "last active"],
            "engagement metrics": ["engagement profile", "engagement score", "views", "item clicks", "saves", "reactions", "comments", "shares", "recommendations shown"],
            "activity & interests": ["recent activity", "interests", "subscription"]
        }
    },
    "contents": {
        "id": "contents",
        "preview_table": [
            "Title",
            "Classification",
            "Engagement",
            "Published At",
            "Sources",
            "Status",
            "Actions",
        ],
        "detailed_table": {
            "content info": ["id", "title", "type", "taxonomy path"],
            "performance metrics": ["engagement score", "views", "likes", "dislikes", "comments", "shares", "saves"],
            "target specifics": ["platform", "channel", "author", "subreddit", "is scraped", "word count", "read time", "platform upvotes", "platform comments"],
            "quality & scoring": ["base score", "review score", "article quality score"],
            "taxonomy & targeting": ["intent", "gender", "price tier", "attributes"],
            "related metadata": ["related brands", "related topics", "mentioned products", "available sources", "primary source", "ingestion source"],
            "status & lifecycle": ["published at", "ingested at", "enrichment status", "last enrichment attempt", "status", "renderation status"]
        }
    },
    "items": {
        "id": "items",
        "preview_table": ["Name", "Category / Brand", "Price", "Store Count", "Sync Age", "Health", "Click Count", "Added", "Actions"],
        "detailed_table": {
            "product core mappings": ["id", "name", "category", "brand", "source", "added", "last synced"],
            "variants & availability": ["variants count", "store count", "price", "variant groups"],
            "performance metrics": ["engagement score", "views", "likes", "dislikes", "comments", "shares", "saves", "click count"],
            "content & quality": ["linked contents", "description", "rating", "review count", "images count", "specs count"]
        }
    },
    "sources": {
        "id": "sources",
        "preview_table": ["Name", "Volume", "Last Crawl", "Success Rate", "Failures", "Engagement", "Status", "Actions"],
        "detailed_table": {
            "source info": ["id", "name", "slug", "domain", "authority score", "status"],
            "performance & quality": ["avg quality score", "avg word count", "scrape coverage", "published date range"],
            "related metadata": ["article count"]
        }
    },
    "stores": {
        "id": "stores",
        "preview_table": [
            "Name",
            "Affiliate Network",
            "Product Count",
            "Clicks",
            "CTR",
            "Conversions",
            "Status",
            "Actions",
        ],
        "detailed_table": {
            "store info": ["id", "name", "slug", "website", "status", "affiliate network"],
            "commercial & localization": ["country", "currency", "api enabled", "product count"]
        }
    },
    "recommendations": {
        "id": "recs",
        "preview_table": ["Content Title", "Content Views", "Linked Items Count", "Linked Items IDs", "Actions"],
        "detailed_table": {
            "content info": ["id", "title", "type", "category", "views count"],
            "item info": ["id", "name", "category", "brand", "price", "store count", "totle clicks"],
        }
    },
    "categories": {
        "id": "categories",
        "preview_table": ["Name", "Status", "heirarchy level", "Actions"],
        "detailed_table": {
            "category info": ["id", "slug", "name", "status", "sort order", "heirarchy level", "parent name"],
            "related metadata": ["child categories", "content count", "item count", "top content"],
        }
    },
    "brands": {
        "id": "brands",
        "preview_table": ["Name", "Status", "Featured", "Actions"],
        "detailed_table": {
            "brand info": ["id", "slug", "name", "logo", 'industry', "featured", "status", "sort order"],
            "related metadata": ["content count", "item count", "top content"]
        }
    },
    "topics": {
        "id": "topics",
        "preview_table": ["Name", "Status", "Featured", "Actions"],
        "detailed_table": {
            "topic info": ["id", "slug", "name", "featured", "status", "sort order"],
            "related metadata": ["content count", "related categories", "related brands", "top content"],
        }
    },
    "sections": {
        "id": "sections",
        "preview_table": ["Name", "Status", "Description", "Actions"],
        "detailed_table": {
            "section info": ["id", "slug", "name", "description", "status", "sort order", "allowed filters"],
            "related metadata": ["content count", "category count", "related brands", "top content"],
        }
    },
    "comments": {
        "id": "comments",
        "preview_table": ["Title", "Type", "Comment", "Sentiment", "Likes", "Replies", "Thread?", "Date", "User", "Actions"],
        "detailed_table": {
            "comment content": ["id", "comment", "target title", "target type", "date"],
            "moderation": ["sentiment", "confidence", "sentiment distribution"],
            "engagement": ["likes", "dislikes", "shares", "replies count", "recent reactions"],
            "thread context": ["parent context", "latest replies", "target comments"],
            "author info": ["user id", "user name", "user email", "total comments"]
        }
    },
    "reactions": {
        "id": "reactions",
        "preview_table": ["Title", "Type", "Reaction Type", "Date", "User"],
    },
    "views": {
        "id": "views",
        "preview_table": ["Title", "Type", "Total Views", "Auth Views", "Anon Views", "Latest View"],
    },
    "clicks": {
        "id": "clicks",
        "preview_table": ["Product Name", "Category", "Brand", "Store", "Count", "Latest Click"],
        "detailed_table": {
            "link info": ["store name", "item name", "total clicks", "latest click"],
            "traffic geography": ["top countries"],
            "traffic sources": ["top referrers"]
        }
    },
    "saves": {
        "id": "saves",
        "preview_table": ["User", "Target", "Date"],
        "detailed_table": None
    },
    "shares": {
        "id": "shares",
        "preview_table": ["User", "Target", "Channel", "Date"],
        "detailed_table": None
    },
    "user_interests": {
        "id": "user_interests",
        "preview_table": [],
        "detailed_table": {
            "top affinities (algorithmic)": ["affinity 1", "affinity 2", "affinity 3", "affinity 4", "affinity 5"]
        }
    }
}

INSIGHTS_TABLES = {
    "top_opportunities": {
        "id": "top-opportunities",
        "preview_table": ["Rank", "Entity / Type", "Opportunity Score", "Reason"]
    },
    "content_strategy": {
        "id": "content-strategy",
        "preview_table": [
            "Rank", 
            "Target Entity", 
            "Reasoning & Asset Mapping", 
            {"html": '<th style="width: 60%; min-width: 500px;">Platform Content Strategies</th>'}
        ]
    },
    "social_distribution": {
        "id": "social-distribution",
        "preview_table": ["Platform", "Source Asset", "Status", "Publish Date", "Performance", "Actions"]
    },
    "performance_feedback": {
        "id": "feedback-evaluations",
        "preview_table": ["Platform / Title", "Expected CTR", "Actual CTR", "Evaluation Status", "Reason"]
    },
    "asset_mapping": {
        "id": "asset-mapping",
        "preview_table": ["Target Entity", "Score", "Existing Assets", "Content Gaps", "Actions"]
    },
    "coverage_matrix": {
        "id": "coverage-matrix",
        "preview_table": ["Category", "Content Count", "Product Count", "Coverage Quality", "Action"]
    },
    "brand_opportunities": {
        "id": "brand-opportunities",
        "preview_table": ["Brand", "Opportunity Score", "Related Content", "Products", "Growth Trend"]
    }
}

def get_inspect_table(table_name, data):
    """
    Generate an inspect_table dictionary by mapping the detailed_table schema 
    for a given domain against a provided data dictionary.
    
    `data` should be a dict where keys are the field labels defined in the schema.
    Values can be simple strings/numbers, or a dict like {"value": "html", "is_custom": True}
    """
    table = CRUD_TABLES.get(table_name, {}).get('detailed_table', {})
    mapped_table = {}
    for section_name, fields in table.items():
        mapped_table[section_name.title()] = []
        for field in fields:
            field_data = data.get(field)
            if isinstance(field_data, dict):
                mapped_table[section_name.title()].append({
                    "label": field.title(),
                    "value": field_data.get("value", "—"),
                    "is_custom": field_data.get("is_custom", False)
                })
            else:
                mapped_table[section_name.title()].append({
                    "label": field.title(),
                    "value": str(field_data) if field_data is not None else "—"
                })
    return mapped_table