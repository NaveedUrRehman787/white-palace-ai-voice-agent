# Ubuntu Server Deployment Guide - White Palace AI Voice Agent

This guide provides complete instructions to install and run the White Palace Grill AI Voice Agent project on Ubuntu Server using Docker.

## Prerequisites

- Ubuntu Server 22.04 LTS or later
- Root or sudo access
- Internet connection
- AWS RDS PostgreSQL database (already configured)
- AWS S3 bucket (already configured)
- API keys for LiveKit, OpenAI, Deepgram, Twilio

## 1. System Update & Prerequisites

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y curl wget git htop
```

## 2. Install Docker

```bash
# Download and install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Start and enable Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add current user to docker group (logout/login required after this)
sudo usermod -aG docker $USER

# Verify Docker installation
docker --version
```

## 3. Install Docker Compose

```bash
# Install Docker Compose v2
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify Docker Compose installation
docker-compose --version
```

## 4. Clone Repository

```bash
# Create application directory
sudo mkdir -p /opt/app
sudo chown $USER:$USER /opt/app

# Clone the repository to /opt/app
cd /opt/app
git clone https://github.com/NaveedUrRehman787/white-palace-ai-voice-agent.git
cd white-palace-ai-voice-agent
```

## 5. Configure Environment Variables

```bash
# Copy the production environment template
cp .env.production.example .env

# Edit the .env file with your actual values
nano .env
```

### Required Environment Variables to Update:

```bash
# Database - Update with your AWS RDS endpoint
DATABASE_URL=postgresql://whitepalace:your_password@white-palace-db-prod.c0jg4kiui148.us-east-1.rds.amazonaws.com:5432/white_palace_db

# Frontend - Update with your server IP
VITE_API_URL=http://YOUR_SERVER_IP:5000

# Security - Update with your server IP
ALLOWED_HOSTS=YOUR_SERVER_IP,localhost,127.0.0.1
CORS_ORIGINS=http://YOUR_SERVER_IP:5000,http://localhost:5000

# Keep these as configured (from your existing .env):
# LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET
# OPENAI_API_KEY, DEEPGRAM_API_KEY
# TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
# AWS_S3_BUCKET, AWS_REGION
```

## 6. Security Groups

**Note**: AWS Security Groups are already configured. Ensure the following ports are open:

- **Port 22**: SSH access
- **Port 80**: HTTP (frontend)
- **Port 443**: HTTPS (if using SSL)
- **Port 5000**: Backend API

Verify your EC2 security group allows inbound traffic on these ports from your IP or 0.0.0.0/0 for public access.

## 7. Deploy with Docker

```bash
# Build and start all services in detached mode
docker-compose up -d

# Check if all services are running
docker-compose ps

# View real-time logs
docker-compose logs -f

# View logs for specific service
docker-compose logs backend
docker-compose logs frontend
docker-compose logs livekit-agent
```

## 8. Verify Deployment

```bash
# Check all containers are running
docker ps

# Test backend API health
curl http://localhost:5000/api/health

# Test frontend accessibility
curl http://localhost

# Check application logs for errors
docker-compose logs
```

## 9. Access Your Application

- **Frontend**: `http://YOUR_SERVER_IP`
- **Backend API**: `http://YOUR_SERVER_IP:5000`
- **Health Check**: `http://YOUR_SERVER_IP:5000/api/health`

## Maintenance Commands

### Stop Services

```bash
docker-compose down
```

### Restart Services

```bash
docker-compose restart
```

### Update Deployment

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart with new changes
docker-compose up -d --build
```

### Monitor Resources

```bash
# System resources
htop
df -h
free -h

# Docker containers
docker stats
docker ps
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f livekit-agent

# Last 100 lines
docker-compose logs --tail=100 backend
```

## Troubleshooting

### Docker Permission Issues

If you get "permission denied" errors with Docker:

```bash
# Option 1: Add user to docker group (requires logout/login)
sudo usermod -aG docker $USER
# Logout and login again, or run:
newgrp docker

# Option 2: Run with sudo (not recommended for production)
sudo docker-compose up -d

# Option 3: Check Docker daemon status
sudo systemctl status docker
sudo systemctl start docker

# Option 4: Fix socket permissions (if needed)
sudo chmod 666 /var/run/docker.sock
```

### Services Not Starting

```bash
# Check detailed error logs
docker-compose logs

# Check specific service
docker-compose logs backend

# Restart specific service
docker-compose restart backend

# Rebuild specific service
docker-compose up -d --build backend
```

### Port Conflicts

```bash
# Check what's using ports
sudo netstat -tulpn | grep :5000
sudo netstat -tulpn | grep :80

# Stop conflicting services or change ports in docker-compose.yml
```

### Database Connection Issues

```bash
# Test database connection from container
docker-compose exec backend bash
python -c "import psycopg2; conn = psycopg2.connect(os.environ['DATABASE_URL']); print('DB connected')"
```

### Permission Issues

```bash
# If Docker commands require sudo
sudo usermod -aG docker $USER
# Logout and login again
```

## Security Considerations

1. **Change default passwords** in `.env`
2. **Use strong SECRET_KEY** (generate with `python -c "import secrets; print(secrets.token_hex(32))"`)
3. **Set up SSL/HTTPS** with Let's Encrypt or AWS Certificate Manager
4. **Regular security updates**: `sudo apt update && sudo apt upgrade`
5. **Monitor logs** for suspicious activity
6. **Use AWS security groups** to restrict access

## Backup Strategy

```bash
# Database backup (AWS RDS automated)
# File backups
tar -czf backup-$(date +%Y%m%d).tar.gz /path/to/important/files

# Docker volumes backup
docker run --rm -v white-palace-backend_data:/data -v $(pwd):/backup alpine tar czf /backup/backup.tar.gz -C /data .
```

## Performance Monitoring

```bash
# Monitor container resources
docker stats

# Check disk usage
df -h

# Monitor system logs
sudo journalctl -u docker -f

# Application metrics (if implemented)
curl http://localhost:5000/api/health
```

## Support

If you encounter issues:

1. Check the logs: `docker-compose logs`
2. Verify environment variables in `.env`
3. Ensure AWS RDS security group allows connections
4. Ensure EC2 security group allows required ports (22, 80, 443, 5000)
5. Verify Docker is running: `sudo systemctl status docker`

---

**Server Requirements Reminder:**

- **RAM**: 4GB minimum, 8GB recommended
- **CPU**: 2 vCPUs minimum
- **Storage**: 30GB SSD minimum
- **OS**: Ubuntu 22.04 LTS

**Happy deploying! 🚀**
