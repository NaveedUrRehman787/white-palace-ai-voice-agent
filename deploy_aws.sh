#!/bin/bash

################################################################################
# White Palace Grill - AWS ECR Deployment Script
# Builds and pushes Docker images to AWS Elastic Container Registry
################################################################################

set -e  # Exit on error

# === COLORS FOR OUTPUT ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# === CONFIGURATION ===
AWS_REGION="${1:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)

if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}❌ Error: Could not get AWS Account ID. Make sure AWS CLI is configured.${NC}"
    exit 1
fi

PROJECT_NAME="white-palace"
ECR_URL="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
GIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
IMAGE_TAG="${GIT_HASH:-latest}"

# === DISPLAY CONFIGURATION ===
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🚀 White Palace Grill - AWS ECR Deployment${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}AWS Region:${NC}      ${AWS_REGION}"
echo -e "${YELLOW}AWS Account:${NC}     ${AWS_ACCOUNT_ID}"
echo -e "${YELLOW}ECR Registry:${NC}    ${ECR_URL}"
echo -e "${YELLOW}Project Name:${NC}    ${PROJECT_NAME}"
echo -e "${YELLOW}Image Tag:${NC}       ${IMAGE_TAG}"
echo ""

# === FUNCTION: ERROR HANDLER ===
error_exit() {
    echo -e "${RED}❌ Error: $1${NC}"
    exit 1
}

# === FUNCTION: CREATE ECR REPOSITORY ===
create_repo() {
    local REPO_NAME=$1
    local FULL_REPO="${PROJECT_NAME}-${REPO_NAME}"
    
    echo -e "${YELLOW}📦 Checking repository: ${FULL_REPO}...${NC}"
    
    if aws ecr describe-repositories \
        --repository-names "${FULL_REPO}" \
        --region "${AWS_REGION}" > /dev/null 2>&1; then
        echo -e "${GREEN}   ✅ Repository exists${NC}"
    else
        echo -e "${YELLOW}   📝 Creating repository...${NC}"
        aws ecr create-repository \
            --repository-name "${FULL_REPO}" \
            --region "${AWS_REGION}" \
            --encryption-configuration encryptionType=AES \
            --image-scanning-configuration scanOnPush=true \
            > /dev/null
        echo -e "${GREEN}   ✅ Repository created${NC}"
    fi
}

# === FUNCTION: BUILD AND PUSH IMAGE ===
build_and_push() {
    local SERVICE_NAME=$1
    local DOCKERFILE_PATH=$2
    local BUILD_CONTEXT=$3
    local REPO_NAME="${PROJECT_NAME}-${SERVICE_NAME}"
    local IMAGE_URI="${ECR_URL}/${REPO_NAME}"
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}🔨 Building ${SERVICE_NAME}...${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Check if Dockerfile exists
    if [ ! -f "${DOCKERFILE_PATH}" ]; then
        error_exit "Dockerfile not found: ${DOCKERFILE_PATH}"
    fi
    
    # Build image
    echo -e "${YELLOW}📦 Building Docker image...${NC}"
    if docker build \
        -t "${REPO_NAME}:${IMAGE_TAG}" \
        -t "${REPO_NAME}:latest" \
        -f "${DOCKERFILE_PATH}" \
        "${BUILD_CONTEXT}"; then
        echo -e "${GREEN}✅ Build successful${NC}"
    else
        error_exit "Build failed for ${SERVICE_NAME}"
    fi
    
    # Tag image for ECR
    echo -e "${YELLOW}🏷️  Tagging image...${NC}"
    docker tag "${REPO_NAME}:${IMAGE_TAG}" "${IMAGE_URI}:${IMAGE_TAG}"
    docker tag "${REPO_NAME}:latest" "${IMAGE_URI}:latest"
    
    # Push to ECR
    echo -e "${YELLOW}🔼 Pushing to ECR...${NC}"
    if docker push "${IMAGE_URI}:${IMAGE_TAG}" && docker push "${IMAGE_URI}:latest"; then
        echo -e "${GREEN}✅ Push successful${NC}"
        echo -e "${GREEN}   URI: ${IMAGE_URI}:${IMAGE_TAG}${NC}"
    else
        error_exit "Push failed for ${SERVICE_NAME}"
    fi
}

# === MAIN SCRIPT ===

# Step 1: Check Docker is running
echo -e "${YELLOW}🔍 Checking Docker daemon...${NC}"
if ! docker ps > /dev/null 2>&1; then
    error_exit "Docker daemon is not running. Please start Docker."
fi
echo -e "${GREEN}✅ Docker daemon is running${NC}"

# Step 2: Login to AWS ECR
echo ""
echo -e "${YELLOW}🔑 Logging into AWS ECR...${NC}"
if aws ecr get-login-password --region "${AWS_REGION}" | \
    docker login --username AWS --password-stdin "${ECR_URL}"; then
    echo -e "${GREEN}✅ Successfully logged into ECR${NC}"
else
    error_exit "Failed to login to ECR. Check AWS credentials."
fi

# Step 3: Create repositories
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📦 Creating ECR Repositories${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

create_repo "backend"
create_repo "agent"
create_repo "frontend"

# Step 4: Build and push images
# 🔧 Adjusted paths to match root context for backend and agent
build_and_push "backend" "backend/Dockerfile" "."
build_and_push "agent" "Dockerfile.agent" "."
build_and_push "frontend" "frontend/Dockerfile" "frontend"

# Step 5: Summary
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ SUCCESS: All images pushed to ECR!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "   1. Deploy to ECS Fargate:"
echo "      aws ecs update-service --cluster white-palace --service backend --force-new-deployment"
echo ""
echo "   2. View images in ECR:"
echo "      aws ecr describe-images --repository-name white-palace-backend --region ${AWS_REGION}"
echo ""
echo "   3. Image URIs:"
echo "      ${ECR_URL}/${PROJECT_NAME}-backend:${IMAGE_TAG}"
echo "      ${ECR_URL}/${PROJECT_NAME}-agent:${IMAGE_TAG}"
echo "      ${ECR_URL}/${PROJECT_NAME}-frontend:${IMAGE_TAG}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
