import re
from app.db.mongo import db
from app.services.generator import generate

items = list(db.kb_items.find({}, {"_id": 0}).limit(50))
valid = {i["kb_id"] for i in items}

for output_type in ["summary", "notes", "quiz"]:
    text = generate(output_type, items)
    cited = set(re.findall(r"\[(kb_\d+)\]", text))
    invalid = cited - valid
    uncited = [l for l in text.split("\n")
               if len(l.split()) > 6 and not re.search(r"\[kb_\d+\]", l)]
    print(f"{output_type}: cited={len(cited)} invented_ids={sorted(invalid) or 'none'} "
          f"uncited_lines={len(uncited)}")