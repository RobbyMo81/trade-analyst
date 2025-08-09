# PowerShell script to update the trade-analyst GitHub repository
# Usage: .\update-repo.ps1

param(
    [string]$CommitMessage = "Update trade-analyst application with complete implementation",
    [switch]$DryRun = $false,
    [switch]$Force = $false
)

Write-Host "🚀 Trade Analyst Repository Update Script" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

# Check if we're in the right directory
if (-not (Test-Path "app")) {
    Write-Host "❌ Error: This script must be run from the trade-analyst root directory" -ForegroundColor Red
    exit 1
}

# Check if git is installed
try {
    git --version | Out-Null
} catch {
    Write-Host "❌ Error: Git is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

# Check if we're in a git repository
if (-not (Test-Path ".git")) {
    Write-Host "❌ Error: This is not a git repository" -ForegroundColor Red
    Write-Host "Please initialize git first with: git init" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Prerequisites check passed" -ForegroundColor Green

# Rename gitignore to .gitignore if needed
if (Test-Path "gitignore" -and -not (Test-Path ".gitignore")) {
    Write-Host "🔄 Renaming gitignore to .gitignore..." -ForegroundColor Yellow
    Move-Item "gitignore" ".gitignore"
    Write-Host "✅ Renamed gitignore to .gitignore" -ForegroundColor Green
}

# Check current git status
Write-Host "`n📋 Current Git Status:" -ForegroundColor Cyan
git status --porcelain

# Check remote repository
$remotes = git remote -v
if ($remotes) {
    Write-Host "`n🌐 Remote repositories:" -ForegroundColor Cyan
    $remotes
} else {
    Write-Host "`n⚠️  No remote repositories configured" -ForegroundColor Yellow
    Write-Host "To add the GitHub remote, run:" -ForegroundColor Yellow
    Write-Host "git remote add origin https://github.com/RobbyMo81/trade-analyst.git" -ForegroundColor White
}

# Check for sensitive files that shouldn't be committed
$sensitiveFiles = @()
if (Test-Path ".env") { $sensitiveFiles += ".env" }
if (Test-Path "tokens") { $sensitiveFiles += "tokens/" }
if (Test-Path "data") { $sensitiveFiles += "data/" }
if (Test-Path "logs") { $sensitiveFiles += "logs/" }

if ($sensitiveFiles.Count -gt 0) {
    Write-Host "`n⚠️  Sensitive files/directories detected:" -ForegroundColor Yellow
    $sensitiveFiles | ForEach-Object { Write-Host "   - $_" -ForegroundColor Yellow }
    Write-Host "These should be in .gitignore (they are!)" -ForegroundColor Green
}

# Dry run option
if ($DryRun) {
    Write-Host "`n🔍 DRY RUN MODE - No changes will be made" -ForegroundColor Magenta
    Write-Host "Files that would be added:" -ForegroundColor Cyan
    git add --dry-run .
    exit 0
}

# Ask for confirmation unless force is used
if (-not $Force) {
    Write-Host "`n❓ Do you want to proceed with updating the repository? [Y/N]: " -ForegroundColor Yellow -NoNewline
    $response = Read-Host
    if ($response -ne 'Y' -and $response -ne 'y') {
        Write-Host "❌ Operation cancelled" -ForegroundColor Red
        exit 0
    }
}

# Stage all files
Write-Host "`n📦 Staging files..." -ForegroundColor Cyan
git add .

# Check what's being committed
Write-Host "`n📋 Files to be committed:" -ForegroundColor Cyan
git diff --cached --name-status

# Commit changes
Write-Host "`n💾 Committing changes..." -ForegroundColor Cyan
git commit -m "$CommitMessage"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Commit successful!" -ForegroundColor Green
} else {
    Write-Host "❌ Commit failed!" -ForegroundColor Red
    exit 1
}

# Check if remote exists
$hasOrigin = git remote get-url origin 2>$null
if ($hasOrigin) {
    Write-Host "`n🚀 Pushing to GitHub..." -ForegroundColor Cyan
    
    # Get current branch
    $currentBranch = git branch --show-current
    Write-Host "Current branch: $currentBranch" -ForegroundColor White
    
    # Push to remote
    git push origin $currentBranch
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Push successful!" -ForegroundColor Green
        Write-Host "🌐 Repository updated at: https://github.com/RobbyMo81/trade-analyst" -ForegroundColor Green
    } else {
        Write-Host "❌ Push failed!" -ForegroundColor Red
        Write-Host "You may need to pull first if the remote has changes:" -ForegroundColor Yellow
        Write-Host "git pull origin $currentBranch" -ForegroundColor White
    }
} else {
    Write-Host "`n⚠️  No origin remote found. Add it with:" -ForegroundColor Yellow
    Write-Host "git remote add origin https://github.com/RobbyMo81/trade-analyst.git" -ForegroundColor White
    Write-Host "Then run: git push -u origin main" -ForegroundColor White
}

Write-Host "`n🎉 Repository update complete!" -ForegroundColor Green

# Show final status
Write-Host "`n📊 Final Status:" -ForegroundColor Cyan
git status
