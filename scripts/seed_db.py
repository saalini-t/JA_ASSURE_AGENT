import os
import sys
import json
from pathlib import Path

# Add backend to path
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.database.session import SessionLocal, engine
from app.models.entities import (
    Base,
    ContentQueue,
    Competitor,
    Lead,
    LessonLearned,
    Feedback
)

def seed():
    print("--- Initializing Database Tables ---")
    Base.metadata.create_all(bind=engine)
    
    seed_file = current_dir.parent / "data" / "seed" / "seed_data.json"
    if not seed_file.exists():
        print(f"Error: Seed file {seed_file} not found.")
        return

    with open(seed_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    db = SessionLocal()
    try:
        # Seed Competitors if empty
        if db.query(Competitor).count() == 0:
            print("Seeding Competitors...")
            for c in data.get("competitors", []):
                db.add(Competitor(**c))
        else:
            print("Competitors already seeded.")

        # Seed Lessons Learned if empty
        if db.query(LessonLearned).count() == 0:
            print("Seeding Lessons Learned...")
            for l in data.get("lessons_learned", []):
                db.add(LessonLearned(**l))
        else:
            print("Lessons Learned already seeded.")

        # Seed Content Queue if empty
        created_items = []
        if db.query(ContentQueue).count() == 0:
            print("Seeding Content Queue...")
            for q in data.get("content_queue", []):
                item = ContentQueue(**q)
                db.add(item)
                created_items.append(item)
            db.flush()

            print("Seeding Feedback...")
            for fb in data.get("feedbacks", []):
                c_idx = fb.get("content_index", 0)
                content_id = created_items[c_idx].id if c_idx < len(created_items) else created_items[0].id
                db.add(Feedback(
                    content_id=content_id,
                    reason_tag=fb["reason_tag"],
                    notes=fb["notes"],
                    original_content=fb["original_content"],
                    corrected_content=fb.get("corrected_content")
                ))
        else:
            print("Content Queue already contains items.")

        # Seed Leads if empty
        if db.query(Lead).count() == 0:
            print("Seeding Leads...")
            for ld in data.get("leads", []):
                db.add(Lead(**ld))
        else:
            print("Leads already seeded.")

        db.commit()
        print("--- Database successfully updated / seeded! ---")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed()
