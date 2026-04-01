# B.E.A.M Website

Run locally:
```powershell
py -m pip install -r requirements.txt
py app.py
```

Open:
http://127.0.0.1:5000

Public from your PC:
```powershell
py -m waitress --listen=127.0.0.1:5000 app:app
cloudflared tunnel --url http://localhost:5000
```
