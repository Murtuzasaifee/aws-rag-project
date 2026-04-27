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
    echo -e "${BLUE}Usage:${NC} $0 <environment> [options]"
    echo ""
    echo "Arguments:"
    echo "  environment    Deployment environment (dev, staging, prod)"
    echo ""
    echo "Options:"
    echo "  --skip-s3-empty    Skip emptying S3 buckets (faster but may fail if buckets have objects)"
    echo "  --force            Force deletion without confirmation prompt"
    echo "  -h, --help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 dev"
    echo "  $0 staging --force"
    echo "  $0 prod --skip-s3-empty"
    exit 1
}

# Parse arguments
if [[ $# -lt 1 ]]; then
    usage
fi

ENVIRONMENT=$1
shift

# Default values
SKIP_S3_EMPTY=false
FORCE=false

# Parse optional arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-s3-empty)
            SKIP_S3_EMPTY=true
            shift
            ;;
        --force)
            FORCE=true
            shift
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

# Set stack name
STACK_NAME="rag-ingestion-${ENVIRONMENT}"

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

# Check if stack exists
echo ""
echo -e "${BLUE}Checking if stack exists...${NC}"
if ! aws cloudformation describe-stacks --stack-name "${STACK_NAME}" &> /dev/null; then
    echo -e "${YELLOW}Stack ${STACK_NAME} does not exist.${NC}"
    exit 0
fi

echo -e "${GREEN}Stack ${STACK_NAME} found.${NC}"

# Get stack info for confirmation
echo ""
echo -e "${BLUE}Retrieving stack information...${NC}"
STACK_INFO=$(aws cloudformation describe-stacks --stack-name "${STACK_NAME}" --query 'Stacks[0].[CreationTime,StackStatus]' --output text)
echo "Stack Created: $(echo "${STACK_INFO}" | awk '{print $1 " " $2}')"
echo "Stack Status: $(echo "${STACK_INFO}" | awk '{print $3}')"

# Confirm deletion
if [[ "${FORCE}" != true ]]; then
    echo ""
    echo -e "${RED}WARNING: This will permanently delete all resources in stack: ${STACK_NAME}${NC}"
    echo -e "${YELLOW}This action cannot be undone!${NC}"
    echo ""
    echo "The following resources will be deleted:"
    echo "  - S3 buckets and all their contents"
    echo "  - SQS queues"
    echo "  - DynamoDB tables"
    echo "  - KMS keys"
    echo "  - CloudWatch alarms"
    echo "  - IAM roles (if created by this stack)"
    echo ""
    read -p "Are you sure you want to continue? Type 'yes' to proceed: " CONFIRM
    if [[ "${CONFIRM}" != "yes" ]]; then
        echo -e "${YELLOW}Deletion cancelled.${NC}"
        exit 0
    fi
fi

# Empty S3 buckets if not skipped
if [[ "${SKIP_S3_EMPTY}" != true ]]; then
    echo ""
    echo -e "${BLUE}Emptying S3 buckets...${NC}"

    # Get list of S3 buckets from the stack
    BUCKET_NAMES=$(aws cloudformation list-stack-resources \
        --stack-name "${STACK_NAME}" \
        --query "StackResourceSummaries[?ResourceType=='AWS::S3::Bucket'].PhysicalResourceId" \
        --output text 2>/dev/null || true)

    if [[ -n "${BUCKET_NAMES}" && "${BUCKET_NAMES}" != "None" ]]; then
        for bucket in ${BUCKET_NAMES}; do
            echo -e "  Emptying bucket: ${YELLOW}${bucket}${NC}"

            # Delete all objects (including versions if versioning is enabled)
            if aws s3api list-object-versions --bucket "${bucket}" --max-items 1 &> /dev/null; then
                # Delete all versions
                aws s3api delete-objects \
                    --bucket "${bucket}" \
                    --delete "$(aws s3api list-object-versions --bucket "${bucket}" --output json --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}')" 2>/dev/null || true

                # Delete delete markers
                aws s3api delete-objects \
                    --bucket "${bucket}" \
                    --delete "$(aws s3api list-object-versions --bucket "${bucket}" --output json --query '{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}')" 2>/dev/null || true
            fi

            # Delete remaining objects (non-versioned)
            aws s3 rm "s3://${bucket}" --recursive 2>/dev/null || true

            echo -e "  ${GREEN}✓ Bucket ${bucket} emptied${NC}"
        done
    else
        echo -e "  ${YELLOW}No S3 buckets found in stack${NC}"
    fi
else
    echo ""
    echo -e "${YELLOW}Skipping S3 bucket emptying (may cause deletion failures if buckets have objects)${NC}"
fi

# Delete the CloudFormation stack
echo ""
echo -e "${BLUE}Deleting CloudFormation stack: ${STACK_NAME}${NC}"
echo ""

aws cloudformation delete-stack --stack-name "${STACK_NAME}"

echo -e "${GREEN}Stack deletion initiated.${NC}"
echo ""
echo -e "${BLUE}Waiting for stack deletion to complete...${NC}"
echo "(This may take several minutes)"
echo ""

# Wait for deletion with timeout
if aws cloudformation wait stack-delete-complete --stack-name "${STACK_NAME}"; then
    echo ""
    echo -e "${GREEN}====================================${NC}"
    echo -e "${GREEN}  Stack deleted successfully!       ${NC}"
    echo -e "${GREEN}====================================${NC}"
    echo ""
    echo -e "Stack Name: ${YELLOW}${STACK_NAME}${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}====================================${NC}"
    echo -e "${RED}  Stack deletion failed or timed out${NC}"
    echo -e "${RED}====================================${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo "  1. Check the CloudFormation console for detailed error messages"
    echo "  2. Run: aws cloudformation describe-stack-events --stack-name ${STACK_NAME}"
    echo "  3. Some resources may have been retained and need manual deletion"
    echo ""
    exit 1
fi
