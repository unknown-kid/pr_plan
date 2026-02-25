from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_active_admin
from app.models.ai_model import PublicAIModel as PublicAIModelModel
from app.schemas.ai_model import PublicAIModel, PublicAIModelCreate, PublicAIModelUpdate
from app.models.user import User

router = APIRouter()


@router.get("/public-models", response_model=List[PublicAIModel])
def list_public_models(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_active_admin),
):
    return db.query(PublicAIModelModel).all()


@router.post("/public-models", response_model=PublicAIModel)
def create_public_model(
    model_in: PublicAIModelCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_active_admin),
):
    db_model = PublicAIModelModel(**model_in.model_dump(), created_by=current_admin.id)
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model


@router.put("/public-models/{model_id}", response_model=PublicAIModel)
def update_public_model(
    model_id: str,
    model_in: PublicAIModelUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_active_admin),
):
    db_model = (
        db.query(PublicAIModelModel).filter(PublicAIModelModel.id == model_id).first()
    )
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")

    update_data = model_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_model, field, value)

    db.commit()
    db.refresh(db_model)
    return db_model


@router.delete("/public-models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_public_model(
    model_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_active_admin),
):
    db_model = (
        db.query(PublicAIModelModel).filter(PublicAIModelModel.id == model_id).first()
    )
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")
    db.delete(db_model)
    db.commit()
    return None
