param(
  [string]$BackupDirectory = (Join-Path $PSScriptRoot "..\backups")
)

$backupRoot = [System.IO.Path]::GetFullPath($BackupDirectory)
New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null

$fileName = "life-epm-postgres-$(Get-Date -Format 'yyyyMMdd-HHmmssfff').dump"
$containerPath = "/tmp/$fileName"
$destination = Join-Path $backupRoot $fileName

try {
  docker compose exec -T db pg_dump -U life_epm -d life_epm -Fc -f $containerPath
  if ($LASTEXITCODE -ne 0) {
    throw "pg_dump a échoué. Vérifiez que le service db est démarré et consultez ses journaux."
  }

  docker compose cp "db:$containerPath" $destination
  if ($LASTEXITCODE -ne 0) {
    throw "La copie de la sauvegarde vers $destination a échoué."
  }

  Write-Output "Sauvegarde créée : $destination"
}
finally {
  docker compose exec -T db rm -f -- $containerPath
  if ($LASTEXITCODE -ne 0) {
    Write-Warning "Le fichier temporaire n'a pas pu être supprimé du conteneur PostgreSQL."
  }
}
