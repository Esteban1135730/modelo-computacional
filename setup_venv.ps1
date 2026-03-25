# Crea .venv e instala dependencias. Ejecutar desde la raiz del repo:
#   powershell -ExecutionPolicy Bypass -File .\setup_venv.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "No se encontro 'python' en el PATH." -ForegroundColor Red
    Write-Host "1) Instala Python 3.10+ desde https://www.python.org/downloads/"
    Write-Host "2) En el instalador marca: Add python.exe to PATH"
    Write-Host "3) Cierra y abre Cursor, vuelve a ejecutar este script."
    exit 1
}

Write-Host "Python:" (python --version)
if (-not (Test-Path .venv\Scripts\python.exe)) {
    python -m venv .venv
} else {
    Write-Host "Ya existe .venv (se reutiliza)." -ForegroundColor DarkGray
}
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\pip.exe install -r requirements.txt
& .\.venv\Scripts\python.exe -m ipykernel install --user --name=modelo-computacional --display-name="Python (.venv MODELO-COMPUTACIONAL)"
Write-Host ""
Write-Host "Listo. Abre el .ipynb y el kernel deberia ser 'Python (.venv MODELO-COMPUTACIONAL)'." -ForegroundColor Green
Write-Host "Si no: Ctrl+Shift+P -> Python: Select Interpreter ->" (Join-Path $PSScriptRoot ".venv\Scripts\python.exe")
