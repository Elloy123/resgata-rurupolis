# Prepara o ambiente e inicia o site Resgata Rurópolis em http://127.0.0.1:8000
# Uso (no PowerShell, na pasta do projeto):  .\rodar.ps1
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (-not (Test-Path 'venv\Scripts\python.exe')) {
    Write-Host 'Criando ambiente virtual...'
    py -m venv venv
}
$python = '.\venv\Scripts\python.exe'

Write-Host 'Instalando dependências...'
& $python -m pip install --quiet -r requirements.txt

if (-not (Test-Path '.env')) {
    Write-Host 'Criando .env a partir do .env.example (com SECRET_KEY nova)...'
    $chave = & $python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
    (Get-Content '.env.example' -Encoding utf8) -replace '^SECRET_KEY=.*', "SECRET_KEY=$chave" |
        Set-Content '.env' -Encoding utf8
}

Write-Host 'Aplicando migrações...'
& $python manage.py migrate

Write-Host ''
Write-Host 'Site:  http://127.0.0.1:8000'
Write-Host 'Admin: http://127.0.0.1:8000/admin/'
& $python manage.py runserver
