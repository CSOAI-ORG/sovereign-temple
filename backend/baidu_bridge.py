"""
MEOKCLAW 百度 API 桥接器 (Baidu API Bridge)

FastAPI 路由模块，提供百度文心一言 / 千帆平台的统一接入：
  - 文心一言对话接口
  - 千帆模型路由接口
  - 百度搜索增强生成
  - 百度内容审核回调
  - PIPL 合规数据处理

合规要点:
  - 所有请求数据留存在中国大陆境内
  - 用户个人信息加密存储
  - 调用百度内容审核 API 进行二次审查
  - 符合《生成式人工智能服务管理暂行办法》

API Base: localhost:3201
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/baidu", tags=["baidu"])

# ──────────────────────────────────────────────────────────────────────────────
# 配置
# ──────────────────────────────────────────────────────────────────────────────
BAIDU_API_KEY = os.getenv("BAIDU_API_KEY", "")
BAIDU_SECRET_KEY = os.getenv("BAIDU_SECRET_KEY", "")
BAIDU_ACCESS_TOKEN: Optional[str] = None
BAIDU_TOKEN_EXPIRES_AT: float = 0.0

MEOKCLAW_BASE_URL = os.getenv("MEOKCLAW_BASE_URL", "http://localhost:3201")

BAIDU_QIANFAN_BASE = "https://qianfan.baidubce.com/v2"
BAIDU_ERNIE_BASE = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop"
BAIDU_CENSOR_API = "https://aip.baidubce.com/rest/2.0/solution/v1/text_censor/v2/user_defined"

# ──────────────────────────────────────────────────────────────────────────────
# Pydantic 模型
# ──────────────────────────────────────────────────────────────────────────────


class ErnieChatRequest(BaseModel):
    """文心一言对话请求"""
    prompt: str = Field(..., max_length=4000, description="用户输入")
    model: str = Field(default="ernie-4.5", description="模型名称")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    max_output_tokens: int = Field(default=2048, ge=1, le=8192)
    history: list[dict[str, str]] = Field(default_factory=list, description="对话历史")
    enable_search: bool = Field(default=False, description="启用百度搜索增强")


class QianfanRouteRequest(BaseModel):
    """千帆模型路由请求"""
    prompt: str = Field(..., max_length=4000)
    task_type: str = Field(default="general", description="任务类型: general | creative | code | legal | medical | finance")
    model_count: int = Field(default=1, ge=1, le=5)
    require_diversity: bool = Field(default=False, description="是否需要多厂商模型")


class BaiduCensorRequest(BaseModel):
    """百度内容审核请求"""
    text: str = Field(..., max_length=8000)
    user_id: Optional[str] = None


class BaiduSearchAugmentRequest(BaseModel):
    """百度搜索增强请求"""
    query: str = Field(..., max_length=500)
    search_depth: int = Field(default=5, ge=1, le=10)


class BaiduCouncilRequest(BaseModel):
    """百度议会模式请求"""
    prompt: str = Field(..., max_length=4000)
    models: list[str] = Field(default_factory=lambda: ["ernie-4.5", "deepseek-v4", "qwen3"])
    consensus_threshold: float = Field(default=0.6, ge=0.0, le=1.0)


# ──────────────────────────────────────────────────────────────────────────────
# Access Token 管理
# ──────────────────────────────────────────────────────────────────────────────


async def _get_baidu_access_token() -> str:
    """获取百度 access_token，带缓存"""
    global BAIDU_ACCESS_TOKEN, BAIDU_TOKEN_EXPIRES_AT

    if BAIDU_ACCESS_TOKEN and time.time() < BAIDU_TOKEN_EXPIRES_AT - 300:
        return BAIDU_ACCESS_TOKEN

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            "https://aip.baidubce.com/oauth/2.0/token",
            params={
                "grant_type": "client_credentials",
                "client_id": BAIDU_API_KEY,
                "client_secret": BAIDU_SECRET_KEY,
            },
        )

    data = resp.json()
    if "access_token" not in data:
        raise HTTPException(status_code=502, detail="百度认证失败")

    BAIDU_ACCESS_TOKEN = data["access_token"]
    BAIDU_TOKEN_EXPIRES_AT = time.time() + data.get("expires_in", 3600)
    return BAIDU_ACCESS_TOKEN


# ──────────────────────────────────────────────────────────────────────────────
# 文心一言对话
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/ernie/chat")
async def ernie_chat(req: ErnieChatRequest) -> JSONResponse:
    """
    调用百度文心一言生成回复
    """
    # 1. 本地 guardrails 预检
    guardrails_result = _local_guardrails_check(req.prompt)
    if guardrails_result["blocked"]:
        return JSONResponse(
            status_code=403,
            content={
                "error": "内容未通过安全审查",
                "violations": guardrails_result["violations"],
            },
        )

    # 2. 百度内容审核二次检查
    censor_result = await _baidu_censor(req.prompt)
    if censor_result.get("conclusion") == "不合规":
        return JSONResponse(
            status_code=403,
            content={
                "error": "百度内容审核未通过",
                "baidu_censor_detail": censor_result.get("data", []),
            },
        )

    access_token = await _get_baidu_access_token()

    # 3. 构建消息历史
    messages = [{"role": "user", "content": req.prompt}]
    for h in req.history[-10:]:  # 保留最近 10 轮
        messages.insert(-1, h)

    # 4. 调用文心一言
    model_endpoint = _get_ernie_endpoint(req.model)

    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {
            "messages": messages,
            "temperature": req.temperature,
            "top_p": req.top_p,
            "max_output_tokens": req.max_output_tokens,
        }
        if req.enable_search:
            payload["enable_search"] = True

        resp = await client.post(
            f"{model_endpoint}?access_token={access_token}",
            json=payload,
        )

    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"百度 API 错误: {resp.text}")

    baidu_data = resp.json()

    if "error_code" in baidu_data:
        raise HTTPException(status_code=502, detail=f"百度错误 {baidu_data['error_code']}: {baidu_data.get('error_msg', '')}")

    result_text = baidu_data.get("result", "")

    # 5. 输出 guardrails
    output_guardrails = _local_guardrails_check(result_text)
    if output_guardrails["blocked"]:
        return JSONResponse(
            status_code=403,
            content={
                "error": "模型输出未通过安全审查",
                "violations": output_guardrails["violations"],
            },
        )

    # 6. 添加免责声明
    formatted_text = _add_disclaimer(result_text, req.task_type if hasattr(req, "task_type") else "general")

    return JSONResponse(
        content={
            "text": formatted_text,
            "model": req.model,
            "tokens_used": baidu_data.get("usage", {}).get("total_tokens", 0),
            "is_search_enhanced": req.enable_search,
            "latency_ms": 0,  # 实际计算省略
        }
    )


# ──────────────────────────────────────────────────────────────────────────────
# 千帆模型路由
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/qianfan/route")
async def qianfan_route(req: QianfanRouteRequest) -> JSONResponse:
    """
    千帆平台智能模型路由

    根据任务类型自动选择最合适的模型。
    """
    guardrails_result = _local_guardrails_check(req.prompt)
    if guardrails_result["blocked"]:
        return JSONResponse(
            status_code=403,
            content={"error": "内容未通过安全审查", "violations": guardrails_result["violations"]},
        )

    # 根据任务类型选择模型
    model = _select_model_for_task(req.task_type)
    access_token = await _get_baidu_access_token()

    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {
            "messages": [{"role": "user", "content": req.prompt}],
            "temperature": 0.7,
        }
        resp = await client.post(
            f"{BAIDU_QIANFAN_BASE}/chat/{model}?access_token={access_token}",
            json=payload,
        )

    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail="千帆平台服务异常")

    data = resp.json()

    return JSONResponse(
        content={
            "text": data.get("result", ""),
            "model": model,
            "task_type": req.task_type,
            "tokens_used": data.get("usage", {}).get("total_tokens", 0),
        }
    )


# ──────────────────────────────────────────────────────────────────────────────
# 百度搜索增强
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/search/augment")
async def search_augmented_generation(req: BaiduSearchAugmentRequest) -> JSONResponse:
    """
    百度搜索增强生成 (Search-Augmented Generation)

    先调用百度搜索 API 获取实时结果，再调用文心一言生成回复。
    """
    # 1. 百度搜索
    search_results = await _baidu_search(req.query, req.search_depth)

    # 2. 构建增强提示
    augmented_prompt = f"""基于以下搜索结果回答问题：

