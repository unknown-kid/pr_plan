from celery import Celery
from app.config import settings

celery_app = Celery("worker", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    beat_schedule={
        "cleanup-trash-daily": {
            "task": "cleanup_trash",
            "schedule": 86400.0,  # Run every 24 hours
            "args": (settings.TRASH_RETENTION_DAYS,),
        },
    },
)

# 自动发现任务
celery_app.autodiscover_tasks(["app.tasks"])

# 显式导入以确保注册
import app.tasks.vectorization_tasks
import app.tasks.paper_tasks
import app.tasks.report_tasks

# 导入所有模型以确保 SQLAlchemy 知道所有表
import app.models.folder  # noqa
import app.models.paper  # noqa
