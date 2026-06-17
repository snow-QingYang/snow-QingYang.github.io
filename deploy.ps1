param(
  [string]$Message = "Update site",
  [string]$Remote = "origin",
  [string]$Branch = ""
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

function Stop-Deploy {
  param([string]$Text)
  Write-Host "ERROR: $Text" -ForegroundColor Red
  exit 1
}

Push-Location $Root
try {
  & (Join-Path $Root "build.ps1")

  if (-not (Test-Path -LiteralPath (Join-Path $Root ".git"))) {
    Stop-Deploy "This folder is not a Git repository."
  }

  if (-not $Branch) {
    $Branch = (git branch --show-current).Trim()
  }

  if (-not $Branch) {
    Stop-Deploy "Could not determine the current Git branch. Pass -Branch explicitly."
  }

  $remoteUrl = $null
  try {
    $remoteUrl = git remote get-url $Remote 2>$null
  } catch {
    $remoteUrl = $null
  }

  if (-not $remoteUrl) {
    Stop-Deploy "Git remote '$Remote' is not configured. Add it first, for example: git remote add origin https://github.com/snow-QingYang/snow-QingYang.github.io.git"
  }

  $status = git status --short
  if (-not $status) {
    Write-Host "Nothing changed after build. No deploy needed."
    return
  }

  git add -- .gitignore README.md index.html styles.css script.js build.ps1 deploy.ps1 tools assets content blog research
  if ($LASTEXITCODE -ne 0) {
    throw "git add failed."
  }

  git commit -m $Message
  if ($LASTEXITCODE -ne 0) {
    throw "git commit failed."
  }

  git push $Remote $Branch
  if ($LASTEXITCODE -ne 0) {
    throw "git push failed."
  }

  Write-Host "Deployed to $Remote/$Branch."
} finally {
  Pop-Location
}
