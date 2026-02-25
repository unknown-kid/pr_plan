"""
Paper Reading Report Generation Agent (CrewAI)

This script defines a multi-agent CrewAI pipeline with a 3-phase process:

Phase 1 - Skim Read (粗读):
    The skim-reader agent quickly reads the entire paper with the user's
    focus directions in mind, producing a structured outline for the report.

Phase 2 - Outline Review (大纲审核):
    The outline-reviewer agent refines the outline, ensuring it aligns with
    the user's focus directions and covers all important aspects.

Phase 3 - Deep Read & Report (精读生成):
    The report-writer agent re-reads the paper in depth, guided by the
    finalized outline, and produces the complete reading report with
    Mermaid diagrams, tables, and structured markdown.

Usage:
    from app.agents.paper_report_agent import generate_paper_report
    report = generate_paper_report(sections, api_config, paper_title, focus_directions)
"""

import os
import re
import json
from typing import List, Dict, Any, Optional
from crewai import Agent, Task, Crew, Process, LLM


def _build_llm(api_config: Dict[str, Any]) -> LLM:
    """Build a CrewAI LLM from the user's model configuration."""
    api_url = api_config.get("api_url", "https://api.openai.com/v1")
    api_key = api_config.get("api_key", "")
    model_name = api_config.get("model_name", "gpt-4o-mini")

    # CrewAI LLM uses litellm under the hood
    # For OpenAI-compatible APIs, use openai/ prefix
    base_url = api_url.rstrip("/")
    if base_url.endswith("/chat/completions"):
        base_url = base_url.rsplit("/chat/completions", 1)[0]
    if base_url.endswith("/v1"):
        base_url = base_url

    return LLM(
        model=f"openai/{model_name}",
        base_url=base_url,
        api_key=api_key,
        temperature=0.3,
    )


def _prepare_sections_text(sections: List[Dict[str, Any]]) -> str:
    """Concatenate all paper sections into a single text with page markers."""
    sections_text = ""
    for i, sec in enumerate(sections):
        page = sec.get("page", i + 1)
        text = sec.get("text", "")
        sections_text += f"\n\n--- 第 {page} 页 ---\n{text}"
    return sections_text


def _build_focus_prompt(focus_directions: Optional[str]) -> str:
    """Build the focus directions prompt segment."""
    if focus_directions and focus_directions.strip():
        return f"""
**用户重点关注方向**：
{focus_directions.strip()}

请特别注意围绕用户的关注方向来组织分析，在报告中优先展开用户关注的内容，
但也要覆盖论文的其他重要方面以保持完整性。"""
    else:
        return """
**用户未指定特别关注方向**，请全面分析论文的各个方面。"""


# =============================================================================
# Agent Definitions
# =============================================================================


