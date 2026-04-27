#!/usr/bin/env bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Usage function
usage() {
    echo -e "${BLUE}Usage:${NC} $0 <environment> <org-list> [options]"
    echo ""
    echo "Arguments:"
    echo "  environment    Deployment environment (dev, staging, prod)"
    echo "  org-list       Comma-separated list of organization IDs (e.g., acme,globex,initech)"
    echo ""
    echo "Options:"
    echo "  -e, --email     Alert email for DLQ notifications (default: alerts@example.com)"
    echo "  -f, --frontend  Frontend origin for CORS (default: *)"
    echo "  -a, --api-role  ARN of existing FastAPI IAM role (optional)"
    echo "  -p, --processor-role  ARN of existing processor IAM role (optional)"
    echo "  -h, --help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 dev acme,globex"
    echo "  $0 prod acme,globex,initech -e ops@example.com -f https://app.example.com"
    exit 1
}

# Parse arguments
if [[ $# -lt 2 ]]; then
    usage
fi

ENVIRONMENT=$1
ORG_LIST=$2
shift 2

# Default values
ALERT_EMAIL="alerts@example.com"
FRONTEND_ORIGIN="*"
API_ROLE_ARN=""
PROCESSOR_ROLE_ARN=""

# Parse optional arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--email)
            ALERT_EMAIL="$2"
            shift 2
            ;;
        -f|--frontend)
            FRONTEND_ORIGIN="$2"
            shift 2
            ;;
        -a|--api-role)
            API_ROLE_ARN="$2"
            shift 2
            ;;
        -p|--processor-role)
            PROCESSOR_ROLE_ARN="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    echo -e "${RED}Error: Environment must be dev, staging, or prod${NC}"
    exit 1
fi

# Validate org list
if [[ -z "$ORG_LIST" ]]; then
    echo -e "${RED}Error: Organization list cannot be empty${NC}"
    exit 1
fi

# Set stack name
STACK_NAME="rag-ingestion-${ENVIRONMENT}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CFN_DIR="${SCRIPT_DIR}/../cloudformation"
TEMPLATE="${CFN_DIR}/root-stack.yaml"

# Check if template exists
if [[ ! -f "${TEMPLATE}" ]]; then
    echo -e "${RED}Error: Template not found at ${TEMPLATE}${NC}"
    exit 1
fi

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    exit 1
fi

# Check AWS credentials
echo -e "${BLUE}Checking AWS credentials...${NC}"
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: AWS credentials not configured or invalid${NC}"
    exit 1
fi
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}Authenticated to AWS Account: ${ACCOUNT_ID}${NC}"

# Build parameter overrides
PARAM_OVERRIDES="Environment=${ENVIRONMENT} Organisations=${ORG_LIST}"

if [[ -n "${ALERT_EMAIL}" ]]; then
    PARAM_OVERRIDES="${PARAM_OVERRIDES} AlertEmail=${ALERT_EMAIL}"
fi

if [[ -n "${FRONTEND_ORIGIN}" ]]; then
    PARAM_OVERRIDES="${PARAM_OVERRIDES} FrontendOrigin=${FRONTEND_ORIGIN}"
fi

if [[ -n "${API_ROLE_ARN}" ]]; then
    PARAM_OVERRIDES="${PARAM_OVERRIDES} ApiRoleArn=${API_ROLE_ARN}"
fi

if [[ -n "${PROCESSOR_ROLE_ARN}" ]]; then
    PARAM_OVERRIDES="${PARAM_OVERRIDES} ProcessorRoleArn=${PROCESSOR_ROLE_ARN}"
fi

# Print deployment info
echo ""
echo -e "${BLUE}====================================${NC}"
echo -e "${BLUE}  CloudFormation Deployment Summary  ${NC}"
echo -e "${BLUE}====================================${NC}"
echo ""
echo -e "Stack Name:        ${YELLOW}${STACK_NAME}${NC}"
echo -e "Environment:       ${YELLOW}${ENVIRONMENT}${NC}"
echo -e "Organizations:     ${YELLOW}${ORG_LIST}${NC}"
echo -e "Alert Email:       ${YELLOW}${ALERT_EMAIL}${NC}"
echo -e "Frontend Origin:   ${YELLOW}${FRONTEND_ORIGIN}${NC}"
if [[ -n "${API_ROLE_ARN}" ]]; then
    echo -e "API Role ARN:      ${YELLOW}${API_ROLE_ARN}${NC}"
fi
if [[ -n "${PROCESSOR_ROLE_ARN}" ]]; then
    echo -e "Processor Role:    ${YELLOW}${PROCESSOR_ROLE_ARN}${NC}"
fi
echo ""
echo -e "Template:          ${YELLOW}${TEMPLATE}${NC}"
echo ""

# Confirm deployment
if [[ "${ENVIRONMENT}" == "prod" ]]; then
    echo -e "${RED}WARNING: You are about to deploy to PRODUCTION!${NC}"
    read -p "Are you sure you want to continue? (yes/no): " CONFIRM
    if [[ "${CONFIRM}" != "yes" ]]; then
        echo -e "${YELLOW}Deployment cancelled.${NC}"
        exit 0
    fi
else
    read -p "Do you want to proceed with the deployment? (yes/no): " CONFIRM
    if [[ "${CONFIRM}" != "yes" ]]; then
        echo -e "${YELLOW}Deployment cancelled.${NC}"
        exit 0
    fi
fi

# Deploy the stack
echo ""
echo -e "${BLUE}Deploying CloudFormation stack...${NC}"
echo ""

set +e
DEPLOY_OUTPUT=$(aws cloudformation deploy \
    --stack-name "${STACK_NAME}" \
    --template-file "${TEMPLATE}" \
    --parameter-overrides ${PARAM_OVERRIDES} \
    --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
    --no-fail-on-empty-changeset \
    --tags \
        project=rag \
        environment="${ENVIRONMENT}" \
        managed_by=cloudformation \
    2>&1)

DEPLOY_EXIT_CODE=$?
set -e

# Display output
echo "${DEPLOY_OUTPUT}"

if [[ ${DEPLOY_EXIT_CODE} -eq 0 ]]; then
    echo ""
    echo -e "${GREEN}====================================${NC}"
    echo -e "${GREEN}  Deployment completed successfully! ${NC}"
    echo -e "${GREEN}====================================${NC}"
    echo ""
    echo -e "Stack Name: ${YELLOW}${STACK_NAME}${NC}"

    # Get stack outputs
    echo ""
    echo -e "${BLUE}Stack Outputs:${NC}"
    aws cloudformation describe-stacks \
        --stack-name "${STACK_NAME}" \
        --query 'Stacks[0].Outputs[*].[OutputKey, OutputValue]' \
        --output table 2>/dev/null || true

    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "  1. Check the CloudFormation console for stack details"
    echo "  2. Verify resources were created in the AWS Console"
    echo "  3. Test the API endpoints"
    exit 0
else
    echo ""
    echo -e "${RED}====================================${NC}"
    echo -e "${RED}      Deployment failed!            ${NC}"
    echo -e "${RED}====================================${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting tips:${NC}"
    echo "  1. Check CloudFormation events in AWS Console"
    echo "  2. Run: aws cloudformation describe-stack-events --stack-name ${STACK_NAME}"
    echo "  3. Check IAM permissions"
    echo ""
    exit 1
fi
