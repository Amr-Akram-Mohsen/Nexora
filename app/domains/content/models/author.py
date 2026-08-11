from app.core.extensions import db
class Author(db.Model):
    __tablename__ = 'authors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    slug = db.Column(db.String(255), unique=True, index=True)
    url = db.Column(db.Text, nullable=True)
    uri = db.Column(db.String(255), nullable=True)
    type = db.Column(db.String(50), nullable=True)
    is_agency = db.Column(db.Boolean, default=False, nullable=False)
    icon_url = db.Column(db.Text, nullable=True)
    aliases = db.Column(db.JSON, default=list)
    @classmethod
    def get_or_create(cls, session, name, uri=None, url=None, type_val=None, is_agency=False):
        from app.shared.utils.slug import generate_slug
        if not name:
            return None
        slug = generate_slug(name)
        existing = session.query(cls).filter_by(slug=slug).first()
        if existing:
            if uri and (not existing.uri):
                existing.uri = uri
            if url and (not existing.url):
                existing.url = url
            return existing
        parts = name.split()
        if len(parts) >= 2:
            base_name = ' '.join(parts[:2])
            potential_matches = session.query(cls).filter(cls.name.ilike(f'{base_name}%')).all()
            for p in potential_matches:
                p_name = p.name.lower()
                n_name = name.lower()
                def is_valid_boundary(long_str, short_str):
                    if len(long_str) == len(short_str):
                        return True
                    char_after = long_str[len(short_str)]
                    return not char_after.isalpha()
                if p_name.startswith(n_name) and is_valid_boundary(p_name, n_name) or (n_name.startswith(p_name) and is_valid_boundary(n_name, p_name)):
                    aliases = p.aliases or []
                    if len(n_name) > len(p_name):
                        if name not in aliases:
                            aliases.append(name)
                            from sqlalchemy.orm.attributes import flag_modified
                            flag_modified(p, 'aliases')
                    else:
                        if p.name not in aliases:
                            aliases.append(p.name)
                            from sqlalchemy.orm.attributes import flag_modified
                            flag_modified(p, 'aliases')
                        p.name = name
                        p.slug = slug
                    p.aliases = aliases
                    if uri and (not p.uri):
                        p.uri = uri
                    if url and (not p.url):
                        p.url = url
                    return p
        new_author = cls(name=name, slug=slug, url=url, uri=uri, type=type_val, is_agency=is_agency, aliases=[])
        session.add(new_author)
        session.flush()
        return new_author