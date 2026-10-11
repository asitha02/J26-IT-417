from app.services.llm import complete

OUTPUT_TYPES = {
    "summary": "Write a concise study summary.",
    "notes": "Write structured study notes with headings and bullet points.",
    "quiz": "Write 5 multiple-choice questions with answers and one-line explanations.",
}

SYSTEM = (
    "You are an educational content generator. Use ONLY the knowledge items provided. "
    "Do not add facts that are not in them. Cite items as [kb_id] after each claim."
)


def generate(output_type: str, kb_items: list[dict]) -> str:
    facts = "\n".join(f"[{i['kb_id']}] ({i['type']}) {i['text']}" for i in kb_items)
    prompt = f"{OUTPUT_TYPES[output_type]}\n\nKnowledge items:\n{facts}"
    return complete(prompt, system=SYSTEM)

from app.services.llm import complete

OUTPUT_TYPES = {
    "summary": "Write a concise study summary in 1-3 short paragraphs.",
    "notes": "Write structured study notes with headings and bullet points.",
    "quiz": "Write 5 multiple-choice questions, each with options A-D, the correct answer, and a one-line explanation.",
}

SYSTEM = (
    "You are an educational content generator. Use ONLY the knowledge items provided. "
    "Do not add facts, examples or numbers that are not in them. "
    "After every claim, cite the supporting item id in the form [kb_00001]. "
    "Do not invent ids."
)


def generate(output_type: str, kb_items: list[dict]) -> str:
    facts = "\n".join(f"[{i['kb_id']}] ({i['type']}) {i['text']}" for i in kb_items)
    prompt = f"{OUTPUT_TYPES[output_type]}\n\nKnowledge items:\n{facts}"
    return complete(prompt, system=SYSTEM)