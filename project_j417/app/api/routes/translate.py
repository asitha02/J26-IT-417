from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.consistency import check_consistency
from app.services.translator import translate_with_pairs

router = APIRouter(prefix="/translate", tags=["translate"])


class TranslateRequest(BaseModel):
    text: str
    source: Literal["en", "si"] = "en"
    target: Literal["en", "si"] = "si"
    check: bool = True


@router.post("")
def translate_text(req: TranslateRequest):
    translated, pairs = translate_with_pairs(req.text, req.target, req.source)
    resp = {"translation": translated}
    if req.check and pairs:
        resp["consistency"] = check_consistency(pairs)
    return resp