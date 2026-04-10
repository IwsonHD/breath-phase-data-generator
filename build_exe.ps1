param(
    [switch]$OneFile = $true,
    [string]$Name = "BreathingRecorder"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    throw "Python executable not found: $PythonExe"
}

function Invoke-Python {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args
    )

    & $PythonExe @Args
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $PythonExe $($Args -join ' ')"
    }
}

Push-Location $ProjectRoot
try {
    Invoke-Python -Args @("-m", "ensurepip", "--upgrade")
    Invoke-Python -Args @("-m", "pip", "install", "--upgrade", "pip")
    Invoke-Python -Args @("-m", "pip", "install", "-r", "requirements.txt", "pyinstaller")

    $PyInstallerArgs = @(
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name", $Name,
        "--windowed",
        "--collect-binaries", "pyaudio",
        "--collect-submodules", "pygame",
        "--hidden-import", "pygame.freetype"
    )

    if ($OneFile) {
        $PyInstallerArgs += "--onefile"
    }

    $PyInstallerArgs += "breathing_recorder.py"

    Invoke-Python -Args $PyInstallerArgs

    $distPath = Join-Path $ProjectRoot "dist"
    Write-Host "Build completed. Artifacts are in: $distPath"
}
finally {
    Pop-Location
}
