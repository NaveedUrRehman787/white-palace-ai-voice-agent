# ============================================
# White Palace Grill - Docker Deployment Guide
# ============================================

## Quick Start

### 1. Setup Environment Variables

```bash
# Copy the example environment file
cp .env.docker.example .env

# Edit with your actual credentials
nano .env
```

### 2. Build and Start All Services

```bash
# Build all containers
docker compose build

# Start all services in detached mode
docker compose up -d

# View logs
docker compose logs -f
```

### 3. Verify Services are Running

```bash
# Check container status
docker compose ps

# Check agent logs specifically
docker compose logs -f livekit-agent
```

---

## Individual Service Commands

### LiveKit Agent Only

```bash
# Build agent container
docker build -f Dockerfile.agent -t whitepalace-agent .

# Run agent container
docker run -d \
  --name whitepalace-livekit-agent \
  --restart always \
  -e LIVEKIT_URL=wss://your-project.livekit.cloud \
  -e LIVEKIT_API_KEY=your_key \
  -e LIVEKIT_API_SECRET=your_secret \
  -e OPENAI_API_KEY=sk-... \
  -e DEEPGRAM_API_KEY=... \
  -e BACKEND_URL=http://your-backend:5000 \
  whitepalace-agent
```

### Backend Only

```bash
docker build -f Dockerfile.backend -t whitepalace-backend .
docker run -d -p 5000:5000 --name whitepalace-backend whitepalace-backend
```

---

## Cloud Deployment Options

### Option 1: Railway.app (Easiest)

1. Connect your GitHub repository
2. Railway auto-detects the docker-compose.yml
3. Set environment variables in Railway dashboard
4. Deploy!

### Option 2: DigitalOcean App Platform

```bash
# Install doctl CLI
doctl apps create --spec .do/app.yaml
```

### Option 3: AWS ECS / Google Cloud Run

```bash
# Build and push to container registry
docker build -f Dockerfile.agent -t your-registry/whitepalace-agent .
docker push your-registry/whitepalace-agent

# Deploy to cloud service
# (Follow your cloud provider's container deployment guide)
```

### Option 4: VPS with Docker

```bash
# SSH into your VPS
ssh user@your-server

# Clone repository
git clone https://github.com/your-repo/white-palace-ai-voice-agent.git
cd white-palace-ai-voice-agent

# Setup and run
cp .env.docker.example .env
nano .env  # Add your credentials
docker compose up -d
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DOCKER COMPOSE STACK                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │  livekit-agent   │───▶│     backend      │───▶│   postgres    │  │
│  │  (Voice Agent)   │    │   (Flask API)    │    │  (Database)   │  │
│  │                  │    │                  │    │               │  │
│  │  Connects to     │    │  Port: 5000      │    │  Port: 5432   │  │
│  │  LiveKit Cloud   │    │  /api/*          │    │               │  │
│  └──────────────────┘    └──────────────────┘    └───────────────┘  │
│           │                      │                                   │
│           │                      ▼                                   │
│           │              ┌──────────────────┐                        │
│           │              │    frontend      │                        │
│           │              │  (React + Vite)  │                        │
│           │              │                  │                        │
│           │              │  Port: 3000      │                        │
│           │              └──────────────────┘                        │
│           │                                                          │
│           ▼                                                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                      LIVEKIT CLOUD                            │   │
│  │  - Manages rooms                                              │   │
│  │  - Routes SIP calls (Twilio)                                  │   │
│  │  - Dispatches agents                                          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Monitoring & Troubleshooting

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f livekit-agent
docker compose logs -f backend

# Last 100 lines
docker compose logs --tail=100 livekit-agent
```

### Restart Services

```bash
# Restart all
docker compose restart

# Restart specific service
docker compose restart livekit-agent
```

### Check Health

```bash
# Container health status
docker compose ps

# Backend health endpoint
curl http://localhost:5000/api/health
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Agent not receiving calls | Check LIVEKIT_URL, API_KEY, API_SECRET are correct |
| Backend DB connection error | Ensure postgres is running and DATABASE_URL is correct |
| Agent tools failing | Check BACKEND_URL is `http://backend:5000` (docker network) |
| OpenAI/Deepgram errors | Verify API keys are set correctly |

---

## Updating

```bash
# Pull latest code
git pull

# Rebuild and restart
docker compose down
docker compose build --no-cache
docker compose up -d
```

---

## Production Checklist

- [ ] All environment variables set in `.env`
- [ ] LiveKit Cloud project configured with SIP Trunk
- [ ] Twilio number configured to dial LiveKit SIP
- [ ] Database migrations applied
- [ ] SSL/TLS configured (if using custom domain)
- [ ] Logging and monitoring set up
- [ ] Backup strategy for database

