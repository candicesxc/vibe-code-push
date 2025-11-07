# How to Push Your Code to GitHub

## Step 1: Install Git (if not already installed)

If you see "xcode-select: note: no developer tools were found", you need to install Git:

**Option A: Install Xcode Command Line Tools**
```bash
xcode-select --install
```
Then follow the dialog that appears.

**Option B: Install Git via Homebrew**
```bash
brew install git
```

**Option C: Download Git directly**
Visit: https://git-scm.com/download/mac

## Step 2: Configure Git (first time only)

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

## Step 3: Initialize Git Repository

```bash
cd "/Users/xinchenshen/Desktop/Vibe Coding"
git init
```

## Step 4: Add All Files

```bash
git add .
```

This will add all files except `.env` (which is in `.gitignore` to protect your API keys).

## Step 5: Create Initial Commit

```bash
git commit -m "Initial commit: Bitcoin Trading Analysis System with CrewAI

- Added Bitcoin analyzer with 5 agents (Search, Reader, Synthesis, Analyst, Website)
- Integrated SerpAPI for web search
- Created HTML report generation (output.html and newpage.html)
- Added email functionality to send reports
- SEVENTEEN and Blackpink themed designs
- Professional Wall Street trader tone option
- Complete requirements.txt and README"
```

## Step 6: Create GitHub Repository

1. Go to https://github.com and sign in
2. Click the "+" icon in the top right
3. Select "New repository"
4. Name it (e.g., "bitcoin-trading-analyzer")
5. Choose Public or Private
6. **DO NOT** initialize with README, .gitignore, or license (we already have these)
7. Click "Create repository"

## Step 7: Connect Local Repository to GitHub

After creating the repository, GitHub will show you commands. Use these:

```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` and `YOUR_REPO_NAME` with your actual GitHub username and repository name.

## Step 8: Push Your Code

```bash
git push -u origin main
```

You may be prompted for your GitHub username and password (or personal access token).

## Important Notes:

✅ **Your `.env` file is already in `.gitignore`** - it won't be pushed to GitHub (protecting your API keys)

✅ **Files that WILL be pushed:**
- bitcoin_analyzer.py
- send_email.py
- requirements.txt
- README.md
- .gitignore
- output.html (if exists)
- newpage.html (if exists)

❌ **Files that WON'T be pushed (protected by .gitignore):**
- .env (contains your API keys)
- __pycache__/
- *.pyc files
- .DS_Store

## Troubleshooting:

**If you get authentication errors:**
- Use a Personal Access Token instead of password
- Generate one at: https://github.com/settings/tokens
- Use the token as your password when pushing

**If you need to update later:**
```bash
git add .
git commit -m "Your update message"
git push
```

