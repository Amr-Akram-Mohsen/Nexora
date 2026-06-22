from main import app
from flask import render_template
from app.admin.recommendations import _fetch_matches_page

with app.test_request_context('/'):
    try:
        total, pages, serialized = _fetch_matches_page(1, 25, '', None, None)
        display_items = []
        for r in serialized:
            display_items.append({
                "id": r["content_id"],
                "content-title": f"{r['content_title']} (#{r['content_id']})",
                "widget-impressions": "{:,}".format(r["widget_impressions"]),
                "widget-ctr": r["widget_ctr"],
                "last-active": r["last_active"],
                "linked-items-count": r["linked_items_count"],
                "linked-items-list": [i['id'] for i in r["items"]]
            })
        html = render_template("admin/components/_rows.html", items=display_items, domain_type="rec")
        print("Success! HTML Length:", len(html))
    except Exception as e:
        import traceback
        traceback.print_exc()
