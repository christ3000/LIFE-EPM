$ErrorActionPreference = "Stop"

$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$envFile = Join-Path $projectRoot ".env"
$backupDirectory = Join-Path $projectRoot "backups"

if (-not (Test-Path $envFile)) {
  throw "Le fichier .env est introuvable."
}

foreach ($line in Get-Content $envFile) {
  if ($line -match '^\s*([^#=\s]+)\s*=(.*)$') {
    Set-Item -Path "Env:$($Matches[1])" -Value $Matches[2].Trim().Trim('"').Trim("'")
  }
}

if (-not $env:DATABASE_URL) {
  if (-not $env:LIFE_EPM_DATABASE_PASSWORD) {
    throw "Définissez DATABASE_URL ou LIFE_EPM_DATABASE_PASSWORD dans .env pour PostgreSQL."
  }
  $env:DATABASE_URL = "postgresql+psycopg://life_epm:$($env:LIFE_EPM_DATABASE_PASSWORD)@localhost:5432/life_epm"
}
if ($env:DATABASE_URL -notmatch '^postgresql(?:\+\w+)?://([^:/?#]+):([^@]*)@([^:/?#]+)(?::(\d+))?/([^?]+)') {
  throw "DATABASE_URL doit contenir l'identifiant, le mot de passe, l'hôte et la base PostgreSQL."
}

$username = [System.Uri]::UnescapeDataString($Matches[1])
$env:PGPASSWORD = [System.Uri]::UnescapeDataString($Matches[2])
$hostName = $Matches[3]
$port = if ($Matches[4]) { $Matches[4] } else { "5432" }
$database = [System.Uri]::UnescapeDataString($Matches[5])

$pgDump = Get-Command pg_dump.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1
if (-not $pgDump) {
  foreach ($version in @("17", "16", "15")) {
    $candidate = "C:\Program Files\PostgreSQL\$version\bin\pg_dump.exe"
    if (Test-Path $candidate) {
      $pgDump = $candidate
      break
    }
  }
}
if (-not $pgDump) {
  throw "pg_dump est introuvable. Installez les outils clients PostgreSQL."
}

New-Item -ItemType Directory -Force -Path $backupDirectory | Out-Null
$destination = Join-Path $backupDirectory ("life-epm-postgres-{0}.dump" -f (Get-Date -Format "yyyyMMdd-HHmmssfff"))
try {
  & $pgDump --no-password --format=custom --host $hostName --port $port --username $username --dbname $database --file $destination
  if ($LASTEXITCODE -ne 0) {
    throw "pg_dump a échoué. Vérifiez que PostgreSQL est démarré et que les identifiants de .env sont corrects."
  }
} catch {
  Remove-Item $destination -Force -ErrorAction SilentlyContinue
  throw
} finally {
  Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}

Write-Output "Sauvegarde créée : $destination"
