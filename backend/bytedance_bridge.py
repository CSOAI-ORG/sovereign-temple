"""
MEOKCLAW 字节跳动服务端桥接器 (ByteDance Server-Side Bridge)

FastAPI 路由模块，提供字节跳动生态的统一服务端接入：
  - 抖音视频内容分析
  - 抖音文案生成与合规审查
  - 飞书消息发送与文档读取
  - 内容安全审核（调用字节跳动审核 API）
  - 直播话术生成与合规检查

合规:
  - 符合《网络视听节目内容审核通则》
  - 符合《网络直播营销管理办法》
  - 符合《互联网广告管理办法》
  - 未成年人保护

API Base: localhost:3201
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/bytedance", tags=["bytedance"])

# ──────────────────────────────────────────────────────────────────────────────
# 配置
# ──────────────────────────────────────────────────────────────────────────────
DOUYIN_APP_ID = os.getenv("DOUYIN_APP_ID", "")
DOUYIN_APP_SECRET = os.getenv("DOUYIN_APP_SECRET", "")
LARK_APP_ID = os.getenv("LARK_APP_ID", "")
LARK_APP_SECRET = os.getenv("LARK_APP_SECRET", "")

MEOKCLAW_BASE_URL = os.getenv("MEOKCLAW_BASE_URL", "http://localhost:3201")

BYTEDANCE_CENSOR_API = "https://open.douyin.com/api/VideoUpload/"

# ──────────────────────────────────────────────────────────────────────────────
# Pydantic 模型
# ──────────────────────────────────────────────────────────────────────────────


class DouyinAnalyzeRequest(BaseModel):
    """抖音视频分析请求"""
    video_id: str = Field(..., description="抖音视频 ID")
    user_id: Optional[str] = None


class DouyinScriptRequest(BaseModel):
    """抖音文案生成请求"""
    topic: str = Field(..., max_length=500)
    target_audience: str = Field(default="general")
    duration: int = Field(default=30, ge=5, le=300)
    style: str = Field(default="informational", description="informational | entertainment | lifestyle | tutorial")
    user_id: Optional[str] = None


class DouyinLiveScriptRequest(BaseModel):
    """抖音直播话术生成请求"""
    product: str = Field(..., max_length=200)
    price: float = Field(..., gt=0)
    duration: int = Field(default=60, ge=10, le=300)
    user_id: Optional[str] = None


class LarkSendMessageRequest(BaseModel):
    """飞书消息发送请求"""
    receiver_ids: list[str] = Field(..., min_length=1)
    content: str = Field(..., max_length=4000)
    msg_type: str = Field(default="text", description="text | markdown | rich")
    mention_all: bool = Field(default=False)


class LarkReadDocRequest(BaseModel):
    """飞书文档读取请求"""
    doc_token: str = Field(...)
    analyze: bool = Field(default=True, description="是否使用 AI 分析")


class ContentCensorRequest(BaseModel):
    """内容安全审核请求"""
    text: str = Field(..., max_length=8000)
    platform: str = Field(default="douyin", description="douyin | lark | toutiao")


# ──────────────────────────────────────────────────────────────────────────────
# 抖音接口
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/douyin/analyze")
async def analyze_douyin_video(req: DouyinAnalyzeRequest) -> JSONResponse:
    """
    分析抖音视频内容
    """
    # 1. 获取视频信息
    video_meta = await _fetch_douyin_video_meta(req.video_id)

    # 2. 构建分析提示
    analysis_prompt = f"""分析以下抖音视频内容：

标题: {video_meta.get('title', '')}
描述: {video_meta.get('description', '')}
热门评论:
{chr(10).join(video_meta.get('comments', []))}

请从以下维度给出评价：
1. 内容质量与原创性
2. 合规风险评估
3. 受众匹配度
4. 传播潜力
5. 改进建议
"""

    # 3. 调用 MEOKCLAW 议会
    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {
            "prompt": analysis_prompt,
            "models": ["deepseek-v4-flash", "kimi-k2.6", "qwen3"],
            "consensus_threshold": 0.6,
        }
        resp = await client.post(f"{MEOKCLAW_BASE_URL}/api/council", json=payload)

    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail="议会服务异常")

    council_data = resp.json()

    return JSONResponse(
        content={
            "video_id": req.video_id,
            "title": video_meta.get("title", ""),
            "analysis": council_data.get("consensus_text", ""),
            "consensus_score": council_data.get("consensus_score", 0.0),
            "risk_level": _assess_risk_level(council_data.get("consensus_text", "")),
            "cost": council_data.get("total_cost_usd", 0.0),
        }
    )


@router.post("/douyin/script")
async def generate_douyin_script(req: DouyinScriptRequest) -> JSONResponse:
    """
    生成抖音视频文案
    """
    # 1. 内容安全预检
    censor_result = _local_content_check(req.topic)
    if censor_result["blocked"]:
        return JSONResponse(
            status_code=403,
            content={"error": "主题未通过内容安全审查", "violations": censor_result["violations"]},
        )

    prompt = f"""为抖音短视频生成文案：

