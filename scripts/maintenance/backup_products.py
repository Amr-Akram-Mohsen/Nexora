import os
import sys
import json
import logging
from sqlalchemy import select

# Ensure we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core import create_app
from app.core.extensions import db
from app.domains.item.models import Item, ItemVariant, ItemImage, ItemStoreLink, ItemSpecification, Store
from app.domains.taxonomy.models import Category, Brand, Section
from app.shared.serializers import serialize_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def backup_data():
    app = create_app()
    with app.app_context():
        logger.info("Starting backup process...")
        
        # 1. Fetch used Categories (including parents)
        logger.info("Extracting used categories...")
        items = db.session.execute(select(Item)).scalars().all()
        used_category_ids = set([item.category_id for item in items if item.category_id])
        
        # We need to fetch the parents of these categories too
        all_categories = {c.id: c for c in db.session.execute(select(Category)).scalars().all()}
        categories_to_keep = set()
        
        for cid in used_category_ids:
            current_id = cid
            while current_id and current_id in all_categories:
                categories_to_keep.add(current_id)
                current_id = all_categories[current_id].parent_id
                
        category_data = []
        for cid in categories_to_keep:
            c = all_categories[cid]
            category_data.append({
                "id": c.id,
                "name": c.name,
                "slug": c.slug,
                "external_uri": c.external_uri,
                "parent_id": c.parent_id,
                "is_active": c.is_active,
                "sort_order": c.sort_order,
                "is_leaf": c.is_leaf
            })
            
        # 2. Fetch used Brands
        logger.info("Extracting used brands...")
        used_brand_ids = set([item.brand_id for item in items if item.brand_id])
        brands = db.session.execute(select(Brand).filter(Brand.id.in_(used_brand_ids))).scalars().all() if used_brand_ids else []
        brand_data = [{
            "id": b.id,
            "name": b.name,
            "slug": b.slug,
            "industry": b.industry,
            "is_active": b.is_active
        } for b in brands]
        
        # 3. Fetch Sections (Keep all sections as they are structural)
        logger.info("Extracting sections...")
        sections = db.session.execute(select(Section)).scalars().all()
        section_data = [{
            "id": s.id,
            "name": s.name,
            "slug": s.slug,
            "description": s.description,
            "is_active": s.is_active,
            "sort_order": s.sort_order
        } for s in sections]
        
        # 4. Fetch Stores
        logger.info("Extracting stores...")
        stores = db.session.execute(select(Store)).scalars().all()
        store_data = [{
            "id": s.id,
            "name": s.name,
            "slug": s.slug,
            "website": s.website,
            "country": s.country,
            "currency": s.currency,
            "affiliate_network": s.affiliate_network,
            "logo_url": s.logo_url
        } for s in stores]
        
        # 5. Fetch Items and relations
        logger.info("Extracting items and relationships...")
        item_data = []
        for item in items:
            variants = []
            for v in item.variants:
                v_data = {
                    "id": v.id,
                    "title": v.title,
                    "sku": v.sku,
                    "attributes": v.attributes,
                    "is_default": v.is_default,
                    "price": float(v.price) if v.price else None,
                    "old_price": float(v.old_price) if v.old_price else None,
                    "currency": v.currency,
                    "images": [],
                    "store_links": []
                }
                for img in v.images:
                    v_data["images"].append({
                        "image_url": img.image_url,
                        "position": img.position
                    })
                for link in v.store_links:
                    v_data["store_links"].append({
                        "store_id": link.store_id,
                        "external_item_id": link.external_item_id,
                        "original_url": link.original_url,
                        "affiliate_url": link.affiliate_url,
                        "price": float(link.price) if link.price else None,
                        "old_price": float(link.old_price) if link.old_price else None,
                        "currency": link.currency,
                        "availability": link.availability
                    })
                variants.append(v_data)
                
            specs = []
            for spec in item.specifications:
                specs.append({
                    "category": spec.category,
                    "spec_json": spec.spec_json
                })
                
            item_images = []
            for img in item.images:
                if not img.variant_id: # Only top-level images not tied to a variant
                    item_images.append({
                        "image_url": img.image_url,
                        "position": img.position
                    })
                    
            item_data.append({
                "id": item.id,
                "name": item.name,
                "slug": item.slug,
                "description": item.description,
                "rating": item.rating,
                "review_count": item.review_count,
                "item_type": item.item_type,
                "source_type": item.source_type,
                "source_id": item.source_id,
                "category_id": item.category_id,
                "brand_id": item.brand_id,
                "card_type": item.card_type,
                "searchable_attributes": item.searchable_attributes,
                "variants": variants,
                "images": item_images,
                "specifications": specs
            })
            
        final_backup = {
            "categories": category_data,
            "brands": brand_data,
            "sections": section_data,
            "stores": store_data,
            "items": item_data
        }
        
        backup_path = os.path.join(os.path.dirname(__file__), "product_backup.json")
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(final_backup, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Successfully backed up {len(item_data)} items, {len(category_data)} categories, and {len(brand_data)} brands to {backup_path}")

if __name__ == "__main__":
    backup_data()
