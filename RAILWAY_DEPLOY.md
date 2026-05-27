# SOV3 — Railway.app Deployment Guide

## Why Railway?
Vast.ai is for GPU training jobs, not persistent API servers. Railway gives you:
- **Persistent uptime** — no instance expiry
- **PostgreSQL + pgvector** — included, managed, backed up
- **London region** — low latency for UK users
- **Auto-deploy** — push to GitHub → auto-deploy
- **Cost**: ~$5/mo (1 vCPU, 512MB RAM, included Postgres)

## Prerequisites
- Railway account at railway.app
- Railway CLI: `npm install -g @railway/cli`
- GitHub repo with this code pushed

## Step 1: Create Railway Project
```bash
cd /clawd/sovereign-temple
railway login
railway init
# Select "Empty project"
# Name: meok-sov3
```

## Step 2: Add PostgreSQL with pgvector
In Railway dashboard:
1. Click "+ New" → "Database" → "PostgreSQL"
2. After Postgres is created, click it → Settings → Extensions
3. Enable `pgvector` extension
4. Copy the `DATABASE_URL` connection string

## Step 3: Set Environment Variables
In Railway dashboard → Your service → Variables, set:
```
POSTGRES_DSN=${{Postgres.DATABASE_URL}}
ENCRYPTION_SECRET=<generate with: openssl rand -hex 32>
APP_ENV=production
GUARDIAN_WEBHOOK_URL=https://meok-sov3.up.railway.app/api/guardian/alert
SOV3_ADMIN_TOKEN=<generate with: openssl rand -hex 32>
```

## Step 4: Deploy
```bash
railway up
```
Or connect GitHub repo in Railway dashboard for auto-deploy on push.

## Step 5: Run Migrations
After first deploy:
```bash
# Get a shell in Railway
railway run bash

# Run migrations
cd /app
psql $POSTGRES_DSN < /app/migrations/001_initial.sql
psql $POSTGRES_DSN < /app/migrations/002_ralph_tasks.sql
psql $POSTGRES_DSN < /app/migrations/003_characters.sql
```

Or via Railway CLI:
```bash
railway run python scripts/reseed_agents.py
railway run python scripts/create_dummy_models.py
```

## Step 6: Update MEOK UI Environment
In Vercel dashboard → meok-ui → Settings → Environment Variables:
```
SOV3_API_URL=https://meok-sov3.up.railway.app
NEXT_PUBLIC_SOV3_ENDPOINT=https://meok-sov3.up.railway.app
```

## Step 7: Verify
```bash
curl https://meok-sov3.up.railway.app/health
# Should return: {"status": "ok", "db": "connected", ...}
```

## Fly.io Alternative
If Railway doesn't work, use Fly.io (London region, Docker-native):
```bash
brew install flyctl
fly auth login
fly launch --name meok-sov3 --region lhr
fly postgres create --name meok-sov3-db --region lhr
fly postgres attach meok-sov3-db
fly deploy
```

## Cost Breakdown
| Service | Monthly Cost |
|---------|-------------|
| Railway Hobby Plan | $5/mo |
| Postgres (500MB) | Included |
| Bandwidth (10GB) | Included |
| **Total** | **~$5/mo** |

## Monitoring
- Railway dashboard shows CPU/memory/network graphs
- Logs: `railway logs --tail`
- Health check: `curl https://meok-sov3.up.railway.app/health`

## Rollback
```bash
railway rollback
```

---
*Last updated: 2026-03-22 | Replace Vast.ai instance 33199588 (expired)*
