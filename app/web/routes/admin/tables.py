"""Admin CRUD table definitions used by Jinja table shells."""

CRUD_TABLES = {
    "users": {
        "id": "users",
        "preview_table": ["User", "Role", "Subscription", "Status", "Joined", "Last Active", "Engagement Score", "Tier", "Actions"],
        "detailed_table": {
            "account info": ["id", "name", "email", "role", "status", "provider"],
            "security & auth": ["verified", "verified at", "verification sent", "password changed", "joined", "last active"],
            "engagement metrics": ["engagement tier", "engagement profile", "engagement score", "views", "item clicks", "saves", "reactions", "comments", "shares", "recommendations shown", "recommendations clicked"],
            "activity & interests": ["recent activity", "subscription"]
        }
    },
    "subscribers": {
        "id": "subscribers",
        "preview_table": ["Email", "Status", "User Link", "Subscribed At", "Unsubscribed At", "Actions"],
        "detailed_table": {
            "subscription info": ["email", "status", "subscribed at", "unsubscribed at", "confirmed at"],
            "user link": ["user id", "user name", "engagement score"]
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
            "related metadata": ["related brands", "related topics", "mentioned products", "available sources", "primary source", "acquired via"],
            "status & lifecycle": ["published at", "ingested at", "enrichment status", "last enrichment attempt", "status", "rendering status"]
        }
    },
    "items": {
        "id": "items",
        "preview_table": ["Name", "Category / Brand", "Price", "Store Count", "Sync Age", "Health", "Click Count", "Added", "Actions"],
        "detailed_table": {
            "product core mappings": ["id", "name", "category", "brand", "source", "added", "last synced"],
            "variants & availability": ["variants count", "store count", "price", "price spread", "variant groups"],
            "performance metrics": ["engagement score", "views", "likes", "dislikes", "comments", "shares", "saves", "click count"],
            "content & quality": ["linked contents", "description", "rating", "review count", "images count", "specs count"]
        }
    },
    "sources": {
        "id": "sources",
        "preview_table": ["Name", "Content Volume", "Freshness", "Engagement", "Status", "Actions"],
        "detailed_table": {
            "source info": ["id", "name", "slug", "domain", "authority score", "status"],
            "performance & quality": ["avg quality score", "avg word count", "scrape coverage", "published date range"],
            "ingestion breakdown": ["channels", "last fetch", "success count", "failure count", "consecutive failures"],
            "content distribution": ["article count", "video count", "post count", "categories covered"],
            "article pipeline": ["pending", "enriching", "complete", "failed"],
            "engagement breakdown": ["total views", "total likes", "total saves", "total comments"],
            "multi-source attribution": ["primary attribution count", "secondary attribution count"]
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
            "Active Links",
            "Sync Age",
            "OOS Rate",
            "Avg Commission",
            "Status",
            "Actions",
        ],
        "detailed_table": {
            "store info": ["id", "name", "slug", "website", "status", "affiliate network"],
            "commercial & localization": ["country", "currency", "api enabled", "product count"],
            "link health": ["total links", "active links", "inactive links", "never synced", "stale links (7d)", "out of stock", "avg sync age (days)", "last synced at"],
            "affiliate & commission": ["feed enabled", "network slug", "program count", "avg commission rate", "max commission rate", "links with commission", "links without commission", "links with tracking code"],
            "pricing summary": ["min price", "avg price", "max price", "links with discount", "avg discount %", "links with null price", "currency mix"]
        }
    },
    "recommendations": {
        "id": "recs",
        "preview_table": ["Content Title", "Content Views", "Linked Items Count", "Linked Items IDs", "Actions"],
        "detailed_table": {
            "content info": ["id", "title", "type", "category", "views count"],
            "item info": ["id", "name", "category", "brand", "price", "store count", "total clicks"],
        }
    },
    "categories": {
        "id": "categories",
        "preview_table": ["Name", "Status", "Hierarchy Level", "Content Count", "Product Count", "Health Status", "Actions"],
        "detailed_table": {
            "category info": ["id", "slug", "name", "status", "sort order", "hierarchy level", "parent name"],
            "related metadata": ["child categories", "content count", "item count"],
        }
    },
    "brands": {
        "id": "brands",
        "preview_table": ["Name", "Industry", "Status", "Content Count", "Product Count", "Health Status", "Actions"],
        "detailed_table": {
            "brand info": ["id", "slug", "name", "logo", 'industry', "featured", "status", "sort order"],
            "related metadata": ["content count", "item count"]
        }
    },
    "topics": {
        "id": "topics",
        "preview_table": ["Name", "Status", "Content Count", "Category Count", "Health Status", "Actions"],
        "detailed_table": {
            "topic info": ["id", "slug", "name", "featured", "status", "sort order"],
            "related metadata": ["content count", "related categories", "related brands"],
        }
    },
    "sections": {
        "id": "sections",
        "preview_table": ["Name", "Description", "Status", "Content Count", "Category Count", "Health Status", "Actions"],
        "detailed_table": {
            "section info": ["id", "slug", "name", "description", "status", "sort order", "allowed filters"],
            "related metadata": ["content count", "category count", "related brands"],
        }
    },
    "attributes": {
        "id": "attributes",
        "preview_table": ["Name", "Category", "Content Count", "Health", "Actions"],
        "detailed_table": {
            "attribute info": ["id", "slug", "name", "category"],
            "related metadata": ["content count"],
        }
    },
    "gender_facets": {
        "id": "gender_facets",
        "preview_table": ["Name", "Content Count", "Health", "Actions"],
        "detailed_table": {
            "facet info": ["id", "slug", "name"],
            "related metadata": ["content count"],
        }
    },
    "intent_facets": {
        "id": "intent_facets",
        "preview_table": ["Name", "Content Count", "Health", "Actions"],
        "detailed_table": {
            "facet info": ["id", "slug", "name"],
            "related metadata": ["content count"],
        }
    },
    "price_tier_facets": {
        "id": "price_tier_facets",
        "preview_table": ["Name", "Content Count", "Health", "Actions"],
        "detailed_table": {
            "facet info": ["id", "slug", "name"],
            "related metadata": ["content count"],
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
            {"label": "Platform Content Strategies", "class": "admin-table-th-wide"}
        ]
    },
    "social_distribution": {
        "id": "social-distribution",
        "preview_table": ["Platform", "Source Asset", "Status", "Publish Date", "Performance", "Link", "Actions"]
    },
    "performance_feedback": {
        "id": "feedback-evaluations",
        "preview_table": ["Platform / Title", "Expected CTR", "Actual CTR", "Evaluation Status", "Decay Rate", "Reason"]
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
    Values can be simple strings/numbers, or a dict passing through structured data.
    """
    table = CRUD_TABLES.get(table_name, {}).get('detailed_table', {})
    mapped_table = {}
    for section_name, fields in table.items():
        mapped_table[section_name.title()] = []
        for field in fields:
            if field not in data:
                continue
            field_data = data[field]
            
            if field_data is None:
                mapped_table[section_name.title()].append({
                    "label": field.title(),
                    "value": "—"
                })
            elif isinstance(field_data, dict):
                entry = {"label": field.title()}
                entry.update(field_data)
                if "value" not in entry:
                    entry["value"] = "—"
                mapped_table[section_name.title()].append(entry)
            elif isinstance(field_data, list):
                mapped_table[section_name.title()].append({
                    "label": field.title(),
                    "value": field_data,
                    "is_list": True
                })
            else:
                mapped_table[section_name.title()].append({
                    "label": field.title(),
                    "value": str(field_data)
                })
        # Remove empty sections
        if not mapped_table[section_name.title()]:
            del mapped_table[section_name.title()]
    return mapped_table
