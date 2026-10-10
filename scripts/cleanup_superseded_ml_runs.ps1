param()
$ErrorActionPreference = 'Stop'
$workspacePath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$mlRootPath = (Resolve-Path -LiteralPath (Join-Path $workspacePath 'backend/data/ml')).Path
$currentRunPath = (Resolve-Path -LiteralPath (Join-Path $mlRootPath 'september-fill-predictor')).Path
foreach ($guardedRootPath in @($workspacePath, $mlRootPath, $currentRunPath)) {
    if ((Get-Item -LiteralPath $guardedRootPath -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "Cleanup root must not be a link or junction: $guardedRootPath"
    }
}
$workspacePrefix = $workspacePath.TrimEnd('\') + '\'
if (-not $mlRootPath.StartsWith($workspacePrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'ML root is outside the intended workspace'
}
$verification = Get-Content -LiteralPath (Join-Path $currentRunPath 'delivery_verification.json') -Raw | ConvertFrom-Json
$productVerification = Get-Content -LiteralPath (Join-Path $currentRunPath 'product_verification.json') -Raw | ConvertFrom-Json
if (-not $verification.passed -or -not $productVerification.passed) {
    throw 'Current delivery and isolated product must pass before cleanup'
}
$allowedNames = @('fill-classifier', 'fill-classifier-priority34-100k')
$targetsToRemove = @()
foreach ($runName in $allowedNames) {
    $candidatePath = Join-Path $mlRootPath $runName
    if (-not (Test-Path -LiteralPath $candidatePath)) { continue }
    $runItem = Get-Item -LiteralPath $candidatePath -Force
    $resolvedTargetPath = (Resolve-Path -LiteralPath $candidatePath).Path
    if (-not $runItem.PSIsContainer -or ($runItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Cleanup target must be an ordinary directory: $candidatePath"
    }
    if ([IO.Path]::GetDirectoryName($resolvedTargetPath) -ne $mlRootPath -or
        [IO.Path]::GetFileName($resolvedTargetPath) -notin $allowedNames -or
        $resolvedTargetPath -eq $currentRunPath) {
        throw "Resolved cleanup target is not an allowlisted immediate child: $resolvedTargetPath"
    }
    $nestedLink = Get-ChildItem -LiteralPath $resolvedTargetPath -Force -Recurse |
        Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint } | Select-Object -First 1
    if ($nestedLink) { throw "Cleanup target contains a link/junction: $($nestedLink.FullName)" }
    $targetsToRemove += $resolvedTargetPath
}
foreach ($verifiedTargetPath in $targetsToRemove) {
    Remove-Item -LiteralPath $verifiedTargetPath -Recurse -Force
}
$absent = @{}
foreach ($runName in $allowedNames) {
    $absent[$runName] = -not (Test-Path -LiteralPath (Join-Path $mlRootPath $runName))
    if (-not $absent[$runName]) { throw "Superseded run remains: $runName" }
}
if (-not (Test-Path -LiteralPath (Join-Path $mlRootPath '.venv/Scripts/python.exe')) -or
    -not (Test-Path -LiteralPath (Join-Path $currentRunPath 'product/model.joblib'))) {
    throw 'Expected environment or current product is missing after cleanup'
}
@{
    completed_at_utc = [DateTime]::UtcNow.ToString('o')
    removed_paths = $targetsToRemove
    absent = $absent
    current_run = $currentRunPath
    prerequisite = 'delivery_verification.json and isolated product verification passed'
    source_hash_recheck = 'Run python -m app.ml.verify --config configs/ml.yaml after cleanup'
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $currentRunPath 'cleanup.json') -Encoding utf8
Write-Output 'Superseded run cleanup complete; current product and environment preserved.'
