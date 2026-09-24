# Bot de Automatización Telegram → Word → PDF

Bot de Telegram que automatiza el portal, descarga el Word generado,
lo convierte a PDF con LibreOffice y lo envía al usuario.

## 🚀 Deploy en Render

1. Sube este repositorio a GitHub (sin el `.env`).
2. En [Render](https://dashboard.render.com/) → **New → Web Service**.
3. Conecta tu repositorio.
4. Configura:
   - **Language:** `Docker`
   - **Instance Type:** `Starter` o superior
   - **Health Check Path:** `/health`
5. **Environment Variables** (pegar una por una):
   - `TELEGRAM_TOKEN`
   - `PORTAL_USER`
   - `PORTAL_PASS`
   - `ALLOWED_USERS` (opcional)
6. Deploy.

## ⏰ Keep-alive con cron-job.org

- URL: `https://tu-app.onrender.com/health`
- Frecuencia: cada 10 minutos

## 📋 Uso en Telegram

```
/start
/generar 12345 ABC123456XYZ
```
