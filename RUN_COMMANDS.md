# Vidiolingua Run Commands

Run these in **PowerShell**.

## 1. Start The Backend

```powershell
cd D:\Vidiolingua
.\.venv_api\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Leave this PowerShell window open.

## 2. Start The Frontend

Open a **second PowerShell window**.

```powershell
cd D:\Vidiolingua\NEW_Frontend
Set-Content -Path .env.local -Value "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000"
corepack pnpm run dev
```

Leave this PowerShell window open too.

## 3. Open The Website

```text
http://localhost:3000
```
