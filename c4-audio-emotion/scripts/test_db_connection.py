"""
Day 2 check: can we connect to the team MongoDB, write a document and read it back?

Run from the c4-audio-emotion folder:
    venv\\Scripts\\python -m scripts.test_db_connection
"""
from datetime import datetime, timezone

from backend import db
from backend.config import ANALYSES_COLLECTION, MONGODB_DB

TEST_VIDEO_ID = "TEST_DAY2_00"  # fake id, deleted again at the end

print(f"1. Connecting to database '{MONGODB_DB}', collection '{ANALYSES_COLLECTION}'...")
db.ping()
print("   OK: MongoDB is reachable")

print("2. Inserting a test document...")
db.save_analysis({
    "video_id": TEST_VIDEO_ID,
    "title": "Day 2 connection test",
    "created_at": datetime.now(timezone.utc).isoformat(),
})
print("   OK: inserted")

print("3. Reading it back...")
doc = db.get_analysis(TEST_VIDEO_ID)
assert doc is not None and doc["title"] == "Day 2 connection test", "Read-back failed"
print(f"   OK: read back -> {doc}")

print("4. Cleaning up (deleting the test document)...")
db.delete_analysis(TEST_VIDEO_ID)
assert db.get_analysis(TEST_VIDEO_ID) is None
print("   OK: deleted")

print("\nAll database checks passed.")
