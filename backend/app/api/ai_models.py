from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.ai_model import UserAIModel as UserAIModelModel
from app.schemas.ai_model import (
    UserAIModel,
    UserAIModelCreate,
    UserAIModelUpdate,
    AIModelBase,
)
from app.models.user import User
from uuid import UUID
import httpx
import json

router = APIRouter()


@router.get("/", response_model=List[UserAIModel])
def list_user_models(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return (
        db.query(UserAIModelModel)
        .filter(UserAIModelModel.user_id == current_user.id)
        .all()
    )


@router.post("/", response_model=UserAIModel)
def create_user_model(
    model_in: UserAIModelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if model_in.is_default:
        db.query(UserAIModelModel).filter(
            UserAIModelModel.user_id == current_user.id,
            UserAIModelModel.model_type == model_in.model_type,
        ).update({"is_default": False})

    db_model = UserAIModelModel(**model_in.model_dump(), user_id=current_user.id)
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model


@router.put("/{model_id}", response_model=UserAIModel)
def update_user_model(
    model_id: UUID,
    model_in: UserAIModelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_model = (
        db.query(UserAIModelModel)
        .filter(
            UserAIModelModel.id == model_id, UserAIModelModel.user_id == current_user.id
        )
        .first()
    )
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")

    update_data = model_in.model_dump(exclude_unset=True)

    if update_data.get("is_default"):
        db.query(UserAIModelModel).filter(
            UserAIModelModel.user_id == current_user.id,
            UserAIModelModel.model_type == db_model.model_type,
        ).update({"is_default": False})

    for field, value in update_data.items():
        setattr(db_model, field, value)

    db.commit()
    db.refresh(db_model)
    return db_model


@router.delete("/{model_id}")
def delete_user_model(
    model_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_model = (
        db.query(UserAIModelModel)
        .filter(
            UserAIModelModel.id == model_id, UserAIModelModel.user_id == current_user.id
        )
        .first()
    )
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")
    db.delete(db_model)
    db.commit()
    return {"message": "Model deleted"}


@router.put("/{model_id}/set-default")
def set_default_model(
    model_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_model = (
        db.query(UserAIModelModel)
        .filter(
            UserAIModelModel.id == model_id, UserAIModelModel.user_id == current_user.id
        )
        .first()
    )
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")

    db.query(UserAIModelModel).filter(
        UserAIModelModel.user_id == current_user.id,
        UserAIModelModel.model_type == db_model.model_type,
    ).update({"is_default": False})

    db_model.is_default = True
    db.commit()
    return {"message": "Default model set"}


@router.post("/test-connectivity")
async def test_connectivity(
    config: UserAIModelCreate,
    current_user: User = Depends(get_current_user),
):
    api_url = config.api_url or "https://api.openai.com/v1"
    api_key = config.api_key
    model_name = config.model_name
    model_type = config.model_type
    provider = config.provider or "openai"

    if not api_key:
        raise HTTPException(status_code=400, detail="API Key is required for testing")

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            if model_type == "translation" and provider == "deepl":
                deepl_url = api_url or "https://api-free.deepl.com/v2/translate"
                headers = {
                    "Authorization": f"DeepL-Auth-Key {api_key}",
                    "Content-Type": "application/json",
                }
                payload = {"text": ["test"], "target_lang": "ZH"}
                response = await client.post(deepl_url, json=payload, headers=headers)
            elif model_type == "chat":
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                url = api_url.rstrip("/") + "/chat/completions"
                payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 5,
                }
                response = await client.post(url, json=payload, headers=headers)
            elif model_type == "embedding":
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                url = api_url.rstrip("/") + "/embeddings"
                payload = {"model": model_name, "input": "test"}
                response = await client.post(url, json=payload, headers=headers)
            else:
                raise HTTPException(
                    status_code=400, detail="Unsupported model type for testing"
                )

            if response.status_code == 200:
                return {"status": "success", "message": "Connectivity test passed!"}
            else:
                return {
                    "status": "error",
                    "message": f"API returned error ({response.status_code}): {response.text}",
                }
        except Exception as e:
            return {"status": "error", "message": f"Connection failed: {str(e)}"}
