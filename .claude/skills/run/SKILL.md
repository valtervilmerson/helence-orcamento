---
description: Sobe os servidores locais de desenvolvimento (backend FastAPI + frontend Vite)
---

# Como subir o servidor local

Este projeto tem dois processos: backend FastAPI (porta 8000) e frontend Vite (porta 5173).

## Backend

**Executável**: `backend\.venv\Scripts\python.exe` (venv do projeto — o Python do sistema não tem as dependências)  
**Diretório de trabalho**: `backend\`  
**Comando**:

```powershell
Start-Process -FilePath "backend\.venv\Scripts\python.exe" `
  -ArgumentList "-m","uvicorn","app.main:app","--reload","--port","8000" `
  -RedirectStandardOutput "$env:TEMP\backend_out.txt" `
  -RedirectStandardError  "$env:TEMP\backend_err.txt" `
  -WindowStyle Hidden `
  -WorkingDirectory (Resolve-Path "backend").Path
```

**Health-check** (aguarde ~5s): `GET http://localhost:8000/api/v1/health` → `{"status":"ok"}`

Erros de startup ficam em `$env:TEMP\backend_err.txt`.

## Frontend

**Executável**: `C:\Program Files\nodejs\npm.cmd` (`npm` sem extensão não é executável Win32 válido no PowerShell)  
**Diretório de trabalho**: `frontend\`  
**Comando**:

```powershell
Start-Process -FilePath "C:\Program Files\nodejs\npm.cmd" `
  -ArgumentList "run","dev" `
  -RedirectStandardOutput "$env:TEMP\frontend_out.txt" `
  -RedirectStandardError  "$env:TEMP\frontend_err.txt" `
  -WindowStyle Hidden `
  -WorkingDirectory (Resolve-Path "frontend").Path
```

**Verificação** (aguarde ~7s): `GET http://localhost:5173` → 200 com HTML

## Sequência completa

```powershell
cd C:\projects\codex\helence\helence-orcamento

# 1. backend
Start-Process -FilePath "backend\.venv\Scripts\python.exe" `
  -ArgumentList "-m","uvicorn","app.main:app","--reload","--port","8000" `
  -RedirectStandardOutput "$env:TEMP\backend_out.txt" `
  -RedirectStandardError  "$env:TEMP\backend_err.txt" `
  -WindowStyle Hidden `
  -WorkingDirectory (Resolve-Path "backend").Path

# 2. frontend
Start-Process -FilePath "C:\Program Files\nodejs\npm.cmd" `
  -ArgumentList "run","dev" `
  -RedirectStandardOutput "$env:TEMP\frontend_out.txt" `
  -RedirectStandardError  "$env:TEMP\frontend_err.txt" `
  -WindowStyle Hidden `
  -WorkingDirectory (Resolve-Path "frontend").Path

# 3. aguarda e verifica
Start-Sleep -Seconds 7
Invoke-WebRequest http://localhost:8000/api/v1/health -UseBasicParsing
Invoke-WebRequest http://localhost:5173 -UseBasicParsing | Select-Object StatusCode
```

## Verificar se já estão rodando

```powershell
try { (Invoke-WebRequest http://localhost:8000/api/v1/health -UseBasicParsing -TimeoutSec 2).Content } catch { "backend offline" }
try { (Invoke-WebRequest http://localhost:5173 -UseBasicParsing -TimeoutSec 2).StatusCode } catch { "frontend offline" }
```

## Notas

- O backend usa `--reload` (hot-reload automático ao salvar arquivos Python).
- O frontend usa Vite com HMR.
- Ambos rodam em background (janelas ocultas). Output em `$env:TEMP\backend_*.txt` e `$env:TEMP\frontend_*.txt`.
- Não é necessário ativar o venv manualmente — basta chamar o executável Python direto de `.venv\Scripts\`.
