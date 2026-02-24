#!/bin/bash
# Clone Team Alignment Engine to local Mac
# Run this script on your Mac: bash clone_to_local.sh

set -e  # Exit on error

# Configuration
GITHUB_ORG="Talchain"
REPO_NAME="Team-Alignment-Engine"
BRANCH="claude/analyze-tae-repo-01UdbcekKCt4Sr4eDVBcq3TE"
LOCAL_PATH="/Users/paulslee/Documents/GitHub"

echo "=========================================="
echo "Team Alignment Engine - Local Clone"
echo "=========================================="
echo ""
echo "Target: ${LOCAL_PATH}/${REPO_NAME}"
echo "Branch: ${BRANCH}"
echo ""

# Create directory if it doesn't exist
mkdir -p "${LOCAL_PATH}"

# Navigate to target directory
cd "${LOCAL_PATH}"

# Check if directory already exists
if [ -d "${REPO_NAME}" ]; then
    echo "⚠️  Directory already exists. Options:"
    echo "  1. Update existing repository"
    echo "  2. Delete and re-clone"
    echo "  3. Cancel"
    read -p "Choose (1/2/3): " choice

    case $choice in
        1)
            echo "Updating existing repository..."
            cd "${REPO_NAME}"
            git fetch origin
            git checkout "${BRANCH}"
            git pull origin "${BRANCH}"
            echo "✅ Repository updated!"
            ;;
        2)
            echo "Deleting existing repository..."
            rm -rf "${REPO_NAME}"
            echo "Cloning fresh copy..."
            git clone "https://github.com/${GITHUB_ORG}/${REPO_NAME}.git"
            cd "${REPO_NAME}"
            git checkout "${BRANCH}"
            echo "✅ Repository cloned!"
            ;;
        3)
            echo "Cancelled."
            exit 0
            ;;
        *)
            echo "Invalid choice. Cancelled."
            exit 1
            ;;
    esac
else
    echo "Cloning repository..."
    git clone "https://github.com/${GITHUB_ORG}/${REPO_NAME}.git"
    cd "${REPO_NAME}"
    git checkout "${BRANCH}"
    echo "✅ Repository cloned!"
fi

echo ""
echo "=========================================="
echo "Repository Information"
echo "=========================================="
git log --oneline -5
echo ""

echo "=========================================="
echo "Documentation Files"
echo "=========================================="
ls -lh *.md

echo ""
echo "✅ Setup complete!"
echo ""
echo "Repository location: ${LOCAL_PATH}/${REPO_NAME}"
echo "Current branch: $(git branch --show-current)"
echo ""
echo "Next steps:"
echo "  cd ${LOCAL_PATH}/${REPO_NAME}"
echo "  open README.md"
echo ""
