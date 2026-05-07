$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path $scriptDir

$entrypoint = Join-Path $scriptDir "app.py"
if (-not (Test-Path -LiteralPath $entrypoint)) {
    Write-Error "Could not find app.py in '$scriptDir'. Run this launcher from the AD-HDTV repository root."
    exit 1
}

$pythonCommand = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCommand = @("py", "-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCommand = @("python")
}

if (-not $pythonCommand) {
    Write-Host "[ERROR] Python 3 was not found."
    Write-Host "[ERROR] Install Python 3.8+ from https://www.python.org/downloads/"
    Write-Host "[ERROR] Then install dependencies with: py -3 -m pip install -r requirements.txt"
    exit 1
}

$pythonInstallHint = if ($pythonCommand[0] -eq "py") { "py -3" } else { "python" }

$invokeArgs = @()
if ($pythonCommand.Length -gt 1) {
    $invokeArgs += $pythonCommand[1..($pythonCommand.Length - 1)]
}
$invokeArgs += $entrypoint
$invokeArgs += $args

& $pythonCommand[0] @invokeArgs
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] AD-HDTV exited with code $exitCode."
    Write-Host "[ERROR] If dependencies are missing, run: $pythonInstallHint -m pip install -r requirements.txt"
    Write-Host "[ERROR] Ensure VLC is installed from https://www.videolan.org/vlc/"
}
exit $exitCode