def _create_skim_reader(llm: LLM) -> Agent:
    """Phase 1 Agent: Quickly reads the paper and produces a structured outline."""
    return Agent(
        role="论文粗读与大纲规划专家",
        goal="快速通读论文全文，结合用户关注方向，提取关键信息并形成报告大纲",
        backstory="""你是一位高效的学术论文阅读专家，擅长在短时间内把握论文的整体脉络。
你能够快速识别论文的核心贡献、方法论框架、实验设计和关键结论。
你特别善于根据读者的关注重点，规划出结构清晰、重点突出的阅读报告大纲。
你的大纲能帮助后续的精读者知道该在哪些部分深入、哪些部分概括。""",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


def _create_report_writer(llm: LLM) -> Agent:
    """Phase 3 Agent: Deep reads the paper guided by outline and writes the final report."""
    return Agent(
        role="论文精读与报告撰写专家",
        goal="根据报告大纲精读论文，撰写一份图文并茂、重点突出的完整论文阅读报告",
        backstory="""你是一位资深的学术报告撰写专家，擅长深入理解学术论文并将其转化为
高质量的阅读报告。你的工作流程是：
1. 先仔细研读报告大纲，了解报告的结构和重点
2. 然后逐页精读论文原文，提取与大纲各部分对应的详细信息
3. 最后组织撰写完整报告

你特别擅长：
- 使用 Mermaid 图表展示研究框架和流程
- 使用表格对比方法和实验结果
- 用简洁精准的语言解释复杂概念
- 根据用户关注方向调整叙述的详略

你的报告总是逻辑清晰、重点突出、图文并茂，让读者能快速掌握论文精髓。""",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


# =============================================================================
# Task Definitions
# =============================================================================


def _build_skim_read_task(
    agent: Agent,
    sections_text: str,
    paper_title: str,
    focus_prompt: str,
) -> Task:
    """Phase 1 Task: Skim-read the paper and produce a report outline."""
    return Task(
        description=f"""请快速通读以下论文「{paper_title}」的全部内容，并根据用户的关注方向形成一份报告大纲。

{focus_prompt}

**论文全文**：
{sections_text}

**粗读任务要求**：

请完成以下工作：

1. **快速把握论文核心**：
   - 论文解决了什么问题？
   - 提出了什么方法/模型？
   - 主要实验结论是什么？
   - 核心创新点有哪些？

2. **识别与用户关注方向的关联**：
   - 论文中哪些部分与用户的关注方向高度相关？
   - 这些部分需要在报告中重点展开

3. **输出报告大纲**：
   请设计一个层次分明的报告大纲，格式如下：

   ## 报告大纲

   ### 1. 论文概览
   - 需要涵盖的要点：...

   ### 2. 核心思想（重点/一般）
   - 需要涵盖的要点：...
   - 建议使用的图表类型：mindmap

   ### 3. 研究方法与技术路线（重点/一般）
   - 需要涵盖的要点：...
   - 建议使用的图表类型：flowchart

   ### 4. 模型/系统架构（重点/一般）
   - 需要涵盖的要点：...
   - 建议使用的图表类型：flowchart

   ### 5. 方法对比（重点/一般）
   - 需要涵盖的要点：...
   - 建议使用的图表类型：table

   ### 6. 实验过程（重点/一般）
   - 需要涵盖的要点：...

   ### 7. 实验结果（重点/一般）
   - 需要涵盖的要点：...
   - 建议使用的图表类型：table

   ### 8. 总结与展望（重点/一般）
   - 需要涵盖的要点：...

   ### 用户关注方向专题（如适用）
   - 如果用户的关注方向需要额外的专题章节，在此规划

   对于每个章节，请标注「重点」或「一般」来指示该章节在最终报告中应该展开的详略程度。
   与用户关注方向高度相关的章节标注为「重点」，需要更详细的论述。
   如果论文中某个方面信息不足，请在大纲中标注"论文未涉及，可略写"。""",
        expected_output="""一份结构完整的报告大纲，包含各章节的要点规划、详略标注和建议使用的图表类型。""",
        agent=agent,
    )


def _build_deep_read_report_task(
    agent: Agent,
    outline_task: Task,
    sections_text: str,
    paper_title: str,
    focus_prompt: str,
) -> Task:
    """Phase 3 Task: Deep-read the paper guided by the outline and write the final report."""
    return Task(
        description=f"""现在请你根据前一阶段产出的报告大纲，精读论文「{paper_title}」的原文，撰写完整的阅读报告。

{focus_prompt}

**论文原文**（请逐页仔细阅读）：
{sections_text}

**工作流程**：
1. 先仔细阅读上一阶段产出的报告大纲，理解每个章节的要点和详略要求
2. 对照大纲，逐页精读论文原文，提取每个章节所需的详细信息、数据和论据
3. 对于标注为「重点」的章节，需要深入展开，提供详尽的分析
4. 对于标注为「一般」的章节，概括性描述即可
5. 撰写完整报告

**报告格式要求**（严格遵守）：

## 1. 论文概览
简要介绍论文标题、作者、发表信息和研究领域。概括论文解决的核心问题和主要贡献。

## 2. 核心思想
- 用文字概括论文的核心贡献和创新点
- 使用 Mermaid mindmap 展示核心思想的结构：
```mermaid
mindmap
  root((核心思想))
    问题定义
      具体问题1
      具体问题2
    创新点
      创新点1
      创新点2
    关键贡献
      贡献1
      贡献2
```

## 3. 研究方法与技术路线
- 详细描述提出的方法（根据大纲标注的详略程度）
- 使用 Mermaid flowchart 展示技术路线：
```mermaid
flowchart TD
    A[输入] --> B[步骤1]
    B --> C[步骤2]
    C --> D[输出]
```

## 4. 模型/系统架构
- 描述整体架构（根据大纲标注的详略程度）
- 使用 Mermaid 图展示架构：
```mermaid
flowchart LR
    subgraph 模块A
        A1[组件1]
        A2[组件2]
    end
```

## 5. 方法对比
使用 Markdown 表格对比本文方法与其他方法：

| 方法 | 特点 | 优势 | 局限 |
|------|------|------|------|
| 本文方法 | ... | ... | ... |
| 对比方法1 | ... | ... | ... |

## 6. 实验过程
- 数据集描述
- 实验设置细节
- 评价指标说明

## 7. 实验结果
使用 Markdown 表格展示关键实验结果：

| 方法 | 指标1 | 指标2 | 指标3 |
|------|-------|-------|-------|
| ... | ... | ... | ... |

- 对结果进行分析和解读
- 如果有消融实验，也用表格展示

## 8. 总结与展望
- 论文的主要贡献总结
- 局限性分析
- 未来研究方向

（如果大纲中规划了用户关注方向的专题章节，也请在合适位置加入）

**注意事项**：
- 所有 Mermaid 图表必须使用 ```mermaid 代码块
- 表格必须是标准 Markdown 表格格式
- 每个图表和表格前后都要有文字说明
- 语言使用中文
- 标注为「重点」的章节要深入展开，提供详细数据和分析
- 标注为「一般」的章节概括性描述即可
- 如果论文中某方面信息不足，基于已有信息合理推断，但标注"根据论文有限信息推断"

**Mermaid 语法严格规则（必须遵守，否则图表无法渲染）**：
- 每个 mermaid 代码块的第一行必须是图表类型声明，如 flowchart TD、mindmap、pie 等
- 节点文字中禁止使用以下字符：圆括号 ()、双引号 ""、单引号 ''、反引号 ``、分号 ;、井号 #
- 如果节点文字需要包含括号内容，直接去掉括号只保留文字，例如 A[域适应 DA] 而不是 A[域适应(DA)]
- subgraph 和 end 必须成对出现
- mindmap 中每一层用缩进（两个空格）表示层级，根节点用 root((文字))
- flowchart 中箭头用 -->，节点 ID 只用英文字母和数字
- 不要在 mermaid 图中使用 HTML 标签或 LaTeX 公式""",
        expected_output="""一份完整的论文阅读报告，包含上述所有章节，使用 Mermaid 图表和 Markdown 表格展示关键信息。
报告需要体现对用户关注方向的侧重，标注为「重点」的章节内容更加详细。""",
        agent=agent,
        context=[outline_task],
    )


# =============================================================================
# Mermaid Sanitization (preserved from original)
# =============================================================================


def sanitize_mermaid_blocks(content: str) -> str:
    """
    Post-process Mermaid code blocks to fix common LLM output issues:
    - Remove unsupported special characters in node text (parentheses, quotes, etc.)
    - Fix broken subgraph / end pairs
    - Remove empty mermaid blocks
    - Ensure valid diagram type declaration
    """

    def sanitize_one_block(mermaid_code: str) -> str:
        lines = mermaid_code.strip().split("\n")
        if not lines:
            return mermaid_code

        # 1. Ensure first line is a valid diagram type
        first = lines[0].strip().lower()
        valid_types = [
            "graph",
            "flowchart",
            "sequencediagram",
            "sequence-diagram",
            "classDiagram",
            "class-diagram",
            "statediagram",
            "state-diagram",
            "erdiagram",
            "er-diagram",
            "journey",
            "gantt",
            "pie",
            "mindmap",
            "timeline",
            "gitgraph",
            "sankey",
            "xychart",
            "block",
        ]
        has_valid_type = any(first.startswith(t.lower()) for t in valid_types)
        if not has_valid_type:
            # Common case: LLM writes description instead of type
            # Try to detect and fix
            if "flowchart" in mermaid_code.lower() or "-->" in mermaid_code:
                lines.insert(0, "flowchart TD")
            elif "mindmap" in mermaid_code.lower() or "root((" in mermaid_code:
                lines.insert(0, "mindmap")
            else:
                lines.insert(0, "flowchart TD")

        result = []
        subgraph_depth = 0
        for line in lines:
            stripped = line.strip()

            # Skip empty lines (keep them for readability)
            if not stripped:
                result.append(line)
                continue

            # Track subgraph nesting
            if stripped.lower().startswith("subgraph"):
                subgraph_depth += 1
            elif stripped.lower() == "end":
                if subgraph_depth > 0:
                    subgraph_depth -= 1
                else:
                    # Extra 'end' with no matching subgraph — skip it
                    continue

            # 2. Sanitize node labels: remove problematic chars inside [...] and ((...))
            # Mermaid doesn't like: ( ) " ' ` ; # in node labels
            def clean_label(match):
                prefix = match.group(1)  # e.g., "A[" or "A(("
                label = match.group(2)
                suffix = match.group(3)
                # Remove problematic characters
                label = label.replace('"', "")
                label = label.replace("'", "")
                label = label.replace("`", "")
                label = label.replace(";", " ")
                label = label.replace("#", " ")
                # Replace (xxx) inside labels with xxx
                label = re.sub(r"\(([^)]*)\)", r"\1", label)
                return prefix + label + suffix

            # Match patterns: A["..."], A[...], A(("...")), A((...))
            line = re.sub(
                r"(\w+\[\[?\"?)([^\]]*?)(\"?\]\]?)",
                clean_label,
                line,
            )
            line = re.sub(
                r"(\w+\(\(\"?)([^)]*?)(\"?\)\))",
                clean_label,
                line,
            )

            result.append(line)

        # Close any unclosed subgraphs
        while subgraph_depth > 0:
            result.append("    end")
            subgraph_depth -= 1

        return "\n".join(result)

    # Find and sanitize all ```mermaid ... ``` blocks
    def replace_block(match):
        code = match.group(1)
        sanitized = sanitize_one_block(code)
        if not sanitized.strip():
            return ""  # Remove empty blocks
        return f"```mermaid\n{sanitized}\n```"

    return re.sub(r"```mermaid\s*\n([\s\S]*?)```", replace_block, content)


# =============================================================================
# Main Entry Point
# =============================================================================


def generate_paper_report(
    sections: List[Dict[str, Any]],
    api_config: Dict[str, Any],
    paper_title: str = "Untitled Paper",
    focus_directions: Optional[str] = None,
) -> str:
    """
    Generate a comprehensive reading report for a paper using a 3-phase process.

    Phase 1 (Skim Read):  Quickly read the paper with user's focus directions
                          and produce a structured report outline.
    Phase 2 (Deep Read):  Re-read the paper in detail guided by the outline
                          and generate the final report.

    Args:
        sections: List of {"text": str, "page": int} dicts from PDF parser
        api_config: {"api_key": str, "api_url": str, "model_name": str}
        paper_title: Title of the paper
        focus_directions: User's focus directions for reading the paper

    Returns:
        Markdown string of the reading report
    """
    llm = _build_llm(api_config)

    # Prepare shared data
    sections_text = _prepare_sections_text(sections)
    focus_prompt = _build_focus_prompt(focus_directions)

    # Create agents (2 agents for 3 logical phases)
    skim_reader = _create_skim_reader(llm)
    report_writer = _create_report_writer(llm)

    # Phase 1: Skim-read → produce outline
    skim_read_task = _build_skim_read_task(
        skim_reader, sections_text, paper_title, focus_prompt
    )

    # Phase 2+3: Deep-read guided by outline → produce final report
    deep_read_task = _build_deep_read_report_task(
        report_writer, skim_read_task, sections_text, paper_title, focus_prompt
    )

    # Create and run crew (sequential: skim first, then deep read)
    crew = Crew(
        agents=[skim_reader, report_writer],
        tasks=[skim_read_task, deep_read_task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()
    raw_content = str(result)

    # Post-process: sanitize mermaid blocks to prevent render errors
    sanitized = sanitize_mermaid_blocks(raw_content)
    return sanitized
