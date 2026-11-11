$ErrorActionPreference = "Stop"

$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$backendDirectory = Join-Path $projectRoot "backend"
$virtualEnvironment = Join-Path $backendDirectory ".venv"
$python = Join-Path $virtualEnvironment "Scripts\python.exe"
$envFile = Join-Path $projectRoot ".env"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw "Python est introuvable. Installez Python 3.12 ou plus récent puis relancez ce script."
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  throw "Node.js est introuvable. Installez Node.js puis relancez ce script."
}
if (-not (Test-Path $envFile)) {
  Copy-Item (Join-Path $projectRoot ".env.example") $envFile
  throw "Le fichier .env a été créé. Remplacez ses valeurs de démonstration puis relancez ce script."
}

foreach ($line in Get-Content $envFile) {
  if ($line -match '^\s*([^#=\s]+)\s*=(.*)$') {
    $name = $Matches[1]
    $value = $Matches[2].Trim()
    if ($value.Length -ge 2 -and $value.StartsWith('"') -and $value.EndsWith('"')) {
      $value = $value.Substring(1, $value.Length - 2)
    } elseif ($value.Length -ge 2 -and $value.StartsWith("'") -and $value.EndsWith("'")) {
      $value = $value.Substring(1, $value.Length - 2)
    }
    Set-Item -Path "Env:$name" -Value $value
  }
}

if (-not $env:DATABASE_URL) {
  if (-not $env:LIFE_EPM_DATABASE_PASSWORD) {
    throw "Définissez DATABASE_URL ou LIFE_EPM_DATABASE_PASSWORD dans .env pour PostgreSQL."
  }
  $env:DATABASE_URL = "postgresql+psycopg://life_epm:$($env:LIFE_EPM_DATABASE_PASSWORD)@localhost:5432/life_epm"
}
if (-not $env:DATABASE_URL.StartsWith("postgresql")) {
  throw "DATABASE_URL doit pointer vers PostgreSQL."
}
if (-not $env:LIFE_EPM_JWT_SECRET -or -not $env:LIFE_EPM_ADMIN_PASSWORD) {
  throw "Définissez LIFE_EPM_JWT_SECRET et LIFE_EPM_ADMIN_PASSWORD dans .env."
}

if (-not (Test-Path $python)) {
  & python -m venv $virtualEnvironment
  if ($LASTEXITCODE -ne 0) {
    throw "La création de l'environnement Python a échoué."
  }
}

& $python -m pip install -r (Join-Path $backendDirectory "requirements.txt")
if ($LASTEXITCODE -ne 0) {
  throw "L'installation des dépendances Python a échoué."
}

$npm = Join-Path (Split-Path (Get-Command node).Source) "npm.cmd"
if (-not (Test-Path (Join-Path $projectRoot "node_modules\next"))) {
  & $npm ci --prefix $projectRoot
  if ($LASTEXITCODE -ne 0) {
    throw "L'installation des dépendances web a échoué."
  }
}

Push-Location $backendDirectory
try {
  & $python -m alembic upgrade head
  if ($LASTEXITCODE -ne 0) {
    throw "La migration PostgreSQL a échoué. Vérifiez le service, la base et les identifiants locaux."
  }
}
finally {
  Pop-Location
}

Start-Process -FilePath $python -ArgumentList @(
  "-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1"
) -WorkingDirectory $backendDirectory

Start-Process -FilePath $npm -ArgumentList @("run", "dev") -WorkingDirectory $projectRoot

Write-Output "API et interface démarrées. Ouvrez http://localhost:3000."
