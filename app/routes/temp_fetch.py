@bp.route("/run-fetch")
def run_fetch():
    from app.scrapers.runner import run_article_fetch
    run_article_fetch()
    return "done"
