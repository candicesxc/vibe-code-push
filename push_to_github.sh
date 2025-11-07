#!/bin/bash
# Script to push code to GitHub

echo "🚀 Setting up Git repository..."

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed. Please install it first:"
    echo "   xcode-select --install"
    exit 1
fi

# Initialize git if not already done
if [ ! -d .git ]; then
    git init
    echo "✅ Git repository initialized"
fi

# Add all files
git add .
echo "✅ Files added to staging"

# Show what will be committed
echo ""
echo "📋 Files to be committed:"
git status --short

# Create commit
echo ""
read -p "Enter commit message (or press Enter for default): " commit_msg
if [ -z "$commit_msg" ]; then
    commit_msg="Initial commit: Bitcoin Trading Analysis System with CrewAI"
fi

git commit -m "$commit_msg"
echo "✅ Commit created"

# Check if remote exists
if ! git remote | grep -q origin; then
    echo ""
    echo "📝 You need to add a GitHub remote repository:"
    echo "   1. Create a new repository on GitHub"
    echo "   2. Then run: git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
    echo "   3. Then run: git push -u origin main"
else
    echo ""
    echo "🌐 Pushing to GitHub..."
    git push -u origin main
    echo "✅ Code pushed to GitHub!"
fi
