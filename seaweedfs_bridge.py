"""
SOV3 SeaweedFS Bridge
Distributed storage backbone for character assets, MCP packages, audit logs, and blockchain data.

Replaces MinIO (maintenance-only, AGPL risk) with SeaweedFS (Apache 2.0, 31K+ stars).
"""

import os
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

router = APIRouter(prefix="/storage", tags=["seaweedfs"])

# ── Config ───────────────────────────────────────────────────────────────────

SEAWEEDFS_ENDPOINT = os.environ.get("SEAWEEDFS_ENDPOINT", "http://127.0.0.1:8340")
SEAWEEDFS_FILER = os.environ.get("SEAWEEDFS_FILER", "http://127.0.0.1:8889")
SEAWEEDFS_ACCESS_KEY = os.environ.get("SEAWEEDFS_ACCESS_KEY", "MEOK_ACCESS")
SEAWEEDFS_SECRET_KEY = os.environ.get("SEAWEEDFS_SECRET_KEY", "MEOK_SECRET")
MOCK_MODE = os.environ.get("SEAWEEDFS_MOCK", "true").lower() == "true"

# ── In-Memory Mock Store ─────────────────────────────────────────────────────
_mock_storage: Dict[str, Dict[str, Any]] = {}

# ── Data Models ──────────────────────────────────────────────────────────────

class BucketCreateRequest(BaseModel):
    name: str

class ObjectMeta(BaseModel):
    key: str
    bucket: str
    size: Optional[int] = None
    content_type: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None

class StorageHealthResponse(BaseModel):
    status: str
    mock_mode: bool
    endpoint: str
    filer: str
    buckets: List[str]

# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_s3_client():
    try:
        import boto3
        from botocore.config import Config
        return boto3.client(
            's3',
            endpoint_url=SEAWEEDFS_ENDPOINT,
            aws_access_key_id=SEAWEEDFS_ACCESS_KEY,
            aws_secret_access_key=SEAWEEDFS_SECRET_KEY,
            config=Config(signature_version='s3v4')
        )
    except ImportError:
        return None

# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/buckets")
async def create_bucket(request: BucketCreateRequest):
    """Create a new S3 bucket in SeaweedFS."""
    if MOCK_MODE:
        _mock_storage[request.name] = {}
        return {"bucket": request.name, "created": True, "mock": True}
    
    client = _get_s3_client()
    if not client:
        raise HTTPException(status_code=503, detail="boto3 not available")
    
    try:
        client.create_bucket(Bucket=request.name)
        return {"bucket": request.name, "created": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buckets")
async def list_buckets():
    """List all S3 buckets."""
    if MOCK_MODE:
        return {"buckets": list(_mock_storage.keys()), "mock": True}
    
    client = _get_s3_client()
    if not client:
        raise HTTPException(status_code=503, detail="boto3 not available")
    
    try:
        resp = client.list_buckets()
        return {"buckets": [b["Name"] for b in resp.get("Buckets", [])]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/buckets/{bucket}/upload")
async def upload_object(bucket: str, key: str, file: UploadFile = File(...)):
    """Upload an object to SeaweedFS."""
    content = await file.read()
    
    if MOCK_MODE:
        if bucket not in _mock_storage:
            _mock_storage[bucket] = {}
        _mock_storage[bucket][key] = {
            "size": len(content),
            "content_type": file.content_type,
            "data": content,
        }
        return {"bucket": bucket, "key": key, "size": len(content), "mock": True}
    
    client = _get_s3_client()
    if not client:
        raise HTTPException(status_code=503, detail="boto3 not available")
    
    try:
        client.put_object(Bucket=bucket, Key=key, Body=content, ContentType=file.content_type or "application/octet-stream")
        return {"bucket": bucket, "key": key, "size": len(content)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buckets/{bucket}/objects")
async def list_objects(bucket: str, prefix: Optional[str] = None):
    """List objects in a bucket."""
    if MOCK_MODE:
        if bucket not in _mock_storage:
            return {"bucket": bucket, "objects": [], "mock": True}
        objs = [
            {"key": k, "size": v["size"], "content_type": v["content_type"]}
            for k, v in _mock_storage[bucket].items()
            if not prefix or k.startswith(prefix)
        ]
        return {"bucket": bucket, "objects": objs, "mock": True}
    
    client = _get_s3_client()
    if not client:
        raise HTTPException(status_code=503, detail="boto3 not available")
    
    try:
        kwargs = {"Bucket": bucket}
        if prefix:
            kwargs["Prefix"] = prefix
        resp = client.list_objects_v2(**kwargs)
        objs = [{"key": o["Key"], "size": o["Size"]} for o in resp.get("Contents", [])]
        return {"bucket": bucket, "objects": objs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buckets/{bucket}/objects/{key:path}")
async def get_object(bucket: str, key: str):
    """Get object metadata and redirect to download URL."""
    if MOCK_MODE:
        if bucket not in _mock_storage or key not in _mock_storage[bucket]:
            raise HTTPException(status_code=404, detail="Object not found")
        obj = _mock_storage[bucket][key]
        return {
            "bucket": bucket,
            "key": key,
            "size": obj["size"],
            "content_type": obj["content_type"],
            "mock": True,
        }
    
    client = _get_s3_client()
    if not client:
        raise HTTPException(status_code=503, detail="boto3 not available")
    
    try:
        resp = client.head_object(Bucket=bucket, Key=key)
        return {
            "bucket": bucket,
            "key": key,
            "size": resp.get("ContentLength"),
            "content_type": resp.get("ContentType"),
            "last_modified": resp.get("LastModified"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=StorageHealthResponse)
async def storage_health():
    """SeaweedFS bridge health check."""
    buckets = list(_mock_storage.keys()) if MOCK_MODE else []
    
    if not MOCK_MODE:
        client = _get_s3_client()
        if client:
            try:
                resp = client.list_buckets()
                buckets = [b["Name"] for b in resp.get("Buckets", [])]
            except:
                pass
    
    return StorageHealthResponse(
        status="healthy",
        mock_mode=MOCK_MODE,
        endpoint=SEAWEEDFS_ENDPOINT,
        filer=SEAWEEDFS_FILER,
        buckets=buckets,
    )
