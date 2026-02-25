from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.ai_model import PublicAIModel, UserAIModel
from app.schemas.ai_model import AIModelBase


class ModelResolver:
    """
    模型解析器 - 负责根据用户配置选择合适的模型
    优先级：用户指定 > 用户默认 > 用户任意可用 > 公共活跃模型 > 系统默认
    """

    async def resolve_model(
        self,
        db: Session,
        user_id: UUID,
        model_type: str,
        user_preferred_id: Optional[UUID] = None,
    ) -> Optional[AIModelBase]:
        # 1. 如果用户指定了模型ID
        if user_preferred_id:
            model = (
                db.query(UserAIModel)
                .filter(
                    UserAIModel.id == user_preferred_id, UserAIModel.user_id == user_id
                )
                .first()
            )
            if model:
                return model

        # 2. 查找用户的默认模型
        default_model = (
            db.query(UserAIModel)
            .filter(
                UserAIModel.user_id == user_id,
                UserAIModel.model_type == model_type,
                UserAIModel.is_default == True,
            )
            .first()
        )
        if default_model:
            return default_model

        # 3. 如果没设默认，查找用户该类型的任意一个模型 (按创建时间倒序)
        any_user_model = (
            db.query(UserAIModel)
            .filter(
                UserAIModel.user_id == user_id,
                UserAIModel.model_type == model_type,
            )
            .order_by(UserAIModel.created_at.desc())
            .first()
        )
        if any_user_model:
            return any_user_model

        # 4. 查找公共活跃模型 (按优先级排序)
        public_model = (
            db.query(PublicAIModel)
            .filter(
                PublicAIModel.model_type == model_type, PublicAIModel.is_active == True
            )
            .order_by(PublicAIModel.priority.desc())
            .first()
        )

        if public_model:
            return public_model

        return None


model_resolver = ModelResolver()
