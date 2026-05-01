from random import shuffle
from app.domains.item.service import get_search_items
from app.domains.content.service import get_search_contents

def search_workflow(query):
    """
    Orchestrates search results from both content and items.
    """
    if not query:
        return []

    items = get_search_items(query)
    contents = get_search_contents(query)
    
    results = items + contents
    shuffle(results)
    
    return results