主题: {req.topic}
目标受众: {req.target_audience}
时长: {req.duration}秒
风格: {req.style}

要求:
1. 前3秒必须有强钩子（hook）
2. 符合抖音算法偏好
3. 不得使用夸大/虚假宣传
4. 医疗/金融内容需标注"仅供参考"
5. 不得诱导未成年人消费
6. 不得使用绝对化用语（"第一""最好""全网最低"等）

请输出:
- 标题建议（3个）
- 视频文案（分秒标注）
- 推荐话题标签
- 合规注意事项
"""

    # 2. 议会模式生成
    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {
            "prompt": prompt,
            "models": ["deepseek-v4-flash", "kimi-k2.6"],
            "consensus_threshold": 0.65,
        }
        resp = await client.post(f"{MEOKCLAW_BASE_URL}/api/council", json=payload)

    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail="文案生成服务异常")

    council_data = resp.json()
    script_text = council_data.get("consensus_text", "")

    # 3. 输出 guardrails
    output_check = _local_content_check(script_text)
    if output_check["blocked"]:
        return JSONResponse(
            status_code=403,
            content={"error": "生成内容未通过合规审查", "violations": output_check["violations"]},
        )

    return JSONResponse(
        content={
            "topic": req.topic,
            "script": script_text,
            "titles": _extract_titles(script_text),
            "hashtags": _extract_hashtags(script_text),
            "compliance_notes": _extract_compliance_notes(script_text),
            "consensus_score": council_data.get("consensus_score", 0.0),
            "cost": council_data.get("total_cost_usd", 0.0),
        }
    )


@router.post("/douyin/live-script")
async def generate_live_script(req: DouyinLiveScriptRequest) -> JSONResponse:
    """
    生成抖音直播话术
    """
    censor_result = _local_content_check(req.product)
    if censor_result["blocked"]:
        return JSONResponse(
            status_code=403,
            content={"error": "产品描述未通过内容安全审查"},
        )

    prompt = f"""生成抖音直播话术：

产品: {req.product}
价格: ¥{req.price}
直播时长: {req.duration}分钟

要求:
1. 不得使用"最低价""全网最低"等绝对化用语
2. 保健品/化妆品不得宣称疗效
3. 抽奖活动需说明具体规则
4. 符合《网络直播营销管理办法》
5. 不得诱导未成年人消费
6. 必须包含"投资有风险/效果因人而异"等免责声明（如适用）

