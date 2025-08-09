<#
.SYNOPSIS
    Stages, commits, and pushes all local changes to the GitHub remote.
.PARAMETER CommitMessage
    The message to use for the git commit. A default message with a timestamp is used if not provided.
.EXAMPLE
    .\sync-repo.ps1
    Uses the default commit message.
.EXAMPLE
    .\sync-repo.ps1 -CommitMessage "Feat: Add new data processing logic"
    Uses a custom message for the commit.
#>
[CmdletBinding()]
param (
    # The commit message. Defaults to a generic message with the current date and time.
    [string]$CommitMessage = "Sync: Update project files on $(Get-Date)"
)

Write-Host "🚀 Starting repository sync..."

# 1. Stage all changes (new, modified, deleted files)
git add .
if (-not $?) { Write-Error "Failed to stage files. Aborting."; return }
Write-Host "✅ Files staged for commit."

# 2. Commit the staged files with the provided message
git commit -m "$CommitMessage"
if (-not $?) { Write-Error "Failed to commit files. Nothing to commit or git error. Aborting."; return }
Write-Host "✅ Files committed with message: `"$CommitMessage`""

# 3. Push the commit to the remote repository (assumes 'origin' and 'main' branch)
git push
if (-not $?) { Write-Error "Failed to push to remote repository. Aborting."; return }
Write-Host "✅ Commit pushed to remote."

Write-Host "`n🎉 Repository sync complete!"