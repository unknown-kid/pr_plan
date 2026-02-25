from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.model_resolver import model_resolver
import httpx
import os

router = APIRouter()


class TranslationRequest(BaseModel):
    text: str
    target_lang: str = "ZH"


@router.post("/")
async def translate_text(
    request: TranslationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    model_config = await model_resolver.resolve_model(
        db, current_user.id, "translation"
    )
    
    if not model_config:
        raise HTTPException(status_code=400, detail="请先在模型配置中配置 DeepL API Key")
    
    api_key = model_config.api_key
    if not api_key:
        raise HTTPException(status_code=400, detail="请配置 DeepL API Key")
    
    deepl_url = model_config.api_url or "https://api-free.deepl.com/v2/translate"
    
    headers = {
        "Authorization": f"DeepL-Auth-Key {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "text": [request.text],
        "target_lang": request.target_lang,
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                deepl_url, json=payload, headers=headers, timeout=30.0
            )
            if response.status_code != 200:
                raise Exception(f"DeepL API error: {response.status_code} - {response.text}")
            
            result = response.json()
            if "translations" in result and len(result["translations"]) > 0:
                translated_text = result["translations"][0]["text"]
                detected_lang = result["translations"][0].get("detected_source_language", "unknown")
                return {
                    "translated_text": translated_text,
                    "detected_source_language": detected_lang
                }
            else:
                raise Exception("No translation returned from DeepL")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"翻译失败: {str(e)}")
