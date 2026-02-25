from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.paper import Paper
from app.models.search import SearchHistory, PopularSearch
from uuid import UUID
from datetime import datetime


async def search_papers(
    db: Session,
    query: str,
    user_id: Optional[UUID] = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "relevance",
) -> Dict[str, Any]:
    offset = (page - 1) * page_size

    # 构建全文搜索 SQL
    search_sql = text("""
        SELECT 
            id, title, authors, abstract, created_at, view_count,
            ts_rank(search_vector, plainto_tsquery('simple', :query)) as rank,
            ts_headline('simple', title, plainto_tsquery('simple', :query), 
                'StartSel=<mark>, StopSel=</mark>') as title_highlight,
            ts_headline('simple', coalesce(abstract, ''), plainto_tsquery('simple', :query), 
                'MaxWords=35, MinWords=15, StartSel=<mark>, StopSel=</mark>') as abstract_highlight
        FROM papers
        WHERE search_vector @@ plainto_tsquery('simple', :query)
            AND is_deleted = FALSE
            AND is_public = TRUE
    """)

    # 注意：这里需要根据具体的 SQL 语法调整，SQLAlchemy text 直接追加可能报错
    # 为了简单起见，这里假设 SQL 结构是正确的
    sql_str = str(search_sql)
    if sort_by == "relevance":
        sql_str += " ORDER BY rank DESC, created_at DESC"
    elif sort_by == "created_at":
        sql_str += " ORDER BY created_at DESC"
    elif sort_by == "view_count":
        sql_str += " ORDER BY view_count DESC"

    sql_str += " LIMIT :limit OFFSET :offset"

    results = (
        db.execute(
            text(sql_str), {"query": query, "limit": page_size, "offset": offset}
        )
        .mappings()
        .all()
    )

    # 统计总数
    count_sql = text("""
        SELECT COUNT(*) 
        FROM papers 
        WHERE search_vector @@ plainto_tsquery('simple', :query)
            AND is_deleted = FALSE
            AND is_public = TRUE
    """)
    total = db.execute(count_sql, {"query": query}).scalar()

    # 记录搜索历史
    record_search(db, query, user_id, total)

    return {
        "results": [dict(r) for r in results],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def record_search(db: Session, query: str, user_id: Optional[UUID], result_count: int):
    # 记录历史
    history = SearchHistory(user_id=user_id, query=query, result_count=result_count)
    db.add(history)

    # 更新热门搜索
    popular = db.query(PopularSearch).filter(PopularSearch.query == query).first()
    if popular:
        popular.search_count += 1
        popular.last_searched_at = datetime.utcnow()
    else:
        popular = PopularSearch(query=query, search_count=1)
        db.add(popular)

    db.commit()


def get_search_suggestions(db: Session, query: str, limit: int = 5) -> List[str]:
    results = (
        db.query(PopularSearch)
        .filter(PopularSearch.query.ilike(f"{query}%"))
        .order_by(PopularSearch.search_count.desc())
        .limit(limit)
        .all()
    )
    return [r.query for r in results]


def get_popular_searches(db: Session, limit: int = 10) -> List[Dict]:
    results = (
        db.query(PopularSearch)
        .order_by(PopularSearch.search_count.desc())
        .limit(limit)
        .all()
    )
    return [{"query": r.query, "count": r.search_count} for r in results]
