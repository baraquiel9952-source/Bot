import os
import time
import asyncio
import shutil
import subprocess
import threading
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ---------- CONFIGURACIÓN (lee del archivo .env) ----------
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")               # 👈 tu token de BotFather
CORREO_USUARIO = os.getenv("PORTAL_USER")         # 👈 tu correo del portal
PASSWORD_USUARIO = os.getenv("PORTAL_PASS")       # 👈 tu contraseña del portal

USUARIOS_AUTORIZADOS = {
    int(x) for x in os.getenv("ALLOWED_USERS", "").split(",") if x.strip().isdigit()
}

URL_LOGIN = "https://validate-mx.byethost6.com/login/"

BASE_DIR = Path("/app")
TEMP_DIR = BASE_DIR / "temp"
DESCARGAS_DIR = BASE_DIR / "descargas"
TEMP_DIR.mkdir(parents=True, exist_ok=True)
DESCARGAS_DIR.mkdir(parents=True, exist_ok=True)

PROCESO_LOCK = threading.Lock()


# ---------- HELPERS ----------
def _autorizado(update: Update) -> bool:
    if not USUARIOS_AUTORIZADOS:
        return True
    return update.effective_chat.id in USUARIOS_AUTORIZADOS


def _crear_driver():
    options = Options()
    options.binary_location = os.getenv("CHROME_BIN", "/usr/bin/chromium")
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1366,900")
    options.add_argument("--ignore-certificate-errors")

    prefs = {
        "download.default_directory": str(DESCARGAS_DIR),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    options.add_experimental_option("prefs", prefs)

    service = Service(os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver"))
    return webdriver.Chrome(service=service, options=options)


def _esperar_descarga(carpeta: Path, timeout: int = 90) -> Path | None:
    fin = time.time() + timeout
    while time.time() < fin:
        archivos = list(carpeta.glob("*.docx")) + list(carpeta.glob("*.doc"))
        archivos = [a for a in archivos if not a.name.endswith(".crdownload")]
        if archivos:
            tam1 = archivos[0].stat().st_size
            time.sleep(1)
            tam2 = archivos[0].stat().st_size
            if tam1 == tam2 and tam1 > 0:
                return archivos[0]
        time.sleep(1)
    return None


def _word_a_pdf(ruta_docx: Path, carpeta_salida: Path) -> Path | None:
    comando = [
        "libreoffice", "--headless", "--invisible", "--norestore",
        "--convert-to", "pdf:writer_pdf_Export",
        str(ruta_docx),
        "--outdir", str(carpeta_salida),
    ]
    try:
        subprocess.run(comando, check=True, capture_output=True, timeout=180)
        pdf = carpeta_salida / (ruta_docx.stem + ".pdf")
        return pdf if pdf.exists() else None
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"Error al convertir: {e}")
        return None


def _limpiar_carpeta(carpeta: Path):
    for item in carpeta.iterdir():
        try:
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        except Exception as e:
            print(f"No se pudo borrar {item}: {e}")


# ---------- AUTOMATIZACIÓN ----------
def _automatizacion_sync(idcif_val: str, rfc_val: str) -> Path:
    with PROCESO_LOCK:
        _limpiar_carpeta(DESCARGAS_DIR)
        _limpiar_carpeta(TEMP_DIR)

        driver = _crear_driver()
        try:
            # PASO 1: Login
            driver.get(URL_LOGIN)
            wait = WebDriverWait(driver, 30)

            input_email = wait.until(EC.presence_of_element_located((By.ID, "email-1")))
            input_pass = driver.find_element(By.ID, "userpassword-1")

            input_email.clear()
            input_email.send_keys(CORREO_USUARIO)
            input_pass.clear()
            input_pass.send_keys(PASSWORD_USUARIO)

            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            wait.until(EC.url_changes(URL_LOGIN))

            # PASO 2: Menú hamburguesa
            menu = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button.btn.btn-outline-light, button.fa-bars, .fa-bars")
            ))
            menu.click()

            # PASO 3: Opción RFC
            wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(@href,'rfc.php')]")
            )).click()

            # PASO 4: Rellenar campos
            wait.until(EC.presence_of_element_located((By.NAME, "idcif"))).send_keys(idcif_val)
            driver.find_element(By.NAME, "rfc").send_keys(rfc_val)

            # PASO 5: Botón GENERAR
            driver.find_element(
                By.CSS_SELECTOR,
                "input[type='submit'].btn-success, button[type='submit'].btn-success",
            ).click()

            # Esperar descarga del Word
            archivo_word = _esperar_descarga(DESCARGAS_DIR, timeout=90)
            if not archivo_word:
                raise RuntimeError("No se detectó la descarga del Word.")

            # Convertir a PDF
            ruta_pdf = _word_a_pdf(archivo_word, TEMP_DIR)
            if not ruta_pdf:
                raise RuntimeError("La conversión del Word a PDF falló.")

            return ruta_pdf

        finally:
            driver.quit()


# ---------- HANDLERS DE TELEGRAM ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _autorizado(update):
        await update.message.reply_text("⛔ No estás autorizado.")
        return
    await update.message.reply_text(
        "🤖 *Bot de automatización activo*\n\n"
        "Uso:\n`/generar [IDCIF] [RFC]`\n\n"
        "Ejemplo:\n`/generar 12345 ABC123456XYZ`",
        parse_mode="Markdown",
    )


async def generar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _autorizado(update):
        await update.message.reply_text("⛔ No estás autorizado.")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ Faltan datos.\nUsa: `/generar [IDCIF] [RFC]`",
            parse_mode="Markdown",
        )
        return

    idcif_val, rfc_val = context.args[0], context.args[1]
    msg = await update.message.reply_text("🔄 Procesando… esto puede tardar un minuto.")

    try:
        ruta_pdf = await asyncio.to_thread(_automatizacion_sync, idcif_val, rfc_val)

        with open(ruta_pdf, "rb") as f:
            await update.message.reply_document(
                document=InputFile(f, filename=f"RFC_{idcif_val}_{rfc_val}.pdf"),
                caption=f"✅ Documento generado\nIDCIF: `{idcif_val}`\nRFC: `{rfc_val}`",
                parse_mode="Markdown",
            )
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ Error en el proceso:\n`{e}`", parse_mode="Markdown")

    finally:
        _limpiar_carpeta(DESCARGAS_DIR)
        _limpiar_carpeta(TEMP_DIR)


# ---------- FLASK (keep-alive) ----------
flask_app = Flask(__name__)


@flask_app.route("/")
def index():
    return jsonify({"status": "ok", "service": "bot-telegram-rfc"})


@flask_app.route("/health")
def health():
    return jsonify({"status": "healthy", "timestamp": time.time()}), 200


def _run_flask():
    port = int(os.getenv("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


# ---------- MAIN ----------
def main():
    if not TOKEN:
        raise SystemExit("Falta TELEGRAM_TOKEN en las variables de entorno.")

    threading.Thread(target=_run_flask, daemon=True).start()
    print(f"🌐 Flask escuchando en el puerto {os.getenv('PORT', 10000)}")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("generar", generar))

    print("🤖 Bot iniciado. Esperando comandos…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
