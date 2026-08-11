from app.domains.taxonomy.models import Category, Brand, Entity, Section
def serialize_taxonomy(t, counts=None, health=None):
    data = {'id': t.id, 'name': t.name, 'is_active': t.is_active}
    match t.__class__.__name__:
        case 'Category':
            data['hierarchy level'] = 'Leaf' if t.is_leaf else 'Parent'
        case 'Section':
            data['description'] = t.description
    if counts:
        for k, v in counts.items():
            data[k] = v
    if health:
        data['health'] = health
    return data
def _serialize_taxonomy_base(obj, **kwargs):
    data = {'id': obj.id, 'name': obj.name, 'slug': obj.slug, 'is_active': obj.is_active, 'sort_order': obj.sort_order}
    data.update(kwargs)
    return data
def serialize_category(c):
    return _serialize_taxonomy_base(c, is_leaf=c.is_leaf, parent_id=c.parent_id)
def serialize_brand(b):
    return _serialize_taxonomy_base(b, industry=b.industry, is_featured=b.is_featured)
def serialize_topic(t):
    return _serialize_taxonomy_base(t)
def serialize_section(s):
    return _serialize_taxonomy_base(s, description=s.description)
def serialize_attribute(a):
    return {'id': a.id, 'name': a.name, 'slug': a.slug, 'category_id': a.category_id, 'category_name': a.category.name if a.category else 'Global'}