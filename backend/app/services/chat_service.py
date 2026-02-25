from typing import List, Dict, Any, Optional, AsyncGenerator
import httpx
import json
from app.services.model_resolver import model_resolver
from sqlalchemy.orm import Session
from uuid import UUID


class ChatService:
    async def chat_stream(
        self,
        db: Session,
        user_id: UUID,
        messages: List[Dict[str, str]],
        paper_id: Optional[UUID] = None,
        model_id: Optional[UUID] = None,
        rag_scope: str = "single",
        report_id: Optional[UUID] = None,
    ) -> AsyncGenerator[str, None]:
        # 1. 解析聊天模型配置
        model_config = await model_resolver.resolve_model(
            db, user_id, "chat", user_preferred_id=model_id
        )
        if not model_config:
            yield "错误：未配置 AI 模型。请前往‘模型配置’页面添加您的 API Key。"
            return

        # Helper to get attribute safely
        def get_model_attr(attr, default=None):
            if isinstance(model_config, dict):
                return model_config.get(attr, default)
            return getattr(model_config, attr, default)

        # 2. 获取阅读报告内容（如果用户选择了某个版本）
        report_context = ""
        if report_id:
            try:
                from app.models.reading_report import ReadingReport

                report = (
                    db.query(ReadingReport)
                    .filter(
                        ReadingReport.id == report_id,
                        ReadingReport.user_id == user_id,
                        ReadingReport.status == "completed",
                    )
                    .first()
                )
                if report:
                    report_context = report.content
                    print(
                        f"[Chat] Including reading report v{report.version} "
                        f"({len(report_context)} chars) as context"
                    )
            except Exception as e:
                print(f"[Chat] Failed to load reading report: {e}")

        # 3. 执行 RAG 检索
        user_query = messages[-1]["content"]
        should_rag = paper_id or rag_scope == "all"
        rag_context = ""
        if should_rag:
            try:
                from app.services.rag_service import RAGService

                rag_service = RAGService()
                rag_context = await rag_service.get_context(
                    db,
                    user_id,
                    user_query,
                    paper_id=paper_id,
                    top_k=10,
                    scope=rag_scope,
                )
            except Exception as e:
                print(f"RAG context retrieval failed: {str(e)}")

        # 4. 组装 system prompt
        if rag_context or report_context:
            prompt_parts = ["你是一个专业的论文阅读助手。"]

            if report_context:
                prompt_parts.append(
                    "以下是用户选择引用的阅读报告，它包含了对论文的系统性分析，"
                    "请将其作为重要的参考信息：\n\n"
                    "=== 阅读报告 ===\n"
                    f"{report_context}\n"
                    "=== 阅读报告结束 ==="
                )

            if rag_context:
                if rag_scope == "all":
                    prompt_parts.append(
                        f"以下是从多篇论文中检索到的相关片段：\n\n{rag_context}"
                    )
                else:
                    prompt_parts.append(
                        f"以下是从论文中检索到的相关片段：\n\n{rag_context}"
                    )

            prompt_parts.append(
                "请基于以上信息回答用户问题。"
                "如果提供的信息中没有相关内容，请结合你的通用知识回答但说明来源。"
            )

            system_prompt = "\n\n".join(prompt_parts)

            if messages and messages[0]["role"] == "system":
                messages[0]["content"] = system_prompt
            else:
                messages.insert(0, {"role": "system", "content": system_prompt})

        # 5. 准备 API 调用
        api_url = get_model_attr("api_url") or "https://api.openai.com/v1"
        if not api_url.endswith("/chat/completions"):
            api_url = api_url.rstrip("/") + "/chat/completions"

        api_key = get_model_attr("api_key")
        model_name = get_model_attr("model_name")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": True,
            "temperature": 0.7,
        }

        # 更长的超时
        timeout = httpx.Timeout(60.0, connect=10.0)

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            try:
                async with client.stream(
                    "POST", api_url, json=payload, headers=headers
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        yield f"AI 提供商返回错误 ({response.status_code}): {error_text.decode()}"
                        return

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        if line.startswith("data: "):
                            data = line[6:].strip()
                            if data == "[DONE]":
                                break
                            try:
                                json_data = json.loads(data)
                                if json_data.get("choices"):
                                    content = (
                                        json_data["choices"][0]
                                        .get("delta", {})
                                        .get("content", "")
                                    )
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                continue
            except httpx.ConnectError:
                yield "连接 AI 服务失败：无法建立网络连接。请检查 API URL 是否正确，或服务器是否需要代理。"
            except httpx.ReadTimeout:
                yield "连接 AI 服务超时：模型响应过慢。"
            except Exception as e:
                yield f"AI 服务异常: {str(e)}"


chat_service = ChatService()
