# EC2 Deployment Guide - White Palace Grill

This guide outlines how to deploy the full stack to a single AWS EC2 instance using Docker Compose.

## 1. Provision EC2 Instance
You can launch the instance automatically using the provided script:

```bash
chmod +x scripts/launch_ec2.sh
./scripts/launch_ec2.sh
```

This will create a `white-palace-key.pem` in your project root and output the **Public IP** of your new server.

### Manual Alternative (AWS Console)
If you prefer the UI:
- **OS**: Ubuntu 22.04 LTS
- **Instance Type**: `t3.medium` (Minimum 4GB RAM recommended for builds)
- **Security Group**: Open the following ports:
    - `22`: SSH
    - `80`: HTTP (Frontend)
    - `443`: HTTPS (Production)
    - `5000`: Backend API (Inter-container, but useful for debugging)

## 2. Remote Setup
Upload the setup script to your instance and run it:

```bash
# On your local machine:
scp -i your-key.pem scripts/setup_ec2.sh ubuntu@<EC2-IP>:~/
ssh -i your-key.pem ubuntu@<EC2-IP> "chmod +x ~/setup_ec2.sh && ./setup_ec2.sh"
```

*Note: You may need to log out and back in for Docker permissions to take effect.*

## 3. Deployment from Local Machine
Use the deployment script to sync your code and start the application:

```bash
chmod +x scripts/deploy_to_ec2.sh
./scripts/deploy_to_ec2.sh <EC2-IP> <PATH-TO-PEM-KEY>
```

## 4. Environment Variables
After the first deployment, SSH into your EC2 and update the `.env` file with actual production keys:

```bash
ssh -i your-key.pem ubuntu@<EC2-IP>
cd ~/white-palace-app
nano .env
# Restart containers after editing
docker compose up -d
```

## 5. Helpful Commands
- **View Logs**: `docker compose logs -f`
- **Check Status**: `docker compose ps`
- **Stop App**: `docker compose down`
