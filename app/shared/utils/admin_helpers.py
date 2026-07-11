"""
Shared utilities and workflows for the Admin dashboard.

This module provides common patterns for deleting models, executing paginated queries,
and running workflows that require a session commit.
"""
from app.core.extensions import db

def execute_admin_workflow(action_func, *args, session=None, **kwargs):
    """
    Standard wrapper that executes a domain action and commits the session if it succeeds.
    """
    if session is None:
        session = db.session
    result = action_func(*args, **kwargs)
    if result:
        session.commit()
    return result

def delete_model_workflow(model_class, model_id, name_attr=None, session=None):
    """
    Standardizes fetching, deleting, committing, and returning a result or specific attribute.
    """
    if session is None:
        session = db.session
        
    obj = session.get(model_class, model_id)
    if not obj:
        return False if not name_attr else None
        
    name = getattr(obj, name_attr) if name_attr else None
    session.delete(obj)
    session.commit()
    
    return name if name_attr else True

def execute_paginated_query(stmt, count_stmt, page, per_page, session=None):
    """
    Handles offset calculation, total counts, page math, and returns (products, total, pages).
    Returns elements as a tuple: (products, total, pages)
    """
    import math
    if session is None:
        session = db.session
        
    total = session.scalar(count_stmt) or 0
    offset = (page - 1) * per_page
    products = session.execute(stmt.limit(per_page).offset(offset)).all()
    pages = math.ceil(total / per_page) if per_page else 1
    
    return products, total, pages

def toggle_model_flag_workflow(model_class, model_id, flag_attr, target_value=None, session=None):
    """
    Standardizes toggling a boolean field or setting it to a target value.
    """
    if session is None:
        session = db.session
        
    obj = session.get(model_class, model_id)
    if not obj:
        return None
        
    if target_value is not None:
        setattr(obj, flag_attr, target_value)
    else:
        current_val = getattr(obj, flag_attr)
        setattr(obj, flag_attr, not current_val)
        
    session.commit()
    return obj
