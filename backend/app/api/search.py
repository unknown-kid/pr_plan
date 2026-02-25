from typing import List, Optional, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.api.deps import get_current_user, get_optional_current_user
from app.models.user import User
from app.models.paper import Paper
from app.services import search_service
from app.services.milvus_service import milvus_store
from app.services.embedding_client import EmbeddingClient
from app.services.model_resolver import model_resolver
from pymilvus import utility, connections
from uuid import UUID

router = APIRouter()


class SemanticSearchRequest(BaseModel):
    query: str
    top_k: int = 50


@router.post("/semantic")
async def semantic_search(
    request: SemanticSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Semantic search across all vectorized papers.
    Returns unique papers ranked by their best matching chunk score.
    """
    # 1. Resolve the user's embedding model
    embedding_config = await model_resolver.resolve_model(
        db, current_user.id, "embedding"
    )
    if not embedding_config:
        return {"papers": [], "total": 0, "message": "未配置嵌入模型"}

    api_key = getattr(embedding_config, "api_key", None)
    api_url = getattr(embedding_config, "api_url", "https://api.openai.com/v1")
    provider = getattr(embedding_config, "provider", "openai")
    model_name = getattr(embedding_config, "model_name", "text-embedding-ada-002")

    if not api_key:
        return {"papers": [], "total": 0, "message": "嵌入模型未配置 API Key"}

    # 2. Generate query embedding
    try:
        client = EmbeddingClient(
            api_key=api_key,
            api_url=api_url,
            model_name=model_name,
            provider=provider,
        )
        query_embedding = await client.get_single_embedding(request.query)
    except Exception as e:
        print(f"[SemanticSearch] Embedding error: {e}")
        return {"papers": [], "total": 0, "message": f"生成向量失败: {str(e)}"}

    # 3. Find all collections and search across them
    all_results = []
    try:
        milvus_store._connect()
        collections = utility.list_collections()
        for col_name in collections:
            try:
                results = await milvus_store.search(
                    query_embedding=query_embedding,
                    collection_name=col_name,
                    paper_id=None,  # search ALL papers
                    top_k=request.top_k,
                )
                all_results.extend(results)
            except Exception as e:
                print(f"[SemanticSearch] Search error in {col_name}: {e}")
                continue
    except Exception as e:
        print(f"[SemanticSearch] Milvus error: {e}")
        return {"papers": [], "total": 0, "message": f"向量搜索失败: {str(e)}"}

    # 4. Aggregate by paper_id: keep best score + collect matched snippets
    paper_scores: dict = {}  # paper_id -> {score, snippets}
    for r in all_results:
        pid = r.get("metadata", {}).get("paper_id")
        if not pid:
            continue
        score = r.get("score", 0)
        snippet = r.get("text", "")[:200]
        if pid not in paper_scores:
            paper_scores[pid] = {"best_score": score, "snippets": [snippet]}
        else:
            if score > paper_scores[pid]["best_score"]:
                paper_scores[pid]["best_score"] = score
            if len(paper_scores[pid]["snippets"]) < 3:
                paper_scores[pid]["snippets"].append(snippet)

    if not paper_scores:
        return {"papers": [], "total": 0}

    # 5. Rank papers by best score
    ranked_ids = sorted(
        paper_scores.keys(), key=lambda x: paper_scores[x]["best_score"], reverse=True
    )

    # 6. Fetch paper details from DB (only the user's papers)
    paper_rows = (
        db.query(Paper)
        .filter(Paper.id.in_([UUID(pid) for pid in ranked_ids]))
        .filter(Paper.upload_user_id == current_user.id)
        .filter(Paper.is_deleted == False)
        .all()
    )
    paper_map = {str(p.id): p for p in paper_rows}

    # 7. Build response in ranked order
    papers_out = []
    for pid in ranked_ids:
        p = paper_map.get(pid)
        if not p:
            continue
        papers_out.append(
            {
                "id": str(p.id),
                "title": str(p.title),
                "status": str(p.status),
                "folder_id": str(p.folder_id) if p.folder_id else None,
                "created_at": str(p.created_at) if p.created_at else None,
                "score": round(paper_scores[pid]["best_score"], 4),
                "snippets": paper_scores[pid]["snippets"],
            }
        )

    return {"papers": papers_out, "total": len(papers_out)}


@router.get("/papers")
async def search_papers(
    query: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("relevance", enum=["relevance", "created_at", "view_count"]),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    user_id = current_user.id if current_user else None
    return await search_service.search_papers(
        db,
        query=query,
        user_id=user_id,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
    )


@router.get("/suggestions")
def get_suggestions(
    query: str = Query(..., min_length=1), db: Session = Depends(get_db)
):
    return search_service.get_search_suggestions(db, query=query)


@router.get("/popular")
def get_popular(db: Session = Depends(get_db)):
    return search_service.get_popular_searches(db)