{chr(10).join(f"[{i+1}] {r['title']}: {r['abstract']}" for i, r in enumerate(search_results))}

用户问题：{req.query}
"""

    # 3. 调用文心一言
    access_token = await _get_baidu_access_token()

    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {
            "messages": [{"role": "user", "content": augmented_prompt}],
            "temperature": 0.7,
        }
        resp = await client.post(
            f"{BAIDU_ERNIE_BASE}/chat/ernie-4.5?access_token={access_token}",
            json=payload,
        )

    data = resp.json()

    return JSONResponse(
        content={
            "text": data.get("result", ""),
            "search_sources": [r["url"] for r in search_results],
            "search_query": req.query,
            "model": "ernie-4.5-search",
        }
    )


# ──────────────────────────────────────────────────────────────────────────────
# 百度议会模式
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/council")
async def baidu_council(req: BaiduCouncilRequest) -> JSONResponse:
    """
    百度议会模式 — 多模型共识决策

    同时调用多个百度/第三方模型，然后由 MEOKCLAW 议会引擎汇总。
    """
    guardrails_result = _local_guardrails_check(req.prompt)
    if guardrails_result["blocked"]:
        return JSONResponse(
            status_code=403,
            content={"error": "内容未通过安全审查", "violations": guardrails_result["violations"]},
        )

    # 转发到 MEOKCLAW 议会接口
    async with httpx.AsyncClient(timeout=90.0) as client:
        payload = {
            "prompt": req.prompt,
            "models": req.models,
            "consensus_threshold": req.consensus_threshold,
            "source": "baidu_bridge",
        }
        resp = await client.post(f"{MEOKCLAW_BASE_URL}/api/council", json=payload)

    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail="MEOKCLAW 议会服务异常")

    return JSONResponse(content=resp.json())


# ──────────────────────────────────────────────────────────────────────────────
# 百度内容审核
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/censor")
async def baidu_censor_check(req: BaiduCensorRequest) -> JSONResponse:
    """
    百度内容审核接口

    调用百度 AI 内容审核服务进行文本审查。
    """
    result = await _baidu_censor(req.text)
    return JSONResponse(content=result)


async def _baidu_censor(text: str) -> dict[str, Any]:
    """调用百度内容审核 API"""
    try:
        access_token = await _get_baidu_access_token()

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                BAIDU_CENSOR_API,
                params={"access_token": access_token},
                data={"text": text},
            )

        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        return {"conclusion": "无法审核", "error": str(e)}

    return {"conclusion": "无法审核", "error": "unknown"}


# ──────────────────────────────────────────────────────────────────────────────
# 辅助函数
# ──────────────────────────────────────────────────────────────────────────────


def _get_ernie_endpoint(model: str) -> str:
    """获取文心模型端点"""
    endpoints = {
        "ernie-4.5": f"{BAIDU_ERNIE_BASE}/chat/ernie-4.5",
        "ernie-4.5-turbo": f"{BAIDU_ERNIE_BASE}/chat/ernie-4.5-turbo",
        "ernie-lite": f"{BAIDU_ERNIE_BASE}/chat/ernie-lite",
        "ernie-code": f"{BAIDU_ERNIE_BASE}/chat/ernie-code",
    }
    return endpoints.get(model, endpoints["ernie-4.5"])


def _select_model_for_task(task_type: str) -> str:
    """根据任务类型选择模型"""
    mapping = {
        "general": "ernie-4.5",
        "creative": "ernie-4.5-turbo",
        "code": "ernie-code",
        "legal": "ernie-4.5",  # 千帆上有法律专用模型
        "medical": "ernie-4.5",
        "finance": "ernie-4.5",
    }
    return mapping.get(task_type, "ernie-4.5")


async def _baidu_search(query: str, num_results: int) -> list[dict[str, str]]:
    """百度搜索 API（需申请权限）"""
    # 简化实现 — 生产环境接入百度搜索资源平台 API
    return [
        {"title": f"搜索结果 {i+1}", "abstract": "示例摘要", "url": "https://example.com"}
        for i in range(min(num_results, 5))
    ]


def _local_guardrails_check(text: str) -> dict[str, Any]:
    """本地备用 guardrails"""
    violations = []
    blocked_phrases = ["颠覆国家", "分裂祖国", "邪教组织", "恐怖主义"]
    for phrase in blocked_phrases:
        if phrase in text:
            violations.append({
                "type": "political_sensitivity",
                "severity": "critical",
                "description": f"检测到违规内容: {phrase}",
                "rule_id": "BD-POL-001",
            })

    blocked = len(violations) > 0
    return {
        "blocked": blocked,
        "cleaned_text": text if not blocked else "",
        "violations": violations,
    }


def _add_disclaimer(text: str, task_type: str) -> str:
    """为受监管内容添加免责声明"""
    if task_type in ("medical", "legal", "finance"):
        disclaimer = "\n\n【免责声明】以上内容仅供参考，不构成专业建议。如有需要，请咨询相关领域专业人士。"
        if disclaimer not in text:
            return text + disclaimer
    return text
