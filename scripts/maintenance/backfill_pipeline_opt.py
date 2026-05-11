# scripts/maintenance/backfill_pipeline_opt.py
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from dotenv import load_dotenv
load_dotenv()

from main import app
from app.core.extensions import db
from app.domains.system.models import Source
from app.domains.content.models import Article
from app.shared.constants.taxonomy import TRUSTED_SOURCES

def backfill():
    with app.app_context():
        print("--- Backfilling Authority Scores ---")
        sources = Source.query.all()
        for s in sources:
            # Check if domain is in trusted list
            matched = False
            for ts in TRUSTED_SOURCES:
                if s.domain.lower() == ts["domain"].lower():
                    print(f"Updating {s.name}: {s.authority_score} -> {ts['score']}")
                    s.authority_score = ts["score"]
                    matched = True
                    break
            if not matched and s.authority_score == 5: # Old default was 5 in user prompt, but 50 in model
                s.authority_score = 50
        
        db.session.commit()
        print("Authority scores updated.")

        print("\n--- Materializing Primary Sources ---")
        articles = Article.query.all()
        for a in articles:
            if not a.primary_source_id:
                # print(f"Calculating primary source for: {a.title[:50]}...")
                a.update_primary_source()
        
        db.session.commit()
        print("Primary sources materialized.")

if __name__ == "__main__":
    backfill()
