#!/usr/bin/env bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "==================================="
echo "CloudFormation Template Validator"
echo "==================================="
echo ""

# Check if cfn-lint is installed
if ! command -v cfn-lint &> /dev/null; then
    echo -e "${YELLOW}cfn-lint not found. Installing...${NC}"
    pip install cfn-lint --quiet
    if ! command -v cfn-lint &> /dev/null; then
        echo -e "${RED}Failed to install cfn-lint. Please install it manually.${NC}"
        exit 1
    fi
    echo -e "${GREEN}cfn-lint installed successfully.${NC}"
fi

# Find the CloudFormation directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CFN_DIR="${SCRIPT_DIR}/../cloudformation"

if [[ ! -d "${CFN_DIR}" ]]; then
    echo -e "${RED}CloudFormation directory not found at ${CFN_DIR}${NC}"
    exit 1
fi

echo "Validating CloudFormation templates in: ${CFN_DIR}"
echo ""

# Count templates
TEMPLATE_COUNT=$(find "${CFN_DIR}" -name "*.yaml" -o -name "*.yml" -o -name "*.json" | wc -l)
echo "Found ${TEMPLATE_COUNT} template files"
echo ""

# Run cfn-lint
ERRORS=0
WARNINGS=0

# Validate root stack first
echo "Validating root-stack.yaml..."
if cfn-lint "${CFN_DIR}/root-stack.yaml"; then
    echo -e "${GREEN}✓ root-stack.yaml passed validation${NC}"
else
    echo -e "${RED}✗ root-stack.yaml has errors${NC}"
    ((ERRORS++))
fi
echo ""

# Validate all stacks
for template in "${CFN_DIR}"/stacks/*.yaml; do
    if [[ -f "${template}" ]]; then
        filename=$(basename "${template}")
        echo "Validating ${filename}..."
        if cfn-lint "${template}"; then
            echo -e "${GREEN}✓ ${filename} passed validation${NC}"
        else
            echo -e "${RED}✗ ${filename} has errors${NC}"
            ((ERRORS++))
        fi
        echo ""
    fi
done

# Summary
echo "==================================="
echo "Validation Summary"
echo "==================================="
echo ""
if [[ ${ERRORS} -eq 0 ]]; then
    echo -e "${GREEN}All ${TEMPLATE_COUNT} templates passed validation!${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}${ERRORS} template(s) failed validation${NC}"
    echo ""
    exit 1
fi