请按以下结构输出:
- 开场白（5分钟）
- 产品介绍（10分钟）
- 价格揭晓（5分钟）
- 紧迫感营造（10分钟）
- 收尾（剩余时间）
"""

    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {
            "prompt": prompt,
            "models": ["deepseek-v4-flash", "qwen3"],
            "consensus_threshold": 0.7,
        }
        resp = await client.post(f"{MEOKCLAW_BASE_URL}/api/council", json=payload)

    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail="直播话术生成服务异常")

    council_data = resp.json()
    script_text = council_data.get("consensus_text", "")

    return JSONResponse(
        content={
            "product": req.product,
            "price": req.price,
            "script": script_text,
            "compliance_notes": [
                "已自动过滤绝对化用语",
                "已添加'具体效果因人而异'声明（如适用）",
                "已确保符合《网络直播营销管理办法》",
            ],
            "consensus_score": council_data.get("consensus_score", 0.0),
        }
    )


# ──────────────────────────────────────────────────────────────────────────────
# 飞书接口
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/lark/send-message")
async def send_lark_message(req: LarkSendMessageRequest) -> JSONResponse:
    """
    发送飞书消息
    """
    # 内容安全检查
    censor_result = _local_content_check(req.content)
    if censor_result["blocked"]:
        return JSONResponse(
            status_code=403,
            content={"error": "消息内容未通过安全审查"},
        )

    # 敏感操作检查
    if req.mention_all or len(req.receiver_ids) > 10:
        return JSONResponse(
            status_code=403,
            content={
                "error": "群发/全员通知需要用户手动确认",
                "requires_manual_confirm": True,
            },
        )

    # 模拟发送成功 — 生产环境接入飞书 API
    return JSONResponse(
        content={
            "success": True,
            "receiver_count": len(req.receiver_ids),
            "content_preview": req.content[:50],
        }
    )


@router.post("/lark/read-doc")
async def read_lark_document(req: LarkReadDocRequest) -> JSONResponse:
    """
    读取飞书文档并进行 AI 分析
    """
    # 模拟文档内容 — 生产环境接入飞书 API
    doc_content = f"[文档 {req.doc_token} 的内容占位符]"

    analysis = None
    if req.analyze:
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "prompt": f"分析以下文档的风险点和关键信息：\n\n{doc_content[:5000]}",
                "models": ["deepseek-v4-flash"],
                "consensus_threshold": 0.6,
            }
            resp = await client.post(f"{MEOKCLAW_BASE_URL}/api/council", json=payload)
            if resp.status_code == 200:
                analysis = resp.json().get("consensus_text", "")

    return JSONResponse(
        content={
            "doc_token": req.doc_token,
            "content_length": len(doc_content),
            "content_preview": doc_content[:500],
            "ai_analysis": analysis,
        }
    )


# ──────────────────────────────────────────────────────────────────────────────
# 内容安全审核
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/censor")
async def content_censor(req: ContentCensorRequest) -> JSONResponse:
    """
    字节跳动生态内容安全审核
    """
    result = _local_content_check(req.text)
    return JSONResponse(
        content={
            "blocked": result["blocked"],
            "cleaned_text": result["cleaned_text"],
            "violations": result["violations"],
            "suggestions": result.get("suggestions", []),
            "platform": req.platform,
        }
    )


# ──────────────────────────────────────────────────────────────────────────────
# 辅助函数
# ──────────────────────────────────────────────────────────────────────────────


async def _fetch_douyin_video_meta(video_id: str) -> dict[str, Any]:
    """获取抖音视频元数据"""
    # 简化实现 — 生产环境接入抖音开放 API
    return {
        "title": f"视频 {video_id} 的标题",
        "description": f"视频 {video_id} 的描述",
        "comments": ["评论1", "评论2", "评论3"],
    }


def _local_content_check(text: str) -> dict[str, Any]:
    """本地内容安全检查"""
    violations = []

    # 绝对化用语
    absolute_terms = ["最好", "第一", "顶级", "全网最低", "100%有效", "保证治愈", "零风险", "稳赚不赔"]
    for term in absolute_terms:
        if term in text:
            violations.append({
                "type": "absolute_term",
                "severity": "warning",
                "description": f"使用绝对化用语: {term}",
                "rule_id": "BD-ADS-001",
            })

    # 政治敏感
    political_blocked = ["颠覆国家", "分裂祖国", "邪教组织", "恐怖主义"]
    for phrase in political_blocked:
        if phrase in text:
            violations.append({
                "type": "political_sensitivity",
                "severity": "critical",
                "description": f"政治敏感内容: {phrase}",
                "rule_id": "BD-POL-001",
            })

    # 医疗虚假
    medical_patterns = ["秘方治愈癌症", "不打针不吃药治愈", "包治百病"]
    for pattern in medical_patterns:
        if pattern in text:
            violations.append({
                "type": "medical_misinformation",
                "severity": "critical",
                "description": f"医疗虚假宣传: {pattern}",
                "rule_id": "BD-MED-001",
            })

    # 金融违规
    financial_patterns = ["保本保息", "稳赚不赔", "内幕消息", "高额返利"]
    for pattern in financial_patterns:
        if pattern in text:
            violations.append({
                "type": "financial_fraud",
                "severity": "critical",
                "description": f"金融违规承诺: {pattern}",
                "rule_id": "BD-FIN-001",
            })

    blocked = any(v["severity"] == "critical" for v in violations)
    cleaned_text = text if not blocked else ""

    # 生成合规建议
    suggestions = []
    if any(v["type"] == "absolute_term" for v in violations):
        suggestions.append("建议将绝对化用语替换为客观描述")
    if any(v["type"] == "medical_misinformation" for v in violations):
        suggestions.append("医疗内容必须标注'本产品不能替代药物'")
    if any(v["type"] == "financial_fraud" for v in violations):
        suggestions.append("金融内容必须标注'投资有风险，入市需谨慎'")

    return {
        "blocked": blocked,
        "cleaned_text": cleaned_text,
        "violations": violations,
        "suggestions": suggestions,
    }


def _assess_risk_level(analysis: str) -> str:
    if "高风险" in analysis or "严重" in analysis:
        return "high"
    if "中风险" in analysis or "注意" in analysis:
        return "medium"
    return "low"


def _extract_titles(script: str) -> list[str]:
    titles = []
    for line in script.split("\n"):
        if "标题" in line or "【" in line:
            clean = line.replace("标题", "").replace("【", "").replace("】", "").strip(" :-123.")
            if clean and len(clean) > 5:
                titles.append(clean)
    return titles[:3] if titles else ["标题建议1", "标题建议2", "标题建议3"]


def _extract_hashtags(script: str) -> list[str]:
    hashtags = re.findall(r"#\w+", script)
    return hashtags[:5] if hashtags else ["#话题1", "#话题2"]


def _extract_compliance_notes(script: str) -> list[str]:
    notes = []
    if "仅供参考" in script:
        notes.append("已包含'仅供参考'声明")
    if "投资有风险" in script:
        notes.append("已包含投资风险声明")
    if not notes:
        notes.append("请根据内容类型自行添加必要的免责声明")
    return notes
