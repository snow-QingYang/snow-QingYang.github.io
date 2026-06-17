param()

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

function Get-NodePath {
  $nodeCommand = Get-Command node -ErrorAction SilentlyContinue
  if ($nodeCommand) {
    return $nodeCommand.Source
  }

  $bundledNode = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
  if (Test-Path -LiteralPath $bundledNode) {
    return $bundledNode
  }

  throw "Node.js was not found. Install Node.js or update build.ps1 with the correct node.exe path."
}

Push-Location $Root
try {
  $node = Get-NodePath
  & $node (Join-Path $Root "tools\build-blog.js")
  if ($LASTEXITCODE -ne 0) {
    throw "Static site build failed."
  }

  Write-Host "Built static pages from Markdown."
  Write-Host "Blog source: content\posts"
  Write-Host "Research source: content\research"
  Write-Host "Blog output: blog\"
  Write-Host "Research output: research\"
} finally {
  Pop-Location
}
