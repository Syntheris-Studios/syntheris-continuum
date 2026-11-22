param(
    [string]$PythonExe,
    [switch]$NonInteractive
)
$ErrorActionPreference = 'Stop'
$releaseRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$venvRoot = Join-Path $releaseRoot '.venv'
$venvPython = Join-Path $venvRoot 'Scripts\python.exe'
$exitCode = 1
$originalLocation = Get-Location
# These process-local settings also constrain build subprocesses to the venv.
$environmentNames = @('PYTHONUTF8','PYTHONDONTWRITEBYTECODE','PYTHONPYCACHEPREFIX','PIP_REQUIRE_VIRTUALENV','PIP_DISABLE_PIP_VERSION_CHECK','PIP_CACHE_DIR','TEMP','TMP')
$savedEnvironment = @{}
foreach ($name in $environmentNames) { $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
try {
    Set-Location -LiteralPath $releaseRoot
    $env:PYTHONUTF8 = '1'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:PIP_REQUIRE_VIRTUALENV = 'true'
    $env:PIP_DISABLE_PIP_VERSION_CHECK = '1'
    if (-not $PythonExe) {
        $pyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
        if ($pyLauncher) {
            try {
                $candidate = & $pyLauncher.Source -3.11 -B -c 'import sys; print(sys.executable)' 2>$null
                if ($LASTEXITCODE -eq 0) { $PythonExe = ($candidate | Select-Object -Last 1).Trim() }
            } catch { } # An unregistered 3.11 may still exist at the standard path.
        }
        if (-not $PythonExe -and (Test-Path -LiteralPath 'C:\Python311\python.exe')) { $PythonExe = 'C:\Python311\python.exe' }
        if (-not $PythonExe) {
            $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
            if ($pythonCommand) { $PythonExe = $pythonCommand.Source }
        }
    }
    if (-not $PythonExe -or -not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
        throw 'Python 3.11 was not found. Supply an existing installation: setup.bat -PythonExe "C:\path\to\python.exe". Setup never installs or repairs Python.'
    }
    & $PythonExe -B -c 'import sys; print(sys.version); sys.exit(0 if sys.version_info[:2] == (3,11) and sys.maxsize > 2**32 else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'An existing 64-bit Python 3.11 interpreter is required. No Python installation was changed.' }
    if (-not (Test-Path -LiteralPath $venvPython)) {
        Write-Host '[SETUP] Creating .venv inside the application folder...'
        New-Item -ItemType Directory -Path (Join-Path $venvRoot '.tmp') -Force | Out-Null
        $env:TEMP = Join-Path $venvRoot '.tmp'
        $env:TMP = $env:TEMP
        $env:PYTHONPYCACHEPREFIX = Join-Path $venvRoot '.pycache'
        & $PythonExe -B -m venv $venvRoot
        if ($LASTEXITCODE -ne 0) { throw 'Venv creation failed. The base interpreter was not modified.' }
    }
    # Never fall back to a system pip or accept a different interpreter here.
    & $venvPython -B -c 'import sys,pathlib; assert sys.version_info[:2] == (3,11); assert sys.prefix != sys.base_prefix; assert pathlib.Path(sys.prefix).resolve() == pathlib.Path(sys.argv[1]).resolve()' $venvRoot
    if ($LASTEXITCODE -ne 0) { throw 'The .venv interpreter is invalid. Inspect/remove that local venv and rerun setup.' }
    New-Item -ItemType Directory -Path (Join-Path $venvRoot '.tmp') -Force | Out-Null
    $env:TEMP = Join-Path $venvRoot '.tmp'
    $env:TMP = $env:TEMP
    $env:PYTHONPYCACHEPREFIX = Join-Path $venvRoot '.pycache'
    $env:PIP_CACHE_DIR = Join-Path $venvRoot '.pip-cache'
    Write-Host '[SETUP] Installing requirements using PyPI and the official CUDA 12.8 wheel index...'
    & $venvPython -B -m pip install -r (Join-Path $releaseRoot 'requirements.txt') --extra-index-url https://download.pytorch.org/whl/cu128
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Review the pip error above; do not launch yet.' }
    & $venvPython -B -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Installed dependency consistency check failed.' }
    & $venvPython -B (Join-Path $PSScriptRoot 'verify_environment.py')
    if ($LASTEXITCODE -ne 0) { throw 'Runtime import verification failed.' }
    foreach ($command in @('ffmpeg','ffprobe')) {
        if (-not (Get-Command $command -ErrorAction SilentlyContinue)) { throw "$command is missing from PATH. Install/configure FFmpeg separately, then rerun setup." }
    }
    # Shortcut creation is optional: a desktop policy must not fail setup.
    try {
        $desktop = [Environment]::GetFolderPath('Desktop')
        if (-not $desktop -or -not (Test-Path -LiteralPath $desktop -PathType Container)) { throw 'Desktop folder is unavailable.' }
        $iconPath = Join-Path $releaseRoot 'assets\continuum.ico'
        $launcherPath = Join-Path $releaseRoot 'windows_launcher.bat'
        if (-not (Test-Path -LiteralPath $iconPath -PathType Leaf)) { throw 'Desktop icon is missing.' }
        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut((Join-Path $desktop 'Syntheris Continuum.lnk'))
        $shortcut.TargetPath = $launcherPath
        $shortcut.WorkingDirectory = $releaseRoot
        $shortcut.IconLocation = $iconPath + ',0'
        $shortcut.Description = 'Launch Syntheris Continuum'
        $shortcut.Save()
        Write-Host '[SETUP] Desktop shortcut created: Syntheris Continuum'
    } catch {
        Write-Warning ('Desktop shortcut could not be created: ' + $_.Exception.Message + ' Launch windows_launcher.bat manually.')
    }
    Write-Host '[SUCCESS] Environment ready. Run windows_launcher.bat.'
    $exitCode = 0
} catch {
    Write-Host ('[ERROR] ' + $_.Exception.Message) -ForegroundColor Red
} finally {
    foreach ($name in $environmentNames) { [Environment]::SetEnvironmentVariable($name, $savedEnvironment[$name], 'Process') }
    Set-Location -LiteralPath $originalLocation.Path
}
if (-not $NonInteractive) { Read-Host 'Press Enter to close' | Out-Null }
exit $exitCode
