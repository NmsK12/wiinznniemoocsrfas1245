import os
import re
import json, requests, base64, collections
from io import BytesIO
import math
import asyncio
import logging
from typing import Any, Dict, List
import aiohttp
from urllib.parse import quote_plus
from decimal import Decimal, InvalidOperation
from html import escape
from PIL import Image, ImageFilter, ImageDraw, ImageFont
from anuncio import anuncio, auto_register_group, auto_register_group_on_message
from datetime import datetime, timedelta, time
from telegram.constants import ParseMode
from utilidades import formatea_titulares
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, ChatMemberHandler, MessageHandler, filters
from database import user_db, ADMIN_USER_ID, DEFAULT_CREDITS, DEFAULT_ROLE, DEFAULT_PLAN

# Logging
logging.basicConfig( format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

EMOJIS = {
    "welcome": "✨",
    "mundo": "🌐",
    "Identidad": "🧑‍💻",
    "Telefonía": "📞",
    "Seguridad": "🚨",
    "Policía": "👮",
    "Impuestos": "🏢",
    "Registros": "🗂️",
    "Transporte": "🚗",
    "Herramienta": "⚙️",
    "Documentos": "📑",
    "Familia": "👨‍👩‍👦",
    "Dinero": "💰",
    "Fraude": "💀",
    "Búsqueda": "🔎",
    "Comprobante": "📄",
    "Adicionales": "➕",
    "Promoción": "🎁",
    "Tiempo": "⏳",
    "Premium": "💎",
    "Global": "🌍",
    "Créditos": "♻️",
    "Actas": "📜",
    "menu": "📖",
    "propiedades": "🚘",
    "credit": "💳",
    "plan": "🎫",
    "date": "📅",
    "phone": "📱",
    "dni": "🆔",
    "operator": "📡",
    "plan_type": "📋",
    "email": "✉️",
    "owner": "👤",
    "search": "🔍",
    "ok": "✅",
    "warn": "⚠️",
    "error": "❌",
    "back": "⬅️",
    "next": "➡️",
    "home": "🏠",
    "profile": "👤",
    "phone": "📱",
    "owner": "👑",
    "plan": "📦",
    "libro": "📓",
    "date": "📅"
}

def bold(text):
    return f"<b>{text}</b>"

def italic(text):
    return f"<i>{text}</i>"

# --------- SISTEMA DE USUARIOS Y CRÉDITOS ---------
async def registro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or ""
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    full_name = f"{first_name} {last_name}".strip()

    # 🔹 Verificar si ya está registrado
    if user_db.get_user(user_id):
        mensaje = (
            f"{EMOJIS['warn']} {bold('Ya estás registrado,')} {italic(full_name)}.\n"
            f"Puedes usar todos los comandos del bot.\n"
            f"Utiliza {bold('/me')} para ver tu perfil."
        )
    else:
        # 🔹 Registrar usuario
        user_db.register_user(user_id, username, first_name, last_name)

        # 🔹 Determinar créditos para el mensaje
        user_data = user_db.get_user(user_id)
        credits = user_data.get("credits", 0)
        credits_display = "♾️" if credits == "inf" else str(credits)

        mensaje = (
            f"{EMOJIS['ok']} {bold('Registro exitoso,')} {italic(full_name)}!\n\n"
            f"Ahora puedes usar todos los comandos disponibles del bot.\n"
            f"Has recibido {bold(credits_display)} créditos.\n"
            f"Utiliza {bold('/cmds')} para ver la lista de comandos."
        )

    # 🔹 Enviar mensaje de registro
    await update.message.reply_text(
        mensaje, parse_mode="HTML", reply_to_message_id=update.message.message_id
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Muestra los planes y tarifas con una imagen + botón de contacto.
    """
    mensaje = (
        "✨<b>PLANES Y TARIFAS</b> ✨\n"
        "⚡️ By: @tronchitobot\n\n"

        "💰<b>PLAN POR CREDITOS</b> 💰\n\n"

        "⟦🔰⟧<b>BÁSICO (45's)</b>\n"
        "* 50 + 20 Créditos ➩ 5 Soles\n"
        "* 200 + 50 Créditos ➩ 10 Soles\n"
        "* 350 + 80 Créditos ➩ 15 Soles\n\n"

        "⟦⭐⟧<b>STANDARD (15's)</b>\n"
        "* 500 + 100 Créditos ➩ 40 Soles\n"
        "* 800 + 150 Créditos ➩ 50 Soles\n"
        "* 1000 + 200 Créditos ➩ 60 Soles\n\n"

        "⟦💎⟧<b>PREMIUM (5's)</b>\n"
        "* 1500 + 300 Créditos ➩ 70 Soles\n"
        "* 2000 + 400 Créditos ➩ 90 Soles\n"
        "* 3000 + 600 Créditos ➩ 140 Soles\n\n"

        "⏳<b>PLAN POR DÍAS</b> ⏳\n\n"

        "⟦🔰⟧<b>BÁSICO - NV1 (25's)</b>\n"
        "* Vip 3 Días ➩ 10 Soles\n"
        "* Vip 7 Días ➩ 15 Soles\n\n"

        "⟦⭐⟧<b>STANDARD - NV2 (15's)</b>\n"
        "* Vip 15 Días ➩ 20 Soles\n"
        "* Vip 25 Días ➩ 35 Soles\n\n"

        "⟦💎⟧<b>PREMIUM - NV3 (5's)</b>\n"
        "* Vip 30 Días ➩ 35 Soles\n"
        "* Vip 60 Días ➩ 60 Soles\n"
        "* Vip 90 Días ➩ 90 Soles\n\n"

        "[⚠️]<b>IMPORTANTE</b> ➩ Antes de comprar leer los términos y condiciones usa /terminos"
    )

    # 🔹 Botón inline
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 彡[ᴡɪɴɴɪᴇ ᴘᴏᴏʜ]彡", url="https://t.me/WinniePoohOFC")]
    ])

    # 🔹 Enviar imagen con texto y botón
    await update.message.reply_photo(
        photo="TRONCHITOBOT.png",  # 📸 imagen o ruta
        caption=mensaje,
        parse_mode="HTML",
        reply_markup=keyboard,
        reply_to_message_id=update.message.message_id
    )

async def terminos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Envía los términos y condiciones del bot.
    """
    mensaje = (
        "<b>[#TRONCHITOBOT] ➾ TERMINOS Y CONDICIONES</b>\n\n"

        "[💰]<b>REEMBOLSOS</b>\n"
        "Acá no hay devoluciones, aguanta que te caen tus créditos. No jodas. "
        "Si un seller te vendió créditos o planes, reclámale a él. No jodas al owner.\n\n"

        "[🛠]<b>GARANTÍA</b>\n"
        "¿El bot se cayó? ¿Un comando no jala? No llores, espera nomás. "
        "Nadie te prometió perfección. No molestes al soporte por huevadas.\n\n"

        "[🚫]<b>PROHIBIDO EL PUENTE</b>\n"
        "Oe chibol@ rata, si te encontramos haciendo puente (revendiendo, compartiendo acceso, "
        "o jalando info a otros bots), te vas baneado, quemado y funado. Así nomás. ¡Ni llorando vuelves!\n\n"

        "[👀]<b>USO INDEBIDO</b>\n"
        "No uses el bot para huevadas legales. Si te meten preso, no nos llames. "
        "Tú solit@ te metiste al agua.\n\n"

        "[📵]<b>SPAM Y ABUSO</b>\n"
        "Te pasas de vivo usando comandos como loco, te metemos cooldown o ban. "
        "Este bot no es tu juquete.\n\n"

        "[⚠️]<b>NO YAPE</b>\n"
        "¿Solo estás preguntando por preguntar? Chao. NO PIDAS YAPE SI NO VAS A COMPRAR.\n\n"

        "[📌]<b>NOTA FINAL</b>\n"
        "Nos reservamos el derecho de cambiar estos términos, condiciones o lo que sea, "
        "cuando se nos da la puta gana. Sin aviso, sin lloros.\n\n"

        "[⚠️]<b>IMPORTANTE</b> ➩ Una vez leído los términos y condiciones, utiliza /buy para comprar."
    )

    # 🔹 Enviar mensaje respondiendo al usuario
    await update.message.reply_text(
        mensaje, parse_mode="HTML", reply_to_message_id=update.message.message_id
    )
async def inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    # --------------------------
    # 1️⃣ Registro automático de grupos
    # --------------------------
    if chat.type in ["group", "supergroup"]:
        if not user_db.get_group(chat.id):  # Solo registra si no existe
            saved = user_db.set_group_subscription(chat.id, "Free")
            if saved:
                await update.message.reply_text(
                    f"📌 Grupo registrado automáticamente: {chat.title}"
                )
            else:
                await update.message.reply_text(
                    f"⚠️ No se pudo registrar el grupo: {chat.title}"
                )
        # Si ya existe, no se envía ningún mensaje

    # --------------------------
    # 2️⃣ Definir nombre para mensaje
    # --------------------------
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    full_name = f"{first_name} {last_name}".strip() or "Usuario"

    # --------------------------
    # 3️⃣ Mensaje de bienvenida con foto
    # --------------------------
    mensaje = (
        f"👋 ¡Hola, <b>{full_name}</b>!\n"
        f"✨ <b>¡Bienvenido a TRONCHITOBOT!</b> Tu plataforma confiable para consultas inteligentes.\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆓 Usa el comando <b>/register</b> para ganar <b>créditos gratis</b> y empezar a buscar lo que quieras.\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🛠️ <i>Desarrollado por:</i> <b>@WinniePoohOFC</b>"
    )

    await update.message.reply_photo( photo="inicio.jpeg", caption=mensaje, parse_mode="HTML", reply_to_message_id=update.message.message_id
    )

async def information(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from datetime import datetime

    user = update.effective_user
    user_id = str(user.id)

    data = user_db.get_user(user_id)
    if not data:
        mensaje = (
            f"{EMOJIS['warn']} {bold('No estás registrado.')}\n"
            f"Regístrate primero con {bold('/register')} para acceder a tu perfil."
        )
        await update.message.reply_text(mensaje, parse_mode="HTML", reply_to_message_id=update.message.message_id)
        return

    # 🔹 Información básica
    nombre = (data.get("first_name", "") + " " + (data.get("last_name") or "")).strip()
    estado = "ACTIVO"  # O tu campo de estado
    rol = data.get("role", "").upper()
    plan = data.get("plan", "Free").upper()
    credits = data.get("credits", 0)
    try:
        # Muestra como entero si es convertible, sino muestra el texto (por ejemplo ♾️)
        credits_display = "♾️" if str(credits) in ["inf", "Infinity", "∞", "♾️"] else str(int(float(credits)))
    except Exception:
        credits_display = credits

    # 🔹 Fechas
    registrado_at = datetime.strptime(data.get("registered_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")), "%Y-%m-%d %H:%M:%S")
    inicio_str = data.get("start_date", registrado_at.strftime("%d/%m/%Y - %I:%M:%S %p"))
    expiracion_str = data.get("expiration_date", "Sin fecha")  # Ajusta según tu DB

    # 🔹 Tiempo transcurrido
    if expiracion_str != "Sin fecha":
        try:
            expiracion_dt = datetime.strptime(expiracion_str, "%Y-%m-%d %H:%M:%S")
            delta = expiracion_dt - registrado_at
            dias = delta.days
            horas, resto = divmod(delta.seconds, 3600)
            minutos, _ = divmod(resto, 60)
            tiempo_transcurrido = f"{dias} días, {horas} horas {minutos} minutos"
        except:
            tiempo_transcurrido = "N/A"
    else:
        tiempo_transcurrido = "N/A"

    # 🔹 Consultas y anti-spam
    consultas_totales = data.get("consultas_totales", 0)
    consultas_hoy = data.get("consultas_hoy", 0)
    anti_spam = data.get("anti_spam", 0)

    # 🔹 Construir mensaje
    mensaje = (
        f"[#TRONCHITOBOT]  ➾ ME - PERFIL\n\n"
        f"PERFIL DE ➾ {nombre}\n\n"
        f"INFORMACIÓN PERSONAL\n\n"
        f"[🙎‍♂️] ID ➾ {user_id}\n"
        f"[👨🏻‍💻] USER ➾ @{data.get('username', 'Sin usuario')}\n"
        f"[👺] ESTADO ➾ {estado}\n"
        f"[📅] F. REGISTRO ➾ {registrado_at.strftime('%d/%m/%Y - %I:%M:%S %p')}\n\n"
        f"ESTADO DE CUENTA\n\n"
        f"[〽️] ROL ➾ {rol}\n"
        f"[📈] PLAN ➾ {plan}\n"
        f"[⏱] ANTI-SPAM ➾ {anti_spam}'\n"
        f"[💰] CREDITOS ➾ {credits_display}\n"
        f"[⏳] TIEMPO ➾ {tiempo_transcurrido}\n"
        f"[📅] F. INICIO ➾ {inicio_str}\n"
        f"[📅] F. EXPIRACION ➾ {expiracion_str}\n\n"
        f"USO DEL SERVICIO\n\n"
        f"[📊] CONSULTAS ➾ {consultas_totales}\n"
        f"[📅] CONSULTAS DE HOY ➾ {consultas_hoy}"
    )

    # 🔹 Intentar usar foto de perfil real de Telegram
    photos = await context.bot.get_user_profile_photos(user.id, limit=1)
    if photos.total_count > 0:
        file_id = photos.photos[0][-1].file_id  # La mejor resolución
        await update.message.reply_photo( photo=file_id, caption=mensaje, parse_mode="HTML", reply_to_message_id=update.message.message_id
        )
    else:
        # Caer a imagen por defecto
        await update.message.reply_photo( photo="perfil.png", caption=mensaje, parse_mode="HTML", reply_to_message_id=update.message.message_id
        )

async def cmds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    nombre_completo = user.first_name
    if user.last_name:
        nombre_completo += f" {user.last_name}"

    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['Telefonía']} TELEFONIA", callback_data='telefonia'),
            InlineKeyboardButton(f"{EMOJIS['Identidad']} RENIEC", callback_data='reniec')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['home']} SUNARP", callback_data='sunarp'),
            InlineKeyboardButton(f"{EMOJIS['Global']} MUNDIAL", callback_data='mundial')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['Premium']} VIP", callback_data='vip'),
            InlineKeyboardButton(f"{EMOJIS['Policía']} POLICIA", callback_data='policia')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['Seguridad']} DELITOS", callback_data='delitos'),
            InlineKeyboardButton(f"{EMOJIS['Búsqueda']} SEEKER", callback_data='seeker')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['Impuestos']} SUNAT", callback_data='sunat'),
            InlineKeyboardButton(f"{EMOJIS['Comprobante']} CERTIFICADOS", callback_data='certificados')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['Promoción']} GRATIS", callback_data='gratis'),
            InlineKeyboardButton(f"{EMOJIS['Herramienta']} GENERADOR", callback_data='generador')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['credit']} BAUCHER", callback_data='baucher'),
            InlineKeyboardButton(f"{EMOJIS['Adicionales']} EXTRAS", callback_data='extras')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['Familia']} FAMILIARES", callback_data='familiares'),
            InlineKeyboardButton(f"{EMOJIS['Actas']} ACTAS", callback_data='actas')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['Transporte']} VEHICULOS", callback_data='vehiculos'),
            InlineKeyboardButton(f"{EMOJIS['Créditos']} INFO BURO", callback_data='infoburo') 
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mensaje = (
        f"{bold('[#TRONCHITOBOT] ➾ SISTEMA DE COMANDOS')}\n\n"
        f"{EMOJIS['menu']} {bold('➣ Hola,')} {italic(nombre_completo)}\n\n"
        f"{bold('Recuerda que para saber los precios debes usar el comando /buy')}\n\n"
        f"{EMOJIS['welcome']} {bold('Bienvenido al menú principal de comandos')}\n\n"
        f"Selecciona una opción según la categoría que deseas explorar:"
    )
    await update.message.reply_photo( photo="TRONCHITOBOT.png", caption=mensaje, reply_markup=reply_markup, parse_mode="HTML", reply_to_message_id=update.message.message_id
    )

# ==== PLANES DE CRÉDITOS ====
PLANES_CREDITOS = [
    {"nombre": "BASICO", "precio": {
        70: 5,    # 50 + 20
        250: 10,  # 200 + 50
        430: 15   # 350 + 80
    }},
    {"nombre": "STANDARD", "precio": {
        600: 40,   # 500 + 100
        950: 50,   # 800 + 150
        1200: 60   # 1000 + 200
    }},
    {"nombre": "PREMIUM", "precio": {
        1800: 70,   # 1500 + 300
        2400: 90,   # 2000 + 400
        3600: 140   # 3000 + 600
    }},
]

# Lista de todos los créditos válidos (para referencia)
VALID_CREDITS = sorted({c for p in PLANES_CREDITOS for c in p["precio"].keys()})

# ==== FUNCION PARA OBTENER PLAN SEGUN CANTIDAD ====
def get_plan_for_credits(cantidad: int):
    """
    Devuelve (plan_info, pack_credits, precio).
    - Si cantidad exacta existe → lo usa.
    - Si no existe → busca el pack más cercano (hacia arriba o abajo).
    - Si cantidad > todos los packs → usa el máximo disponible.
    """
    # Caso exacto
    for p in PLANES_CREDITOS:
        if cantidad in p["precio"]:
            return p, cantidad, p["precio"][cantidad]

    # Buscar el pack más cercano
    closest = None
    min_diff = float('inf')
    for p in PLANES_CREDITOS:
        for c, precio in p["precio"].items():
            diff = abs(cantidad - c)
            if diff < min_diff:
                min_diff = diff
                closest = (p, c, precio)
            # En caso de empate, prioriza el pack mayor
            elif diff == min_diff and c > closest[1]:
                closest = (p, c, precio)

    return closest
# ==== COMANDO /cred ====
async def cred(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    data = user_db.get_user(user_id)

    if not data or data.get("role") != "admin":
        await update.message.reply_text("❌ No tienes permisos para usar este comando.")
        return

    # ===== Determinar user_id del destinatario =====
    if update.message.reply_to_message:
        # Si se responde a un mensaje, usar el user_id de ese usuario
        to_user = update.message.reply_to_message.from_user
        to_user_id = str(to_user.id)
        if len(context.args) != 1:
            await update.message.reply_text(
                "❗ Uso correcto respondiendo al mensaje del usuario:\n"
                "/cred <creditos>\n"
                f"✔️ Packs válidos: {', '.join(map(str, VALID_CREDITS))}"
            )
            return
        arg_index = 0  # El argumento que contiene la cantidad
    else:
        # Si no es respuesta, esperar que pase el user_id como primer argumento
        if len(context.args) != 2:
            await update.message.reply_text(
                "❗ Uso correcto:\n/cred <user_id_10_digitos><creditos>\n"
                f"✔️ Packs válidos: {', '.join(map(str, VALID_CREDITS))}"
            )
            return
        to_user_id = context.args[0]
        if not re.fullmatch(r"\d{10}", to_user_id):
            await update.message.reply_text("El ID debe tener exactamente 10 dígitos.")
            return
        arg_index = 1  # El argumento que contiene la cantidad

    # ===== Validar cantidad =====
    try:
        cantidad = int(context.args[arg_index])
        if cantidad < 1:
            raise ValueError
    except:
        await update.message.reply_text("La cantidad debe ser un número mayor a 0.")
        return

    # Mensaje inmediato de procesamiento
    processing_msg = await update.message.reply_text("⏳ Procesando la asignación de créditos...")

    # ===== Obtener plan y pack más cercano =====
    plan_info, pack_credits, precio = get_plan_for_credits(cantidad)
    if not plan_info:
        await processing_msg.edit_text("❌ No se encontró un plan válido.")
        return

    # ===== Actualizar créditos =====
    if user_db.update_credits(
        to_user_id,
        pack_credits, tipo="admin_add", motivo=f"Créditos añadidos por admin {user.first_name}"
    ):
        target_data = user_db.get_user(to_user_id)
        creditos = int(target_data.get("credits", 0))

        mensaje = (
            f"[#TRONCHITOBOT] ➾ AÑADIÓ CRÉDITOS\n"
            f"ADMIN      : {user.first_name} ({user_id})\n"
            f"USUARIO    : {to_user_id}\n"
            f"PLAN       : {plan_info['nombre']}\n"
            f"SOLICITADO : {cantidad}\n"
            f"ASIGNADO   : {pack_credits} CRÉDITOS\n"
            f"PRECIO     : {precio:.2f} SOLES\n"
            f"💳 Créditos actuales: {creditos}"
        )

        await processing_msg.edit_text(mensaje)
    else:
        await processing_msg.edit_text("❌ Usuario no encontrado.")
        
async def uncred(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    data = user_db.get_user(user_id)
    if not data or data.get("role") != "admin":
        await update.message.reply_text(
            "❌ No tienes permisos para usar este comando.", parse_mode="HTML", reply_to_message_id=update.message.message_id
        )
        return

    if len(context.args) != 2:
        await update.message.reply_text(
            "❗ <b>Uso correcto:</b>\n"
            "/uncred <code>user_id_10_digitos</code><code>cantidad</code>\n"
            "Ejemplo: <code>/uncred 1234567890 50</code>", parse_mode="HTML", reply_to_message_id=update.message.message_id
        )
        return

    to_user_id = context.args[0]
    if not re.fullmatch(r"\d{10}", to_user_id):
        await update.message.reply_text(
            "El ID debe tener exactamente 10 dígitos.", parse_mode="HTML", reply_to_message_id=update.message.message_id
        )
        return

    try:
        cantidad = int(context.args[1])
        if cantidad < 1 or cantidad > 999999:
            raise ValueError
    except:
        await update.message.reply_text(
            "La cantidad debe ser un número entre 1 y 999999.", parse_mode="HTML", reply_to_message_id=update.message.message_id
        )
        return

    if user_db.update_credits(
        to_user_id,
        -cantidad, tipo="admin_remove", motivo="Créditos retirados por admin"
    ):
        target_data = user_db.get_user(to_user_id)
        creditos = target_data["credits"]
        if isinstance(creditos, (int, float)):
            creditos = int(creditos)
        await update.message.reply_text(
            f"✅ Créditos retirados correctamente al usuario <code>{to_user_id}</code>.\n💳 Créditos actuales: {creditos}", parse_mode="HTML", reply_to_message_id=update.message.message_id
        )
    else:
        await update.message.reply_text(
            "❌ Usuario no encontrado.", parse_mode="HTML", reply_to_message_id=update.message.message_id
        )
        
PLANES_DIAS = [
    {"nombre": "BASICO - NV1",   "min": 3,  "max": 7,  "precio": {3: 10, 7: 15}},
    {"nombre": "STANDARD - NV2", "min": 15, "max": 25, "precio": {15: 20, 25: 35}},
    {"nombre": "PREMIUM - NV3",  "min": 30, "max": 90, "precio": {30: 35, 60: 60, 90: 90}},
]

VALID_DAYS = sorted({d for p in PLANES_DIAS for d in p["precio"].keys()})

def get_plan_for_days(dias: int):
    """
    Devuelve (plan_info, pack_days, precio).
    - Si 'dias' exacto existe → se usa.
    - Si no existe → busca el pack >= dias más cercano.
    - Si dias > todos → usa el máximo (90).
    """
    # Caso exacto
    for p in PLANES_DIAS:
        if dias in p["precio"]:
            return p, dias, p["precio"][dias]

    # Caso aproximado (hacia arriba)
    for d in VALID_DAYS:
        if d >= dias:
            candidates = []
            for p in PLANES_DIAS:
                if d in p["precio"]:
                    candidates.append((p, d, p["precio"][d]))
            if candidates:
                return min(candidates, key=lambda x: x[2])  # más barato

    # Si se pasa de todos, asignar el máximo
    max_d = max(VALID_DAYS)
    for p in PLANES_DIAS:
        if max_d in p["precio"]:
            return p, max_d, p["precio"][max_d]

async def sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Agregar días a un usuario (solo Sellers y Admin principal)."""
    user_id = update.effective_user.id
    data_seller = user_db.get_user(user_id)

    if not data_seller or (data_seller.get("role") not in ["seller", "admin"]):
        await update.message.reply_text("❌ No tienes permisos para usar este comando.")
        return

    # Parseo flexible
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        if not context.args:
            await update.message.reply_text("❗ Indica los días. Ejemplo: /sub 30")
            return
        target_id = str(update.message.reply_to_message.from_user.id)
        try:
            dias = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❗ Días inválidos.")
            return
    else:
        if len(context.args) < 2:
            await update.message.reply_text(
                "❗ Uso:\n• Responde a un usuario con: /sub <días>\n• O: /sub <id><días>"
            )
            return
        try:
            target_id = str(int(context.args[0]))
            dias = int(context.args[1])
        except ValueError:
            await update.message.reply_text("❗ Parámetros inválidos.")
            return

    # Validar usuario
    data_target = user_db.get_user(target_id)
    if not data_target:
        await update.message.reply_text("❌ Usuario no encontrado.")
        return

    # Buscar plan válido (exacto o aproximado)
    result = get_plan_for_days(dias)
    if not result:
        await update.message.reply_text("❌ No se encontró un plan válido.")
        return

    plan_info, pack_days, precio = result

    # Fechas
    f_inicio = datetime.now()
    f_caducidad = f_inicio + timedelta(days=pack_days)

    # Actualizar DB
    user_db.set_subscription(target_id, plan_info["nombre"])
    user_db.get_user(target_id)["credits"] = "♾️"
    user_db.set_expiration(target_id, f_caducidad)

    # Mensaje
    mensaje = f"""[#TRONCHITOBOT] ➾ AÑADIÓ DÍAS
                VENDEDOR ➾ {data_seller.get('first_name', '—')} - {user_id}
                USUARIO ➾ {data_target.get('first_name', '—')} - {target_id}
                SOLICITADO ➾ {dias} DÍAS
                ASIGNADO ➾ {pack_days} DÍAS
                PLAN ➾ {plan_info['nombre']}
                PRECIO ➾ {precio:.2f} SOLES
                F. INICIO ➾ {f_inicio.strftime("%d/%m/%Y - %I:%M:%S %p")}
                F. CADUCIDAD ➾ {f_caducidad.strftime("%d/%m/%Y - %I:%M:%S %p")}

                Gracias por confiar en nosotros. ¡Sigue disfrutando del servicio!"""

    await update.message.reply_text(mensaje)

async def unsub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data_seller = user_db.get_user(user_id)

    # 🔒 Verificar permisos
    if not data_seller or (data_seller.get("role") not in ["seller", "admin"]):
        await update.message.reply_text(
            "❌ No tienes permisos para usar este comando.", reply_to_message_id=update.message.message_id
        )
        return

    # 🔹 Obtener target_id
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        target_user = update.message.reply_to_message.from_user
        target_id = str(target_user.id)
    elif context.args:
        try:
            target_id = str(int(context.args[0]))
        except ValueError:
            await update.message.reply_text(
                "❗ El primer argumento debe ser un ID válido.", reply_to_message_id=update.message.message_id
            )
            return
    else:
        await update.message.reply_text(
            "❗ Debes responder al mensaje del usuario o poner su ID.", reply_to_message_id=update.message.message_id
        )
        return

    # 🔹 Validar que el usuario exista
    target_data = user_db.get_user(target_id)
    if not target_data:
        await update.message.reply_text(
            "❌ Usuario no encontrado en la base de datos.", reply_to_message_id=update.message.message_id
        )
        return

    # 🔹 Resetear suscripción y créditos
    user_db.reset_subscription(target_id)
    
    # Asegurarse que audit_log exista antes de actualizar créditos
    if "audit_log" not in target_data:
        target_data["audit_log"] = []

    user_db.update_credits(
        target_id,
        0, tipo="admin_remove", motivo=f"Suscripción revocada por {data_seller['first_name']}"
    )

    # 🔹 Mensaje final
    f_unsub = datetime.now().strftime("%d/%m/%Y - %I:%M:%S %p")
    mensaje = f"""[#TRONCHITOBOT] ➾ QUITÓ SUSCRIPCIÓN

VENDEDOR ➾ {data_seller['first_name']} {data_seller.get('last_name','')} - {user_id}
USUARIO ➾ {target_data['first_name']} {target_data.get('last_name','')} - {target_id}
PLAN ➾ {DEFAULT_PLAN}
CRÉDITOS ➾ {DEFAULT_CREDITS}
F. BAJA ➾ {f_unsub}

El plan ha sido revocado correctamente.
"""
    await update.message.reply_text(mensaje, reply_to_message_id=update.message.message_id)

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Muestra información del usuario.
    Prioridad:
        1️⃣ Reply a mensaje
        2️⃣ ID como argumento
        3️⃣ Info propia
    """
    # 1️⃣ Caso reply
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        target_user = update.message.reply_to_message.from_user
        target_id = str(target_user.id)

    # 2️⃣ Caso argumento con ID
    elif context.args:
        try:
            target_id = str(int(context.args[0]))
        except ValueError:
            await update.message.reply_text(
                "❗ Uso correcto:\n"
                "/info <user_id>\n"
                "O responde al mensaje de un usuario con /info.", parse_mode=ParseMode.HTML, reply_to_message_id=update.message.message_id
            )
            return

    # 3️⃣ Caso propio
    else:
        target_id = str(update.effective_user.id)

    # Obtener datos de la DB
    data = user_db.get_user(target_id)
    if not data:
        await update.message.reply_text(
            "❌ Usuario no encontrado en la base de datos.", parse_mode=ParseMode.HTML, reply_to_message_id=update.message.message_id
        )
        return

    # Formatear suscripción y nombre
    suscripcion = data.get("plan", "Free")
    nombre = (data.get("first_name", "") + " " + data.get("last_name", "")).strip()
    fecha_reg = str(data.get("registered_at", ""))[:10]

    # Mostrar créditos sin .0
    credits = data.get("credits", 0)
    try:
        # Muestra como entero si es convertible, sino muestra el texto (por ejemplo ♾️)
        credits_display = "♾️" if str(credits) in ["inf", "Infinity", "∞", "♾️"] else str(int(float(credits)))
    except Exception:
        credits_display = credits

    # Crear mensaje
    mensaje = (
    f"[#TRONCHITOBOT] ➾ PERFIL DE USUARIO\n\n"
    f"INFORMACIÓN PERSONAL\n\n"
    f"[🙎‍♂️] ID ➾ <code>{target_id}</code>\n"
    f"[👤] NOMBRE ➾ {italic(nombre) if nombre else 'Sin nombre'}\n"
    f"[👨🏻‍💻] USUARIO ➾ @{data['username'] if data.get('username') else 'Sin usuario'}\n"
    f"[💰] CRÉDITOS ➾ {bold(credits_display)}\n"
    f"[👑] ROL ➾ {data.get('role', '').capitalize()}\n"
    f"[📈] PLAN ➾ {suscripcion}\n"
    f"[📅] REGISTRADO ➾ {italic(fecha_reg)}"
)


    # Enviar foto de perfil si existe, sino solo el mensaje
    try:
        await update.message.reply_photo( photo="perfil.png", caption=mensaje, parse_mode=ParseMode.HTML, reply_to_message_id=update.message.message_id
        )
    except Exception:
        await update.message.reply_text(
            mensaje, parse_mode=ParseMode.HTML, reply_to_message_id=update.message.message_id
        )


async def infogrupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Muestra información de un grupo usando su ID.
    Uso:
        /infogrupo <group_id>
    Solo el admin principal puede usarlo.
    """
    # 🔹 Verificar permisos
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text(
            "❌ No tienes permisos para usar este comando.", reply_to_message_id=update.message.message_id
        )
        return

    # 🔹 Validar que se pase el ID
    if not context.args:
        await update.message.reply_text(
            "❗ Debes enviar el ID del grupo.\nUso: /infogrupo <group_id>", reply_to_message_id=update.message.message_id
        )
        return

    # 🔹 Validar que sea un número
    try:
        group_id_int = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❗ El ID del grupo debe ser un número válido.", reply_to_message_id=update.message.message_id
        )
        return

    # 🔹 Obtener info del grupo desde la DB
    group = user_db.get_group(group_id_int)
    if not group:
        await update.message.reply_text(
            "❌ Grupo no encontrado en la base de datos.", reply_to_message_id=update.message.message_id
        )
        return

    # 🔹 Obtener el nombre real del grupo desde Telegram
    try:
        chat = await context.bot.get_chat(group_id_int)
        group_name = chat.title if chat.title else "Grupo desconocido"
    except Exception:
        group_name = "Grupo desconocido"

    # 🔹 Construir mensaje
    mensaje = (
        f"👥 <b>Información del Grupo</b>\n\n"
        f"🆔 <b>ID:</b><code>{group_id_int}</code>\n"
        f"👥 <b>Nombre:</b> {group_name}\n"
        f"📦 <b>Plan:</b> {group.get('plan', 'Free')}\n"
        f"💳 <b>Acceso:</b> {'Ilimitado' if group.get('plan') == 'Premium' else 'Limitado'}\n"
        f"🗓️ <b>Agregado en:</b> {group.get('added_at', 'Desconocido')}"
    )

    await update.message.reply_text(
        mensaje, parse_mode=ParseMode.HTML, reply_to_message_id=update.message.message_id
    )


# 🔹 Dar acceso Premium a un grupo usando su ID
# Comando para dar acceso Premium a un grupo
async def addgroupremium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Solo el admin principal puede usarlo
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ No tienes permisos para usar este comando.")
        return

    if not context.args:
        await update.message.reply_text("❗ Debes enviar el ID del grupo.\nUso: /addgroupremium <group_id>")
        return

    group_id = context.args[0]

    # Validar que sea un número (acepta negativos)
    try:
        group_id_int = int(group_id)
    except ValueError:
        await update.message.reply_text("❌ ID de grupo inválido. Debe ser un número.")
        return

    # Obtener el nombre real del grupo desde Telegram
    try:
        chat = await context.bot.get_chat(group_id_int)
        group_name = chat.title if chat.title else "Grupo sin nombre"
    except Exception:
        group_name = "Nombre desconocido"

    # Asignar plan Premium en la base de datos
    if user_db.set_group_subscription(group_id_int, "Premium"):
        await update.message.reply_text(f"✅ Grupo '{group_name}' ({group_id_int}) ahora tiene plan Premium.")
    else:
        await update.message.reply_text(f"❌ No se pudo asignar Premium al grupo '{group_name}' ({group_id_int}).")

# Comando para quitar el plan Premium a un grupo
async def removegroupremium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Solo el admin principal puede usarlo
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ No tienes permisos para usar este comando.")
        return

    if not context.args:
        await update.message.reply_text("❗ Debes enviar el ID del grupo.\nUso: /removegroupremium <group_id>")
        return

    group_id = context.args[0]

    # Validar que sea un número (acepta negativos)
    try:
        group_id_int = int(group_id)
    except ValueError:
        await update.message.reply_text("❌ ID de grupo inválido. Debe ser un número.")
        return

    # Obtener el nombre real del grupo desde Telegram
    try:
        chat = await context.bot.get_chat(group_id_int)
        group_name = chat.title if chat.title else "Grupo sin nombre"
    except Exception:
        group_name = "Nombre desconocido"

    # Quitar plan Premium en la base de datos (volver a Free)
    if user_db.set_group_subscription(group_id_int, "Free"):
        await update.message.reply_text(f"✅ Grupo '{group_name}' ({group_id_int}) ahora tiene plan Free.")
    else:
        await update.message.reply_text(f"❌ No se pudo quitar Premium al grupo '{group_name}' ({group_id_int}).")

async def seller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Convierte a un usuario en seller.
    Prioridad:
        1️⃣ Reply a mensaje
        2️⃣ ID como argumento
    Solo el admin principal puede usarlo.
    """

    # 🔹 Verificar permisos
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text(
            "❌ No tienes permisos para hacer esto.", reply_to_message_id=update.message.message_id
        )
        return

    # 1️⃣ Caso reply
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        target_user = update.message.reply_to_message.from_user
        target_id = str(target_user.id)

    # 2️⃣ Caso argumento con ID
    elif context.args:
        try:
            target_id = str(int(context.args[0]))
        except ValueError:
            await update.message.reply_text(
                "❗ El ID debe ser un número válido.\n"
                "Uso: /seller <user_id> o responde al mensaje del usuario.", parse_mode=ParseMode.HTML, reply_to_message_id=update.message.message_id
            )
            return

    # 3️⃣ Caso sin reply ni ID
    else:
        await update.message.reply_text(
            "❗ Debes responder al mensaje de un usuario o poner su ID.", parse_mode=ParseMode.HTML, reply_to_message_id=update.message.message_id
        )
        return

    # 🔹 Verificar que el usuario exista en la base de datos
    if not user_db.get_user(target_id):
        await update.message.reply_text(
            "❌ Usuario no encontrado en la base de datos.", reply_to_message_id=update.message.message_id
        )
        return

    # 🔹 Actualizar la base de datos: rol, plan y créditos
    user_db.set_role(target_id, "seller")
    user_db.set_subscription(target_id, "Premium")
    user_db.update_credits(target_id, 2000)  # Créditos hasta 2000

    # 🔹 Obtener los datos del usuario para mostrar en el mensaje
    data = user_db.get_user(target_id)

    if not data:
        await update.message.reply_text("❌ Usuario no encontrado.", reply_to_message_id=update.message.message_id)
        return

    # 🔹 Crear mensaje de confirmación
    mensaje = f"""┏━━━━━━━━━━━━━━━┓
   ✅ ROL ACTUALIZADO
┗━━━━━━━━━━━━━━━┛

🆔 ID: {target_id}
👤 Nombre: {data['first_name']} {data['last_name']}
📱 Usuario: @{data['username'] if data.get('username') else 'Sin usuario'}

💳 Créditos: {data['credits']}
👑 Rol: Seller
📦 Plan: Premium"""

    # 🔹 Enviar mensaje
    try:
        await update.message.reply_photo( caption=mensaje, parse_mode=ParseMode.HTML, reply_to_message_id=update.message.message_id
        )
    except Exception:
        await update.message.reply_text(
            mensaje, parse_mode=ParseMode.HTML, reply_to_message_id=update.message.message_id
        )

async def unseller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Revoca el rol de seller a un usuario.
    Prioridad:
        1️⃣ Reply a mensaje
        2️⃣ ID como argumento
    Solo el admin principal puede usarlo.
    """

    # 🔹 Verificar permisos
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text(
            "❌ No tienes permisos para hacer esto.", reply_to_message_id=update.message.message_id
        )
        return

    # 1️⃣ Caso reply
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        target_user = update.message.reply_to_message.from_user
        target_id = str(target_user.id)

    # 2️⃣ Caso argumento con ID
    elif context.args:
        try:
            target_id = str(int(context.args[0]))
        except ValueError:
            await update.message.reply_text(
                "❗ El ID debe ser un número válido.\n"
                "Uso: /unseller <user_id> o responde al mensaje del usuario.", parse_mode=ParseMode.HTML, reply_to_message_id=update.message.message_id
            )
            return

    # 3️⃣ Caso sin reply ni ID
    else:
        await update.message.reply_text(
            "❗ Debes responder al mensaje de un usuario o poner su ID.", parse_mode=ParseMode.HTML, reply_to_message_id=update.message.message_id
        )
        return

    # 🔹 Obtener datos del usuario antes de modificarlo
    data = user_db.get_user(target_id)

    if not data:
        await update.message.reply_text("❌ Usuario no encontrado.", reply_to_message_id=update.message.message_id)
        return

    # 🔹 Revocar el rol de seller → user normal
    user_db.set_role(target_id, DEFAULT_ROLE)
    user_db.set_subscription(target_id, DEFAULT_PLAN)

    # 🔹 Restablecer créditos al valor por defecto
    user_db.data["users"][target_id]["credits"] = DEFAULT_CREDITS
    user_db._save()

    # 🔹 Crear mensaje de confirmación
    mensaje = f"""┏━━━━━━━━━━━━━━━━━┓
   ✅ USUARIO NORMAL
┗━━━━━━━━━━━━━━━━━┛

🆔 ID: {target_id}
👤 Nombre: {data['first_name']} {data['last_name']}
📱 Usuario: @{data['username'] if data.get('username') else 'Sin usuario'}

📦 Plan: {DEFAULT_PLAN}
💳 Créditos: {DEFAULT_CREDITS}
👑 Rol: {DEFAULT_ROLE.capitalize()}"""

    # 🔹 Enviar mensaje con foto opcional
    try:
        await update.message.reply_photo( caption=mensaje, parse_mode=ParseMode.HTML, reply_to_message_id=update.message.message_id
        )
    except Exception:
        await update.message.reply_text(
            mensaje, parse_mode=ParseMode.HTML, reply_to_message_id=update.message.message_id
        )

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando para eliminar un usuario o un grupo del JSON por ID.
    Uso: /delete <id>
    Solo el admin principal puede usarlo.
    """
    # 🔹 Verificar permisos
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ No tienes permisos para usar este comando.")
        return

    # 🔹 Verificar argumentos
    if len(context.args) != 1:
        await update.message.reply_text(
            "❗ Uso incorrecto.\nUso: /delete <id>\n"
            "Ejemplo: /delete 123456789"
        )
        return

    id_str = context.args[0]

    # Validar que sea un número (acepta negativos)
    try:
        id_int = int(id_str)
    except ValueError:
        await update.message.reply_text("❌ ID inválido. Debe ser un número.")
        return

    id_key = str(id_int)
    eliminado = False

    # 🔹 Intentar eliminar usuario
    if id_key in user_db.data.get("users", {}):
        user_db.data["users"].pop(id_key)
        eliminado = True

    # 🔹 Intentar eliminar grupo
    if id_key in user_db.data.get("groups", {}):
        user_db.data["groups"].pop(id_key)
        eliminado = True

    # 🔹 Guardar cambios y responder
    if eliminado:
        user_db._save()
        await update.message.reply_text(f"✅ ID {id_int} eliminado correctamente de la base de datos.")
    else:
        await update.message.reply_text(f"❌ ID {id_int} no encontrado en la base de datos.")

async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        await update.message.reply_text(f"📂 File ID: <code>{file_id}</code>", parse_mode="HTML")
    elif update.message.document:
        file_id = update.message.document.file_id
        await update.message.reply_text(f"📂 File ID: <code>{file_id}</code>", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ No detecté ninguna imagen o archivo.")

# ------ MENÚS Y CALLBACKS ------

async def telefonia_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['back']} Anterior", callback_data='pagina_anterior'),
            InlineKeyboardButton(f"Siguiente {EMOJIS['next']}", callback_data='pagina_siguiente')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['home']} Volver al menú", callback_data='volver_menu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mensaje = (
        f"{bold('[#TRONCHITOBOT] ➾ SISTEMA DE COMANDOS')}\n\n"
        f"{bold('CATEGORÍA → TELEFONÍA')}\n\n"
        f"{bold('COMANDOS → 2 disponibles')}\n"
        f"{bold('PÁGINA → 1/1')}\n\n"
        f"{EMOJIS['search']} {bold('TELEFONÍA DB')}\n"
        f"Estado: OPERATIVO {EMOJIS['ok']}\n"
        f"Comando: {bold('/telp 999888777')}\n"
        f"Precio: 1 CRÉDITO\n"
        f"Resultado: Consulta por número telefónico en OSIPTEL online\n\n"
        f"{EMOJIS['phone']} {bold('CEL DB')}\n"
        f"Estado: OPERATIVO {EMOJIS['ok']}\n"
        f"Comando: {bold('/cel 44443333')}\n"
        f"Precio: 1 CRÉDITO\n"
        f"Resultado: Consulta por DNI en OSIPTEL\n\n"        
        f"{EMOJIS['phone']} {bold('OSIPTEL DB')}\n"
        f"Estado: OPERATIVO {EMOJIS['ok']}\n"
        f"Comando: {bold('/osiptel 44443333')}\n"
        f"Precio: 1 CRÉDITO\n"
        f"Resultado: Consulta por DNI en OSIPTEL online\n"
    )
    await query.edit_message_caption(caption=mensaje, reply_markup=reply_markup, parse_mode="HTML")

async def reniec_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['back']} Anterior", callback_data='pagina_anterior'),
            InlineKeyboardButton(f"Siguiente {EMOJIS['next']}", callback_data='reniec_menu2')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['home']} Volver al menú", callback_data='volver_menu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mensaje = (
        f"{bold('[#TRONCHITOBOT] ➾ SISTEMA DE COMANDOS')}\n\n"
        f"{bold('CATEGORÍA → RENIEC')}\n\n"
        f"{bold('COMANDOS → 5 Comandos Disponibles')}\n"
        f"{bold('PÁGINA → 1/2')}\n\n"
        f"{EMOJIS['search']} {bold('BUSCAR DNI')}\n"
        f"Estado: (MANTENIMIENTO ⚒️)\n"
        f"Comando: {bold('/dni 12345678')}\n"
        f"Precio: 1 CRÉDITO\n"
        f"Resultado: Consulta por DNI en RENIEC online\n\n"
        f"Estado: (MANTENIMIENTO ⚒️)\n"
        f"Comando: {bold('/dnig 12345678')}\n"
        f"Precio: 1 CRÉDITO\n"
        f"Resultado: Consulta por DNI en RENIEC online Basica\n\n"
        f"Estado: (MANTENIMIENTO ⚒️)\n"
        f"Comando: {bold('/dnit 12345678')}\n"
        f"Precio: 1 CRÉDITO\n"
        f"Resultado: Consulta por DNI en RENIEC online Foto, Firma y Huella\n\n"
        f"Estado: OPERATIVO {EMOJIS['ok']}\n"
        f"Comando: {bold('/nm Juan Perez Ayala')}\n"
        f"Precio: 1 CRÉDITO\n"
        f"Resultado: Consulta por Nombre y Apellidos en RENIEC online\n\n"
        )
    await query.edit_message_caption(caption=mensaje, reply_markup=reply_markup, parse_mode="HTML")
    
async def reniec_menu2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['back']} Anterior", callback_data='reniec_menu'),
            InlineKeyboardButton(f"Siguiente {EMOJIS['next']}", callback_data='pagina_siguiente')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['home']} Volver al menú", callback_data='volver_menu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mensaje = (
        f"{bold('[#TRONCHITOBOT] ➾ SISTEMA DE COMANDOS')}\n\n"
        f"{bold('CATEGORÍA → RENIEC')}\n\n"
        f"{bold('COMANDOS → 5 Comandos Disponibles')}\n"
        f"{bold('PÁGINA → 2/2')}\n\n"
        f"{EMOJIS['search']} {bold('BUSCAR DNI')}\n"
        f"Estado: OPERATIVO {EMOJIS['ok']}\n"
        f"Comando: {bold('/dnis 12345678')}\n"
        f"Precio: 1 CRÉDITO\n"
        f"Resultado: Consulta por DNI en SEEKER\n\n"
        )
    await query.edit_message_caption(caption=mensaje, reply_markup=reply_markup, parse_mode="HTML")
    
async def sunarp_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['back']} Anterior", callback_data='pagina_anterior'),
            InlineKeyboardButton(f"Siguiente {EMOJIS['next']}", callback_data='pagina_siguiente')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['home']} Volver al menú", callback_data='volver_menu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mensaje = (
        f"{bold('[#TRONCHITOBOT] ➾ SISTEMA DE COMANDOS')}\n\n"
        f"{bold('CATEGORÍA → SUNARP')}\n\n"
        f"{bold('COMANDOS → 0 disponibles')}\n"
        f"{bold('PÁGINA → 1/1')}\n\n"
    )
    await query.edit_message_caption(caption=mensaje, reply_markup=reply_markup, parse_mode="HTML")

async def mundial_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['back']} Anterior", callback_data='pagina_anterior'),
            InlineKeyboardButton(f"Siguiente {EMOJIS['next']}", callback_data='pagina_siguiente')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['home']} Volver al menú", callback_data='volver_menu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mensaje = (
        f"{bold('[#TRONCHITOBOT] ➾ SISTEMA DE COMANDOS')}\n\n"
        f"{bold('CATEGORÍA → MUNDIAL')}\n\n"
        f"{bold('COMANDOS → 0 disponibles')}\n"
        f"{bold('PÁGINA → 1/1')}\n\n"
    )
    await query.edit_message_caption(caption=mensaje, reply_markup=reply_markup, parse_mode="HTML")

async def vip_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['back']} Anterior", callback_data='pagina_anterior'),
            InlineKeyboardButton(f"Siguiente {EMOJIS['next']}", callback_data='pagina_siguiente')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['home']} Volver al menú", callback_data='volver_menu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mensaje = (
        f"{bold('[#TRONCHITOBOT] ➾ SISTEMA DE COMANDOS')}\n\n"
        f"{bold('CATEGORÍA → VIP')}\n\n"
        f"{bold('COMANDOS → 0 disponibles')}\n"
        f"{bold('PÁGINA → 1/1')}\n\n"
        f"{EMOJIS['info']} No hay comandos VIP activos en este momento.\n"
    )
    await query.edit_message_caption(caption=mensaje, reply_markup=reply_markup, parse_mode="HTML")

async def policia_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['back']} Anterior", callback_data='pagina_anterior'),
            InlineKeyboardButton(f"Siguiente {EMOJIS['next']}", callback_data='pagina_siguiente')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['home']} Volver al menú", callback_data='volver_menu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mensaje = (
        f"{bold('[#TRONCHITOBOT] ➾ SISTEMA DE COMANDOS')}\n\n"
        f"{bold('CATEGORÍA → POLICIA')}\n\n"
        f"{bold('COMANDOS → 0 disponibles')}\n"
        f"{bold('PÁGINA → 1/1')}\n\n"
    )
    await query.edit_message_caption(caption=mensaje, reply_markup=reply_markup, parse_mode="HTML")
    
async def delitos_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['back']} Anterior", callback_data='pagina_anterior'),
            InlineKeyboardButton(f"Siguiente {EMOJIS['next']}", callback_data='pagina_siguiente')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['home']} Volver al menú", callback_data='volver_menu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mensaje = (
        f"{bold('[#TRONCHITOBOT] ➾ SISTEMA DE COMANDOS')}\n\n"
        f"{bold('CATEGORÍA → DELITOS')}\n\n"
        f"{bold('COMANDOS → 1 disponibles')}\n"
        f"{bold('PÁGINA → 1/1')}\n\n"
        f"{EMOJIS['search']} {bold('BUSCAR DENUNCIA POR DNI')}\n"
        f"Estado: OPERATIVO {EMOJIS['ok']}\n"
        f"Comando: {bold('/denuncias 12345678')}\n"
        f"Precio: 1 CRÉDITO\n"
        f"Resultado: Consulta por DNI DENUNCIAS online\n\n"
        f"{EMOJIS['search']} {bold('BUSCAR DENUNCIA POR DNI')}\n"
        f"Estado: OPERATIVO {EMOJIS['ok']}\n"
        f"Comando: {bold('/denunciasv 12345678')}\n"
        f"Precio: 1 CRÉDITO\n"
        f"Resultado: Visualiza por DNI cuantas DENUNCIAS tiene + FOTO\n"
    )
    await query.edit_message_caption(caption=mensaje, reply_markup=reply_markup, parse_mode="HTML")
    
async def seeker_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['back']} Anterior", callback_data='pagina_anterior'),
            InlineKeyboardButton(f"Siguiente {EMOJIS['next']}", callback_data='pagina_siguiente')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['home']} Volver al menú", callback_data='volver_menu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mensaje = (
        f"{bold('[#TRONCHITOBOT] ➾ SISTEMA DE COMANDOS')}\n\n"
        f"{bold('CATEGORÍA → SEEKER')}\n\n"
        f"{bold('COMANDOS → 2 disponibles')}\n"
        f"{bold('PÁGINA → 1/1')}\n\n"
        f"Estado: OPERATIVO {EMOJIS['ok']}\n"
        f"Comando: {bold('/seeker 12345678')}\n"
        f"Precio: 1 CRÉDITO\n"
        f"Resultado: Consulta por DNI busqueda SEEKER\n\n"
        f"{EMOJIS['search']} {bold('BUSCAR DENUNCIA POR DNI')}\n"
        f"Estado: OPERATIVO {EMOJIS['ok']}\n"
        f"Comando: {bold('/seekerpdf 12345678')}\n"
        f"Precio: 1 CRÉDITO\n"
        f"Resultado: Consulta por DNI busqueda SEEKER en PDF\n"
    )
    await query.edit_message_caption(caption=mensaje, reply_markup=reply_markup, parse_mode="HTML")

async def sunat_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['back']} Anterior", callback_data='pagina_anterior'),
            InlineKeyboardButton(f"Siguiente {EMOJIS['next']}", callback_data='pagina_siguiente')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['home']} Volver al menú", callback_data='volver_menu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mensaje = (
        f"{bold('[#TRONCHITOBOT] ➾ SISTEMA DE COMANDOS')}\n\n"
        f"{bold('CATEGORÍA → SUNAT')}\n\n"
        f"{bold('COMANDOS → 0 disponibles')}\n"
        f"{bold('PÁGINA → 1/1')}\n\n"
    )
    await query.edit_message_caption(caption=mensaje, reply_markup=reply_markup, parse_mode="HTML")

async def certificados_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['back']} Anterior", callback_data='pagina_anterior'),
            InlineKeyboardButton(f"Siguiente {EMOJIS['next']}", callback_data='pagina_siguiente')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['home']} Volver al menú", callback_data='volver_menu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mensaje = (
        f"{bold('[#TRONCHITOBOT] ➾ SISTEMA DE COMANDOS')}\n\n"
        f"{bold('CATEGORÍA → CERTIFICADOS')}\n\n"
        f"{bold('COMANDOS → 3 disponible')}\n"
        f"{bold('PÁGINA → 1/1')}\n\n"
        f"{EMOJIS['search']} {bold('BUSCAR ANTECEDENTES')}\n"
        f"Estado: (MANTENIMIENTO ⚒️)\n"
        f"Comando: {bold('/antpen 12345678')}\n"
        f"Precio: 1 CRÉDITO\n"
        f"Resultado: Consulta por DNI Antecedentes Penales\n\n"
        f"Estado: (MANTENIMIENTO ⚒️)\n"
        f"Comando: {bold('/antjud 12345678')}\n"
        f"Precio: 1 CRÉDITO\n"
        f"Resultado: Consulta por DNI Antecedentes Judiciales\n\n"
        f"Estado: (MANTENIMIENTO ⚒️)\n"
        f"Comando: {bold('/antpol 12345678')}\n"
        f"Precio: 1 CRÉDITO\n"
        f"Resultado: Consulta por DNI Antecedentes Policiales\n\n"
    )
    await query.edit_message_caption(caption=mensaje, reply_markup=reply_markup, parse_mode="HTML")
    
async def gratis_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['back']} Anterior", callback_data='pagina_anterior'),
            InlineKeyboardButton(f"Siguiente {EMOJIS['next']}", callback_data='pagina_siguiente')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['home']} Volver al menú", callback_data='volver_menu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mensaje = (
        f"{bold('[#TRONCHITOBOT] ➾ SISTEMA DE COMANDOS')}\n\n"
        f"{bold('CATEGORÍA → GRATIS')}\n\n"
        f"{bold('COMANDOS → 0 disponibles')}\n"
        f"{bold('PÁGINA → 1/1')}\n\n"
    )
    await query.edit_message_caption(caption=mensaje, reply_markup=reply_markup, parse_mode="HTML")

async def generador_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['back']} Anterior", callback_data='pagina_anterior'),
            InlineKeyboardButton(f"Siguiente {EMOJIS['next']}", callback_data='pagina_siguiente')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['home']} Volver al menú", callback_data='volver_menu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mensaje = (
        f"{bold('[#TRONCHITOBOT] ➾ SISTEMA DE COMANDOS')}\n\n"
        f"{bold('CATEGORÍA → GENERADOR')}\n\n"
        f"{bold('COMANDOS → 0 disponibles')}\n"
        f"{bold('PÁGINA → 1/1')}\n\n"
    )
    await query.edit_message_caption(caption=mensaje, reply_markup=reply_markup, parse_mode="HTML")

async def baucher_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['back']} Anterior", callback_data='pagina_anterior'),
            InlineKeyboardButton(f"Siguiente {EMOJIS['next']}", callback_data='pagina_siguiente')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['home']} Volver al menú", callback_data='volver_menu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mensaje = (
        f"{bold('[#TRONCHITOBOT] ➾ SISTEMA DE COMANDOS')}\n\n"
        f"{bold('CATEGORÍA → BAUCHER')}\n\n"
        f"{bold('COMANDOS → 0 disponibles')}\n"
        f"{bold('PÁGINA → 1/1')}\n\n"
    )
    await query.edit_message_caption(caption=mensaje, reply_markup=reply_markup, parse_mode="HTML")

async def extras_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['back']} Anterior", callback_data='pagina_anterior'),
            InlineKeyboardButton(f"Siguiente {EMOJIS['next']}", callback_data='pagina_siguiente')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['home']} Volver al menú", callback_data='volver_menu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mensaje = (
        f"{bold('[#TRONCHITOBOT] ➾ SISTEMA DE COMANDOS')}\n\n"
        f"{bold('CATEGORÍA → EXTRAS')}\n\n"
        f"{bold('COMANDOS → 0 disponibles')}\n"
        f"{bold('PÁGINA → 1/1')}\n\n"
    )
    await query.edit_message_caption(caption=mensaje, reply_markup=reply_markup, parse_mode="HTML")

async def familiares_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['back']} Anterior", callback_data='pagina_anterior'),
            InlineKeyboardButton(f"Siguiente {EMOJIS['next']}", callback_data='pagina_siguiente')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['home']} Volver al menú", callback_data='volver_menu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mensaje = (
        f"{bold('[#TRONCHITOBOT] ➾ SISTEMA DE COMANDOS')}\n\n"
        f"{bold('CATEGORÍA → FAMILIARES')}\n\n"
        f"{bold('COMANDOS → 2 disponibles')}\n"
        f"{bold('PÁGINA → 1/1')}\n\n"
        f"Estado: OPERATIVO {EMOJIS['ok']}\n"
        f"Comando: {bold('/ag 12345678')}\n"
        f"Precio: 1 CRÉDITO\n"
        f"Resultado: Consulta por DNI Familiares en SISFOH\n\n"
        f"Estado: OPERATIVO {EMOJIS['ok']}\n"
        f"Comando: {bold('/agv 12345678')}\n"
        f"Precio: 1 CRÉDITO\n"
        f"Resultado: Consulta por DNI Familiares en SISFOH Visual\n\n"
        f"Estado: OPERATIVO {EMOJIS['ok']}\n"
        f"Comando: {bold('/agvp 12345678')}\n"
        f"Precio: 1 CRÉDITO\n"
        f"Resultado: Consulta por DNI Familiares en SISFOH En PDF\n\n"
    )
    await query.edit_message_caption(caption=mensaje, reply_markup=reply_markup, parse_mode="HTML")

async def actas_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['back']} Anterior", callback_data='pagina_anterior'),
            InlineKeyboardButton(f"Siguiente {EMOJIS['next']}", callback_data='pagina_siguiente')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['home']} Volver al menú", callback_data='volver_menu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mensaje = (
        f"{bold('[#TRONCHITOBOT] ➾ SISTEMA DE COMANDOS')}\n\n"
        f"{bold('CATEGORÍA → ACTAS')}\n\n"
        f"{bold('COMANDOS → 0 disponibles')}\n"
        f"{bold('PÁGINA → 1/1')}\n\n"
    )
    await query.edit_message_caption(caption=mensaje, reply_markup=reply_markup, parse_mode="HTML")

async def vehiculos_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['back']} Anterior", callback_data='pagina_anterior'),
            InlineKeyboardButton(f"Siguiente {EMOJIS['next']}", callback_data='pagina_siguiente')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['home']} Volver al menú", callback_data='volver_menu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mensaje = (
        f"{bold('[#TRONCHITOBOT] ➾ SISTEMA DE COMANDOS')}\n\n"
        f"{bold('CATEGORÍA → VEHICULOS')}\n\n"
        f"{bold('COMANDOS → 2 disponibles')}\n"
        f"{bold('PÁGINA → 1/1')}\n\n"
        f"{EMOJIS['search']} {bold('BUSCAR PLACA')}\n"
        f"Estado: OPERATIVO {EMOJIS['ok']}\n"
        f"Comando: {bold('/placa ABC123')}\n"
        f"Precio: 1 CRÉDITO\n"
        f"Resultado: Consulta por placa vehicular en SUNARP online\n\n"
        f"{EMOJIS['search']} {bold('BUSCAR TARJETA VEHICULAR')}\n"
        f"Estado: OPERATIVO {EMOJIS['ok']}\n"
        f"Comando: {bold('/taj 777333')}\n"
        f"Precio: 1 CRÉDITO\n"
        f"Resultado: Consulta por tarjeta vehicular en SUNARP online\n"
    )
    await query.edit_message_caption(caption=mensaje, reply_markup=reply_markup, parse_mode="HTML")

async def infoburo_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['back']} Anterior", callback_data='pagina_anterior'),
            InlineKeyboardButton(f"Siguiente {EMOJIS['next']}", callback_data='pagina_siguiente')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['home']} Volver al menú", callback_data='volver_menu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mensaje = (
        f"{bold('[#TRONCHITOBOT] ➾ SISTEMA DE COMANDOS')}\n\n"
        f"{bold('CATEGORÍA → INFO BURO')}\n\n"
        f"{bold('COMANDOS → 1 disponibles')}\n"
        f"{bold('PÁGINA → 1/1')}\n\n"
        f"{EMOJIS['search']} {bold('BUSCAR DNI')}\n"
        f"Estado: OPERATIVO {EMOJIS['ok']}\n"
        f"Comando: {bold('/riesgo 12345678')}\n"
        f"Precio: 1 CRÉDITO\n"
        f"Resultado: Consulta por DNI en INFO BURO\n\n"
    )
    await query.edit_message_caption(caption=mensaje, reply_markup=reply_markup, parse_mode="HTML")

async def volver_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    nombre_completo = user.first_name
    if user.last_name:
        nombre_completo += f" {user.last_name}"

    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['Telefonía']} TELEFONIA", callback_data='telefonia'),
            InlineKeyboardButton(f"{EMOJIS['Identidad']} RENIEC", callback_data='reniec')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['home']} SUNARP", callback_data='sunarp'),
            InlineKeyboardButton(f"{EMOJIS['Global']} MUNDIAL", callback_data='mundial')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['Premium']} VIP", callback_data='vip'),
            InlineKeyboardButton(f"{EMOJIS['Policía']} POLICIA", callback_data='policia')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['Seguridad']} DELITOS", callback_data='delitos'),
            InlineKeyboardButton(f"{EMOJIS['Búsqueda']} SEEKER", callback_data='seeker')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['Impuestos']} SUNAT", callback_data='sunat'),
            InlineKeyboardButton(f"{EMOJIS['Comprobante']} CERTIFICADOS", callback_data='certificados')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['Promoción']} GRATIS", callback_data='gratis'),
            InlineKeyboardButton(f"{EMOJIS['Herramienta']} GENERADOR", callback_data='generador')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['credit']} BAUCHER", callback_data='baucher'),
            InlineKeyboardButton(f"{EMOJIS['Adicionales']} EXTRAS", callback_data='extras')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['Familia']} FAMILIARES", callback_data='familiares'),
            InlineKeyboardButton(f"{EMOJIS['Actas']} ACTAS", callback_data='actas')
        ],
        [
            InlineKeyboardButton(f"{EMOJIS['Transporte']} VEHICULOS", callback_data='vehiculos'),
            InlineKeyboardButton(f"{EMOJIS['Créditos']} INFO BURO", callback_data='infoburo') 
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    mensaje = (
        f"{bold('[#TRONCHITOBOT] ➾ SISTEMA DE COMANDOS')}\n\n"
        f"{EMOJIS['menu']} {bold('➣ Hola,')} {italic(nombre_completo)}\n\n"
        f"{EMOJIS['welcome']} {bold('Bienvenido al menú principal de comandos')}\n\n"
        f"Selecciona una opción según la categoría que deseas explorar:"
    )
    await query.edit_message_caption(caption=mensaje, reply_markup=reply_markup, parse_mode="HTML")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Siempre responde al callback

    data = query.data
    if data == 'telefonia':
        await telefonia_menu(update, context)
    elif data == 'reniec':
        await reniec_menu(update, context)
    elif data == 'sunarp':
        await sunarp_menu(update, context)
    elif data == 'mundial':
        await mundial_menu(update, context)
    elif data == 'vip':
        await vip_menu(update, context)
    elif data == 'policia':
        await policia_menu(update, context)
    elif data == 'delitos':
        await delitos_menu(update, context)
    elif data == 'seeker':
        await seeker_menu(update, context)
    elif data == 'sunat':
        await sunat_menu(update, context)
    elif data == 'certificados':
        await certificados_menu(update,context)
    elif data == 'gratis':
        await gratis_menu(update, context)
    elif data == 'generador':
        await generador_menu(update, context)
    elif data == 'baucher':
        await baucher_menu(update, context)
    elif data == 'extras':
        await extras_menu(update, context)
    elif data == 'familiares':
        await familiares_menu(update, context)
    elif data == 'actas':
        await actas_menu(update, context)
    elif data == 'vehiculos':
        await vehiculos_menu(update, context)
    elif data == 'infoburo':
        await infoburo_menu(update, context)
    elif data == 'volver_menu':
        await volver_menu(update, context)
    elif data == 'reniec_menu':
        await reniec_menu(update, context)
    elif data == 'reniec_menu2':
        await reniec_menu2(update, context)
    elif data == 'pagina_anterior':
        await query.answer("No hay páginas anteriores.", show_alert=True)
    elif data == 'pagina_siguiente':
        await query.answer("No hay páginas siguientes.", show_alert=True)
    else:
        await query.answer("Función en desarrollo.")

def safe_field(value):
    return value if value not in [None, "", " "] else "-"

# ----------- CRÉDITOS -----------

async def verifica_creditos(update, user_id, tipo="consulta"):
    # 🔹 Obtener usuario desde la base de datos
    user = user_db.get_user(user_id)
    if not user:
        await update.message.reply_text(
            f"{EMOJIS['warn']} Debes registrarte primero con /register.",
            parse_mode="HTML"
        )
        return False

    # 🔹 Si el usuario tiene una suscripción activa, no se descuentan créditos
    if user_db.has_subscription(user_id):
        return True

    # 🔹 Obtener créditos del usuario
    credits = user.get("credits", 0)

    # 🔹 Manejar el caso de créditos infinitos
    if str(credits) == "♾️":
        return True

    # 🔹 Aseguramos que sea numérico
    try:
        credits_val = float(credits)
    except (ValueError, TypeError):
        credits_val = 0

    # 🔹 Verificar si tiene créditos suficientes
    if credits_val < 1:
        await update.message.reply_text(
            f"{EMOJIS['error']} Créditos insuficientes. Usa /me para ver tu perfil.",
            parse_mode="HTML"
        )
        return False

    # 🔹 Descontar 1 crédito por la acción realizada
    user_db.update_credits(user_id, -1, tipo, f"Consumo por {tipo}")

    return True

# ----------- PERMISOS DE ADM ------------
async def require_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Verifica si el bot tiene permisos de administrador en el chat.
    Retorna True si los tiene, False si no.
    """
    chat = update.effective_chat
    bot = context.bot

    # Evita error si el comando viene de un chat privado
    if chat.type == "private":
        return True

    try:
        member = await bot.get_chat_member(chat.id, bot.id)
        if member.status == "administrator":
            return True
        else:
            await update.message.reply_text(
                "⚠️ No puedo ejecutar este comando porque no tengo permisos de administrador en este grupo.\n"
                "Por favor, otórgame permisos de <b>administrador</b> para continuar.",
                parse_mode="HTML",
                reply_to_message_id=update.message.message_id
            )
            return False
    except Exception as e:
        print(f"[ERROR] Verificando permisos de admin: {e}")
        return False

# ----------- COMANDOS DE CONSULTA -----------

async def dni(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    user_id = update.effective_user.id

    # 🧩 Verificar argumentos
    if len(context.args) != 1:
        await update.message.reply_text(
            "❗<b>Uso correcto:</b>\n"
            "/dni <code>dni</code>\n"
            "Ejemplo: <code>/dni 12345678</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # 🧩 Verificar registro en users_db.json
    try:
        with open("users_db.json", "r", encoding="utf-8") as f:
            users_db = json.load(f)
        users = users_db.get("users", {})
    except Exception:
        await update.message.reply_text(
            "❌ Error al leer la base de datos de usuarios.",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    if str(user_id) not in users:
        await update.message.reply_text(
            "⚠️ No puedes usar este comando porque no estás registrado.\n"
            "Usa /register para poder registrarte.",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    user_info = users[str(user_id)]
    credits = user_info.get("credits", "—")
    username = user_info.get("username", "Desconocido")
    
    # 🧩 Formatear créditos para evitar ".0"
    if isinstance(credits, (int, float)):
        if credits == int(credits):
            credits = int(credits)
        else:
            credits = round(credits, 2)

    # 🧩 Verificar créditos antes de procesar
    if not await verifica_creditos(update, user_id, 'reniec_dni'):
        return

    dni_value = context.args[0]

    loading_message = await update.message.reply_photo(
        photo="TRONCHITOBOT.png",
        caption="[⏳] PROCESANDO SOLICITUD EN RENIEC.....",
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )

    try:
        # Endpoint
        url = f"https://zgatoodni.up.railway.app/dniresult?dni={dni_value}&key=b1cbc24054d062a4aae709f9785c30c"
        response = requests.get(url, timeout=30)

        if response.status_code != 200:
            mensaje = "❌ Error al consultar con Reniec."
        else:
            result = response.json()
            data = result.get("data", {})

            if not data:
                mensaje = "❌ No se encontró persona con ese DNI."
            else:
                # 🧩 Construir mensaje con formato original
                mensaje = (
                    f"[#TRONCHITOBOT] ➾ RENIEC X DNI\n\n"
                    f"DNI ➾ <code>{data.get('DNI', '')}</code>\n"
                    f"NOMBRES ➾ {data.get('NOMBRES', '')}\n"
                    f"APELLIDOS ➾ {data.get('APELLIDOS', '')}\n"
                    f"GENERO ➾ {data.get('GENERO', '')}\n"
                    f"EDAD ➾ {data.get('EDAD', '')}\n"
                    f"ESTADO CIVIL ➾ {data.get('ESTADO_CIVIL', '')}\n"
                    f"RESTRICCIÓN ➾ {data.get('RESTRICCION', '')}\n\n"

                    f"[🎂] NACIMIENTO\n\n"
                    f"FECHA NACIMIENTO ➾ {data.get('FECHA_NACIMIENTO', '')}\n"
                    f"PADRE ➾ {data.get('PADRE', '')}\n"
                    f"MADRE ➾ {data.get('MADRE', '')}\n\n"

                    f"[📋] INFORMACIÓN GENERAL\n\n"
                    f"FECHA INSCRIPCIÓN ➾ {data.get('FECHA_INSCRIPCION', '')}\n"
                    f"FECHA EMISIÓN ➾ {data.get('FECHA_EMISION', '')}\n"
                    f"FECHA CADUCIDAD ➾ {data.get('FECHA_CADUCIDAD', '')}\n"
                    f"NIVEL EDUCATIVO ➾ {data.get('NIVEL_EDUCATIVO', '')}\n"
                    f"ESTATURA ➾ {data.get('ESTATURA', '')}\n"
                    f"DONANTE ÓRGANOS ➾ {data.get('DONANTE_ORGANOS', '')}\n\n"

                    f"[🏠] DOMICILIO\n\n"
                    f"DIRECCIÓN ➾ {data.get('DIRECCION', '')}\n"
                    f"DISTRITO ➾ {data.get('DISTRITO', '')}\n"
                    f"PROVINCIA ➾ {data.get('PROVINCIA', '')}\n"
                    f"DEPARTAMENTO ➾ {data.get('DEPARTAMENTO', '')}\n"

                    f"[📍] UBIGEOS\n\n"
                    f"UBIGEO RENIEC ➾ {data.get('UBIGEO_RENIEC', '')}\n"
                    f"UBIGEO INEI ➾ {data.get('UBIGEO_INE', '')}\n"
                    f"UBIGEO SUNAT ➾ {data.get('UBIGEO_SUNAT', '')}\n\n"

                    f"[⚡] ESTADO DE CUENTA\n\n"
                    f"CREDITOS ➾ <code>{credits}</code> - <code>{user_id}</code>\n"
                    f"USUARIO ➾ {username}\n"
                )

                # 🧩 Procesar imagen si existe
                photo_b64 = result.get("photo_base64")
                if photo_b64:
                    try:
                        if photo_b64.startswith("data:image"):
                            _, encoded = photo_b64.split(",", 1)
                        else:
                            encoded = photo_b64

                        photo_bytes = base64.b64decode(encoded)
                        bio = BytesIO(photo_bytes)
                        bio.name = f"{dni_value}.jpg"

                        await update.message.reply_photo(
                            photo=InputFile(bio),
                            caption=mensaje,
                            parse_mode="HTML",
                            reply_to_message_id=update.message.message_id
                        )
                        await loading_message.delete()
                        return
                    except Exception as e:
                        mensaje += f"\n⚠️ Error al procesar la foto: {e}"

    except Exception:
        mensaje = "❌ Error de conexión con el servidor."

    # 🧩 Enviar mensaje sin foto
    await update.message.reply_text(
        mensaje, parse_mode="HTML", reply_to_message_id=update.message.message_id
    )
    await loading_message.delete()

async def dnis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update, context):
        return
    user_id = update.effective_user.id

    # 🧩 Verificar argumentos
    if len(context.args) != 1:
        await update.message.reply_text(
            "❗<b>Uso correcto:</b>\n"
            "/dni <code>dni</code>\n"
            "Ejemplo: <code>/dni 12345678</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # 🧩 Verificar registro en users_db.json
    try:
        with open("users_db.json", "r", encoding="utf-8") as f:
            users_db = json.load(f)
        users = users_db.get("users", {})
    except Exception:
        await update.message.reply_text(
            "❌ Error al leer la base de datos de usuarios.",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    if str(user_id) not in users:
        await update.message.reply_text(
            "⚠️ No puedes usar este comando porque no estás registrado.\n"
            "Usa /register para poder registrarte.",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    user_info = users[str(user_id)]
    credits = user_info.get("credits", "—")
    username = user_info.get("username", "Desconocido")

    # 🧩 Formatear créditos para evitar ".0"
    if isinstance(credits, (int, float)):
        credits = int(credits) if credits == int(credits) else round(credits, 2)

    # 🧩 Verificar créditos antes de procesar
    if not await verifica_creditos(update, user_id, 'reniec_dni'):
        return

    dni_value = context.args[0]

    loading_message = await update.message.reply_photo(
        photo="TRONCHITOBOT.png",
        caption="[⏳] PROCESANDO SOLICITUD EN RENIEC.....",
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )

    mensaje = "❌ Error inesperado."
    try:
        # 🔗 Endpoint (ajústalo si es distinto)
        url = f"https://web-production-da283.up.railway.app/dni?dni={dni_value}"
        response = requests.get(url, timeout=30)

        if response.status_code != 200:
            mensaje = "❌ Error al consultar con Reniec."
        else:
            result = response.json()
            data = (result or {}).get("data", {}) or {}
            if not data:
                mensaje = "❌ No se encontró persona con ese DNI."
            else:
                dni_resp = data.get("dni", "") or ""
                nombre = data.get("nombre", "") or ""
                datos = data.get("datos", {}) or {}

                # Campos dentro de "datos" (con llaves en español y espacios)
                fecha_nac = datos.get("Fecha de Nacimiento", "")
                edad = datos.get("Edad", "")
                sexo = datos.get("Sexo", "")
                estado_civil = datos.get("Estado", "")
                padre = datos.get("Padre", "")
                madre = datos.get("Madre", "")
                ubicacion = datos.get("Ubicación", "") or datos.get("Ubicacion", "")
                direccion = datos.get("Dirección", "") or datos.get("Direccion", "")
                ubigeo_nac = datos.get("Ubigeo Nacimiento", "")
                fecha_fallec = datos.get("Fecha de Fallecimiento", "")

                # 🧩 Construir mensaje con formato similar al original
                mensaje = (
                    f"[#TRONCHITOBOT] ➾ RENIEC X DNI\n\n"
                    f"DNI ➾ <code>{dni_resp}</code>\n"
                    f"NOMBRE COMPLETO ➾ {nombre}\n"
                    f"SEXO ➾ {sexo}\n"
                    f"EDAD ➾ {edad}\n"
                    f"ESTADO CIVIL ➾ {estado_civil}\n"
                    f"FECHA DE FALLECIMIENTO ➾ {fecha_fallec}\n\n"

                    f"[🎂] NACIMIENTO\n\n"
                    f"FECHA NACIMIENTO ➾ {fecha_nac}\n"
                    f"PADRE ➾ {padre}\n"
                    f"MADRE ➾ {madre}\n"
                    f"UBIGEO NACIMIENTO ➾ {ubigeo_nac}\n\n"

                    f"[📋] INFORMACIÓN GENERAL\n\n"
                    f"UBICACIÓN ➾ {ubicacion}\n"
                    f"DIRECCIÓN ➾ {direccion}\n\n"

                    f" ➤ {bold('Estado de Cuenta del Usuario')}\n\n"
                    f"Créditos disponibles ➤ <code>{credits}</code>\n"
                    f"ID de usuario ➤ <code>{user_id}</code>\n"
                    f"Usuario ➤ <code>{username}</code>\n"
                )

                # 📷 Procesar foto si viene en base64 en "data.foto"
                photo_b64 = data.get("foto")
                if photo_b64:
                    try:
                        encoded = photo_b64.split(",", 1)[1] if photo_b64.startswith("data:image") else photo_b64
                        photo_bytes = base64.b64decode(encoded)
                        bio = BytesIO(photo_bytes)
                        bio.name = f"{dni_value}.jpg"

                        await update.message.reply_photo(
                            photo=InputFile(bio),
                            caption=mensaje,
                            parse_mode="HTML",
                            reply_to_message_id=update.message.message_id
                        )
                        await loading_message.delete()
                        return
                    except Exception as e:
                        mensaje += f"\n⚠️ Error al procesar la foto: {e}"

    except Exception:
        mensaje = "❌ Error de conexión con el servidor."
    finally:
        try:
            await loading_message.delete()
        except Exception:
            pass

    # 🧩 Enviar mensaje sin foto
    await update.message.reply_text(
        mensaje, parse_mode="HTML", reply_to_message_id=update.message.message_id
    )

async def dnig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # 🧩 Verificar argumentos
    if len(context.args) != 1:
        await update.message.reply_text(
            "❗ <b>Uso correcto:</b>\n"
            "/dnig <code>dnig</code>\n"
            "Ejemplo: <code>/dnig 12345678</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # 🧩 Cargar base de datos de usuarios
    try:
        with open("users_db.json", "r", encoding="utf-8") as f:
            users_db = json.load(f)
        users = users_db.get("users", {})
    except Exception:
        await update.message.reply_text(
            "❌ Error al leer la base de datos de usuarios.",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # 🧩 Verificar si el usuario está registrado
    if str(user_id) not in users:
        await update.message.reply_text(
            "⚠️ No puedes usar este comando porque no estás registrado.\n"
            "Usa /register para poder registrarte.",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # 🧩 Obtener datos del usuario
    user_info = users[str(user_id)]
    username = user_info.get("username", "Desconocido")
    credits = user_info.get("credits", "—")

    # Evitar .0 en créditos
    if isinstance(credits, (int, float)):
        credits = int(credits) if credits == int(credits) else round(credits, 2)

    if not await verifica_creditos(update, user_id, 'reniec_dni'):
        return

    dni_value = context.args[0]

    loading_message = await update.message.reply_photo(
        photo="TRONCHITOBOT.png",
        caption="[⏳] PROCESANDO SOLICITUD EN RENIEC.....",
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )

    try:
        url = f"https://zgatoodni.up.railway.app/dniresult?dni={dni_value}&key=b1cbc24054d062a4aae709f9785c30c"
        response = requests.get(url, timeout=30)

        if response.status_code != 200:
            mensaje = "❌ Error al consultar con Reniec, intentelo denuevo."
        else:
            result = response.json()
            data = result.get("data", {})

            if not data:
                mensaje = "❌ No se encontró persona con ese DNI."
            else:
                mensaje = (
                    f"[#TRONCHITOBOT] ➾ RENIEC X DNI\n\n"
                    f"BUSQUEDA X DNI GRATIS\n\n"
                    f"DNI ➾ {data.get('DNI', '')}\n"
                    f"NOMBRES ➾ {data.get('NOMBRES', '')}\n"
                    f"APELLIDOS ➾ {data.get('APELLIDOS', '')}\n"
                    f"GENERO ➾ {data.get('GENERO', '')}\n"
                    f"EDAD ➾ {data.get('EDAD', '')}\n"
                    f"ESTADO CIVIL ➾ {data.get('ESTADO_CIVIL', '')}\n\n"
                    f"[🎂] NACIMIENTO\n"
                    f"FECHA NACIMIENTO ➾ {data.get('FECHA_NACIMIENTO', '')}\n"
                    f"PADRE ➾ {data.get('PADRE', '')}\n"
                    f"MADRE ➾ {data.get('MADRE', '')}\n\n"
                    f"[🏠] DOMICILIO\n"
                    f"DIRECCIÓN ➾ {data.get('DIRECCION', '')}\n"
                    f"DISTRITO ➾ {data.get('DISTRITO', '')}\n"
                    f"PROVINCIA ➾ {data.get('PROVINCIA', '')}\n"
                    f"DEPARTAMENTO ➾ {data.get('DEPARTAMENTO', '')}\n\n"
                    "🔎 ¿Necesitas más información?\n"
                    "Utiliza el comando /dni para acceder a \n"
                    "datos completos y detallados.\n\n"
                    f"[⚡] ESTADO DE CUENTA\n\n"
                    f"CREDITOS ➾ <code>{credits}</code> - <code>{user_id}</code>\n"
                    f"USUARIO ➾ {username}\n"
                )

                photo_b64 = result.get("photo_base64")
                if photo_b64:
                    try:
                        # 🔹 Procesar imagen Base64
                        if photo_b64.startswith("data:image"):
                            _, encoded = photo_b64.split(",", 1)
                        else:
                            encoded = photo_b64

                        photo_bytes = base64.b64decode(encoded)
                        img = Image.open(BytesIO(photo_bytes)).convert("RGBA")

                        # 🔸 Aplicar desenfoque más fuerte
                        blurred_img = img.filter(ImageFilter.GaussianBlur(radius=6))

                        # 🔸 Agregar texto “ELPERUANODATA_BOT” sin fondo
                        draw = ImageDraw.Draw(blurred_img)
                        width, height = blurred_img.size
                        text = "ELPERUANODATA_BOT"

                        try:
                            font = ImageFont.truetype("arial.ttf", int(height * 0.06))
                        except:
                            font = ImageFont.load_default()

                        # Calcular tamaño del texto
                        try:
                            bbox = draw.textbbox((0, 0), text, font=font)
                            text_width = bbox[2] - bbox[0]
                            text_height = bbox[3] - bbox[1]
                        except AttributeError:
                            text_width, text_height = draw.textsize(text, font=font)

                        x = (width - text_width) / 2
                        y = height - text_height - 10

                        draw.text(
                            (x, y),
                            text,
                            fill=(255, 255, 255, 180),
                            font=font
                        )

                        bio = BytesIO()
                        blurred_img.convert("RGB").save(bio, format="JPEG")
                        bio.seek(0)
                        bio.name = f"{dni_value}.jpg"

                        await update.message.reply_photo(
                            photo=InputFile(bio),
                            caption=mensaje,
                            parse_mode="HTML",
                            reply_to_message_id=update.message.message_id
                        )
                        await loading_message.delete()
                        return

                    except Exception as e:
                        mensaje += f"\n⚠️ Error al procesar la foto: {e}"

    except Exception:
        mensaje = "❌ Error de conexión de consola"

    await update.message.reply_text(
        mensaje, parse_mode="HTML", reply_to_message_id=update.message.message_id
    )
    await loading_message.delete()

async def dnit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if len(context.args) != 1:
        await update.message.reply_text(
            "❗ <b>Uso correcto:</b>\n"
            "/dnit <code>dnit</code>\n"
            "Ejemplo: <code>/dnit 12345678</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    if not await verifica_creditos(update, user_id, 'reniec_dni'):
        return

    dni_value = context.args[0]

    loading_message = await update.message.reply_photo(
        photo="TRONCHITOBOT.png",
        caption="[⏳] PROCESANDO SOLICITUD EN RENIEC.....",
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )

    try:
        url = f"https://zgatoodnit.up.railway.app/dnit?dni={dni_value}&key=ccb8e2c720304c89d72c4d3d"
        response = requests.get(url, timeout=30)

        if response.status_code != 200:
            await update.message.reply_text(
                "❌ Error al consultar con Reniec.",
                parse_mode="HTML",
                reply_to_message_id=update.message.message_id
            )
            await loading_message.delete()
            return

        result = response.json()
        data = result.get("data", {})

        if not data:
            await update.message.reply_text(
                "❌ No se encontró persona con ese DNI.",
                parse_mode="HTML",
                reply_to_message_id=update.message.message_id
            )
            await loading_message.delete()
            return

        # 📝 Texto del DNI
        mensaje = (
            f"[#TRONCHITOBOT] ➾ RENIEC X DNI\n\n"
            f"DNI ➾ {data.get('DNI', '')}\n"
            f"NOMBRES ➾ {data.get('NOMBRES', '')}\n"
            f"APELLIDOS ➾ {data.get('APELLIDOS', '')}\n"
            f"GENERO ➾ {data.get('GENERO', '')}\n"
            f"EDAD ➾ {data.get('EDAD', '')}\n"
            f"ESTADO CIVIL ➾ {data.get('ESTADO_CIVIL', '')}\n"
            f"RESTRICCIÓN ➾ {data.get('RESTRICCION', '')}\n\n"
            f"[🎂] NACIMIENTO\n\n"
            f"FECHA NACIMIENTO ➾ {data.get('FECHA_NACIMIENTO', '')}\n"
            f"PADRE ➾ {data.get('PADRE', '')}\n"
            f"MADRE ➾ {data.get('MADRE', '')}\n\n"
            f"[📋] INFORMACIÓN GENERAL\n\n"
            f"FECHA INSCRIPCIÓN ➾ {data.get('FECHA_INSCRIPCION', '')}\n"
            f"FECHA EMISIÓN ➾ {data.get('FECHA_EMISION', '')}\n"
            f"FECHA CADUCIDAD ➾ {data.get('FECHA_CADUCIDAD', '')}\n"
            f"NIVEL EDUCATIVO ➾ {data.get('NIVEL_EDUCATIVO', '')}\n"
            f"ESTATURA ➾ {data.get('ESTATURA', '')}\n"
            f"DONANTE ÓRGANOS ➾ {data.get('DONANTE_ORGANOS', '')}\n\n"
            f"[🏠] DOMICILIO\n\n"
            f"DIRECCIÓN ➾ {data.get('DIRECCION', '')}\n"
            f"DISTRITO ➾ {data.get('DISTRITO', '')}\n"
            f"PROVINCIA ➾ {data.get('PROVINCIA', '')}\n"
            f"DEPARTAMENTO ➾ {data.get('DEPARTAMENTO', '')}\n\n"
            f"[📍] UBIGEOS\n\n"
            f"UBIGEO RENIEC ➾ {data.get('UBIGEO_RENIEC', '')}\n"
            f"UBIGEO INE ➾ {data.get('UBIGEO_INE', '')}\n"
            f"UBIGEO SUNAT ➾ {data.get('UBIGEO_SUNAT', '')}\n"
        )

        # 📸 Procesar imágenes primero
        images = result.get("images", [])
        media_group = []

        if images:
            for idx, img in enumerate(images[:4]):  # máximo 4 fotos
                photo_b64 = img.get("base64")
                if not photo_b64:
                    continue

                if photo_b64.startswith("data:image"):
                    _, encoded = photo_b64.split(",", 1)
                else:
                    encoded = photo_b64

                photo_bytes = base64.b64decode(encoded)
                bio = BytesIO(photo_bytes)
                bio.name = f"{dni_value}_{idx+1}.jpg"

                media_group.append(InputMediaPhoto(media=bio))

            await update.message.reply_media_group(
                media_group,
                reply_to_message_id=update.message.message_id
            )

        else:
            # 🔹 Si no hay "images" pero sí "photo_base64"
            photo_b64 = result.get("photo_base64")
            if photo_b64:
                if photo_b64.startswith("data:image"):
                    _, encoded = photo_b64.split(",", 1)
                else:
                    encoded = photo_b64

                photo_bytes = base64.b64decode(encoded)
                bio = BytesIO(photo_bytes)
                bio.name = f"{dni_value}.jpg"

                await update.message.reply_photo(
                    photo=InputFile(bio),
                    reply_to_message_id=update.message.message_id
                )

        # ✅ Después mandamos el texto
        await update.message.reply_text(
            mensaje,
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )

        await loading_message.delete()

    except Exception as e:
        await update.message.reply_text(
            f"❌ Error de conexion de consola",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        await loading_message.delete()

MAX_RESULTADOS_CHAT = 5  # solo para mostrar los primeros en el chat

import io

async def nm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # 🧩 Verificar argumentos
    if len(context.args) < 2:
        await update.message.reply_text(
            "❗ <b>Uso correcto:</b>\n"
            "/nm <code>Nombre Apellido1 [Apellido2]</code>\n"
            "Ejemplos:\n"
            "<code>/nm Juan Perez</code>\n"
            "<code>/nm Juan Perez Lopez</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # 🧩 Verificar créditos
    if not await verifica_creditos(update, user_id, 'reniec_nm'):
        return

    # 🧩 Cargar base de datos de usuarios (para créditos/usuario)
    username = "Desconocido"
    credits = "—"
    try:
        with open("users_db.json", "r", encoding="utf-8") as f:
            users_db = json.load(f)
        users = users_db.get("users", {})
        if str(user_id) in users:
            info = users[str(user_id)]
            username = info.get("username", "Desconocido")
            credits = info.get("credits", "—")
            if isinstance(credits, (int, float)):
                credits = int(credits) if credits == int(credits) else round(credits, 2)
    except Exception:
        pass

    # 🧩 Construir consulta (permite 2 o 3 palabras)
    if len(context.args) == 2:
        nombre1, apellido1 = context.args
        query = f"{nombre1}-{apellido1}"
    else:
        nombre1, apellido1, apellido2 = context.args[:3]
        query = f"{nombre1}-{apellido1}-{apellido2}"

    url = f"https://web-production-da283.up.railway.app/nom?nom={query}"

    # 🧩 Mensaje de carga
    loading_message = await update.message.reply_photo(
        photo="TRONCHITOBOT.png",
        caption=f"[⏳] PROCESANDO SOLICITUD POR NOMBRE: {query.replace('-', ' ')}...",
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )

    try:
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            await loading_message.delete()
            await update.message.reply_text(
                f"{EMOJIS['error']} Error {response.status_code} al consultar la API.",
                parse_mode="HTML",
                reply_to_message_id=update.message.message_id
            )
            return

        data = response.json()

        # ✅ Adaptar a estructura real
        resultados = []
        if isinstance(data, dict):
            contenido = data.get("data") or {}
            resultados = contenido.get("resultados") or []
            if isinstance(resultados, dict):
                resultados = [resultados]
        elif isinstance(data, list):
            resultados = data

        total_resultados = len(resultados)
        if total_resultados == 0:
            await loading_message.delete()
            await update.message.reply_text(
                f"{EMOJIS['error']} No se encontraron resultados para <b>{query.replace('-', ' ')}</b>.",
                parse_mode="HTML",
                reply_to_message_id=update.message.message_id
            )
            return

        # 🧩 Mostrar primeros resultados en el chat
        mensajes = []
        for i, persona in enumerate(resultados[:MAX_RESULTADOS_CHAT], start=1):
            mensajes.append(
                f"[#TRONCHITOBOT] ➾ RESULTADO {i}\n"
                    f"DNI: {persona.get('dni','N/A')}\n"
                    f"Nombres: {persona.get('nombres','N/A')}\n"
                    f"Apellido Paterno: {persona.get('apellidoPaterno','N/A')}\n"
                    f"Apellido Materno: {persona.get('apellidoMaterno','N/A')}\n"
                    f"Fecha Nacimiento: {persona.get('fechaNacimiento','N/A')}\n"
            )

        mensaje_chat = (
            f"🔍 <b>BÚSQUEDA POR NOMBRE</b>\n\n"
            f"🪪 <b>Consulta:</b> {query.replace('-', ' ')}\n\n"
            + "\n\n".join(mensajes)
            + f"\n\n📊 MOSTRANDO {min(MAX_RESULTADOS_CHAT, total_resultados)} DE {total_resultados} RESULTADOS.\n\n"
            f" ➤ {bold('Estado de Cuenta del Usuario')}\n\n"
            f"Créditos disponibles ➤ <code>{credits}</code>\n"
            f"ID de usuario ➤ <code>{user_id}</code>\n"
            f"Usuario ➤ <code>{username}</code>\n"
        )

        await update.message.reply_text(
            mensaje_chat,
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )

        # 🧩 Si hay más resultados (del 6 en adelante), generar un solo archivo TXT
        if total_resultados > MAX_RESULTADOS_CHAT:
            contenido_txt = ""
            for i, persona in enumerate(resultados[MAX_RESULTADOS_CHAT:], start=MAX_RESULTADOS_CHAT + 1):
                contenido_txt += (
                    f"[#TRONCHITOBOT] ➾ RESULTADO {i}\n"
                    f"DNI: {persona.get('dni','N/A')}\n"
                    f"Nombres: {persona.get('nombres','N/A')}\n"
                    f"Apellido Paterno: {persona.get('apellidoPaterno','N/A')}\n"
                    f"Apellido Materno: {persona.get('apellidoMaterno','N/A')}\n"
                    f"Fecha Nacimiento: {persona.get('fechaNacimiento','N/A')}\n"
                    f"{'-'*40}\n"
                )

            archivo = io.BytesIO(contenido_txt.encode("utf-8"))
            archivo.name = f"{query.replace('-', '_')} - RESULTADOS.txt"

            await update.message.reply_document(
                document=archivo,
                caption=f"📄 RESULTADOS RESTANTES ({total_resultados - MAX_RESULTADOS_CHAT} REGISTROS)",
                reply_to_message_id=update.message.message_id
            )

    except Exception as e:
        await update.message.reply_text(
            f"{EMOJIS['error']} Error de conexión o formato: {escape(str(e))}",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )

    finally:
        await loading_message.delete()

async def ag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # === 🧩 API CONFIGURADA ===
    API_URL = "https://web-production-da283.up.railway.app/arg"  # ✅ tu API final
    # ===========================

    # Validar argumentos
    if len(context.args) != 1:
        await update.message.reply_text(
            "❗<b>USO CORRECTO:</b>\n/arg <code>dni</code>\nEJEMPLO: <code>/arg 12345678</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # Leer base de usuarios
    try:
        with open("users_db.json", "r", encoding="utf-8") as f:
            users_db = json.load(f)
        users = users_db.get("users", {})
    except Exception:
        await update.message.reply_text("❌ Error al leer la base de datos.", parse_mode="HTML")
        return

    if str(user_id) not in users:
        await update.message.reply_text(
            "⚠️ No puedes usar este comando porque no estás registrado.\nUsa /register para poder registrarte.",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    user_info = users[str(user_id)]
    credits = user_info.get("credits", "—")
    username = user_info.get("username", "Desconocido")
    if isinstance(credits, (int, float)) and credits == int(credits):
        credits = int(credits)

    dni_value = context.args[0]

    loading_message = await update.message.reply_photo(
        photo="TRONCHITOBOT.png",
        caption="[⏳] PROCESANDO ÁRBOL GENEALÓGICO...",
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )

    try:
        # 🔗 Consumir la API
        url = f"{API_URL}?dni={dni_value}"
        resp = requests.get(url, timeout=40)

        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}")

        payload = resp.json() if resp.content else {}
        data = (payload or {}).get("data", {}) or {}

        # ---- Titular ----
        titular_dni = data.get("dni", "")
        titular_nombres = data.get("nombres", "")
        titular_apellidos = data.get("apellidos", "")
        arbol = data.get("arbol", []) or []

        # Campos extra del titular
        known_titular = {"dni", "nombres", "apellidos", "arbol"}
        extras_titular = {k: v for k, v in data.items() if k not in known_titular}

        # ---- Construir mensaje ----
        lineas = []
        lineas.append("[#TRONCHITOBOT] ➾ ÁRBOL GENEALÓGICO\n")

        # Datos del titular
        lineas.append("[👤] TITULAR")
        lineas.append(f"DNI ➾ <code>{titular_dni}</code>")
        lineas.append(f"NOMBRES ➾ {titular_nombres}")
        lineas.append(f"APELLIDOS ➾ {titular_apellidos}")

        # Extras si existen
        for k, v in extras_titular.items():
            lineas.append(f"{k.upper()} ➾ {v}")

        # Familiares
        lineas.append("\n[👨‍👩‍👧‍👦] FAMILIARES")
        if not arbol:
            lineas.append("No se encontraron familiares.")
        else:
            for i, fam in enumerate(arbol, start=1):
                fam_dni = fam.get("dni", "")
                fam_nom = fam.get("nombres", "")
                fam_ap_pat = fam.get("apellidoPaterno", "")
                fam_ap_mat = fam.get("apellidoMaterno", "")
                fam_edad = fam.get("edad", "")
                fam_sexo = fam.get("sexo", "")
                fam_tipo = fam.get("tipo", "")
                fam_ubigeo = fam.get("ubigeo", "")

                lineas.append(f"\n— Familiar #{i}")
                lineas.append(f"DNI ➾ <code>{fam_dni}</code>")
                lineas.append(f"NOMBRES ➾ {fam_nom}")
                lineas.append(f"AP. PATERNO ➾ {fam_ap_pat}")
                lineas.append(f"AP. MATERNO ➾ {fam_ap_mat}")
                lineas.append(f"EDAD ➾ {fam_edad}")
                lineas.append(f"SEXO ➾ {fam_sexo}")
                lineas.append(f"TIPO ➾ {fam_tipo}")
                lineas.append(f"UBIGEO ➾ {fam_ubigeo}")

                # Campos extra (por si la API envía más)
                known_fam = {
                    "dni", "nombres", "apellidoPaterno", "apellidoMaterno",
                    "edad", "sexo", "tipo", "ubigeo"
                }
                extras_fam = {k: v for k, v in fam.items() if k not in known_fam}
                for k, v in extras_fam.items():
                    lineas.append(f"{k.upper()} ➾ {v}")

        # Pie del mensaje
        lineas.append(" ➤  Estado de Cuenta del Usuario")
        lineas.append(f"Créditos disponibles ➤ <code>{credits}</code>")
        lineas.append(f"ID de usuario ➤ <code>{user_id}</code>")
        lineas.append(f"Usuario ➤ <code>{escape(username)}</code>")

        mensaje = "\n".join(lineas)

        await update.message.reply_text(
            mensaje,
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        await loading_message.delete()

    except Exception as e:
        try:
            await loading_message.delete()
        except:
            pass
        await update.message.reply_text(
            f"❌ ERROR AL PROCESAR: {e}",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )  
        
# ================== HELPERS ==================
INVALID_FECHA_RE = re.compile(r"fecha inválida", re.IGNORECASE)

def _b64_to_image(b64_str):
    """Convierte base64 en imagen PIL (RGBA)"""
    if not b64_str:
        return None
    try:
        encoded = b64_str.split(",", 1)[1] if str(b64_str).startswith("data:image") else b64_str
        raw = base64.b64decode(encoded)
        return Image.open(BytesIO(raw)).convert("RGBA")
    except Exception:
        return None

def _font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()

def _rounded(draw, box, r, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)

def _wrap(draw, text, font, max_w, max_lines):
    s = str(text or "").strip()
    if not s:
        return []
    s = re.sub(r"([-–—/])", r" \1 ", s)
    words = s.split()
    lines, cur = [], ""
    def fits(t):
        try:
            return draw.textlength(t, font=font) <= max_w
        except Exception:
            x0, y0, x1, y1 = draw.textbbox((0, 0), t, font=font)
            return (x1 - x0) <= max_w
    i = 0
    while i < len(words):
        w = words[i]
        candidate = (cur + " " + w).strip() if cur else w
        if fits(candidate):
            cur = candidate
            i += 1
            continue
        if not cur:
            piece = ""
            for ch in w:
                if fits(piece + ch): piece += ch
                else: break
            if piece:
                lines.append(piece)
                words[i] = w[len(piece):]
            else:
                lines.append(w)
                i += 1
        else:
            lines.append(cur)
            cur = ""
        if len(lines) >= max_lines:
            cur = ""
            break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    original = " ".join(words)
    shown = " ".join(lines)
    if len(lines) >= max_lines and original != shown:
        while lines and fits(lines[-1] + "…") and draw.textlength(lines[-1] + "…", font=font) > max_w and lines[-1]:
            lines[-1] = lines[-1][:-1]
        if lines and draw.textlength(lines[-1] + "…", font=font) <= max_w:
            lines[-1] = (lines[-1] + "…") if lines[-1] else "…"
    return lines

def _hgrad(w, h, c1, c2):
    base = Image.new("RGBA", (w, h), c1)
    top  = Image.new("RGBA", (w, h), c2)
    mask = Image.linear_gradient("L").resize((w, 1)).resize((w, h))
    return Image.composite(top, base, mask)

def _san(v, default="N/A"):
    if v is None: return default
    s = str(v).strip()
    if not s or s in {"-", "--"} or INVALID_FECHA_RE.search(s): return default
    return s

def _san_edad(edad):
    s = _san(edad, "")
    if s == "N/A": return s
    return s if s.isdigit() else "N/A"

# === Composición sin alpha_composite, usando paste + máscara ===
def _acompose(bg: Image.Image, im: Image.Image, pos):
    """
    Pega 'im' (con alfa) sobre 'bg' en 'pos' usando paste(..., mask=im).
    Modifica 'bg' IN-PLACE; devuelve 'bg' por comodidad.
    """
    if im is None:
        return bg
    if bg.mode != "RGBA":
        bg = bg.convert("RGBA")
    im = im.convert("RGBA")
    bg.paste(im, pos, im)  # usa el propio canal alfa como máscara
    return bg

# === Cache de fotos + retries + placeholder ===
_IMG_CACHE = {}

def _load_placeholder(size):
    """Genera un placeholder sencillo si no tienes una imagen local."""
    w, h = size
    im = Image.new("RGBA", (w, h), (245, 246, 248, 255))
    d = ImageDraw.Draw(im)
    f = _font(14)
    msg = "No hay foto\ndisponible"
    tw = d.textlength("No hay foto", font=f)
    d.multiline_text(((w - tw)/2 - 10, h/2 - 18), msg, fill=(120,120,130,255), font=f, align="center")
    return im

def _fetch_foto(dni, foto_api_url, size, session=None, timeout=12, retries=3):
    """
    Pide la foto a la API con pequeños reintentos y cache.
    Devuelve PIL.Image (RGBA) del tamaño solicitado o None si la API no trae foto.
    """
    dni = str(dni or "").strip()
    if not dni or dni == "N/A":
        return None

    key = (dni, size)
    if key in _IMG_CACHE:
        return _IMG_CACHE[key]

    sess = session or requests.Session()
    url = f"{foto_api_url}?dni={dni}"

    img = None
    for attempt in range(retries):
        try:
            r = sess.get(url, timeout=timeout)
            if r.status_code == 200:
                b64 = (r.json().get("data") or {}).get("foto")
                tmp = _b64_to_image(b64)  # ya convierte a RGBA
                if tmp:
                    img = tmp.resize(size)
                    break
        except Exception:
            pass
        time.sleep(0.25 * (attempt + 1))  # backoff suave

    _IMG_CACHE[key] = img  # cachea incluso None para evitar repetir fallos
    return img

# ================== HANDLER: /agv ==================
async def agv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ARG_API  = "https://web-production-da283.up.railway.app/arg"
    FOTO_API = "https://web-production-da283.up.railway.app/foto"

    if len(context.args) != 1:
        await update.message.reply_text(
            "❗<b>USO CORRECTO:</b>\n/agv <code>dni</code>\nEJEMPLO: <code>/agv 12345678</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # Cargar base de datos de usuarios
    try:
        with open("users_db.json", "r", encoding="utf-8") as f:
            users_db = json.load(f)
        users = users_db.get("users", {})
    except Exception:
        await update.message.reply_text("❌ Error al leer la base de datos.", parse_mode="HTML",
                                        reply_to_message_id=update.message.message_id)
        return

    if str(user_id) not in users:
        await update.message.reply_text(
            "⚠️ No puedes usar este comando porque no estás registrado.\nUsa /register para poder registrarte.",
            parse_mode="HTML", reply_to_message_id=update.message.message_id
        )
        return

    info = users[str(user_id)]
    credits = info.get("credits", "—")
    if isinstance(credits, (int, float)) and credits == int(credits):
        credits = int(credits)
    username = info.get("username", "Desconocido")
    dni_value = context.args[0]

    loading = await update.message.reply_photo(
        photo="TRONCHITOBOT.png",
        caption="[⏳] GENERANDO ÁRBOL GENEALÓGICO VISUAL...",
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )

    # Reutiliza una sesión HTTP
    SESSION = requests.Session()
    SESSION.headers.update({"User-Agent": "TRONCHITOBOT/1.0"})

    try:
        # --- API familia ---
        fam_r = SESSION.get(f"{ARG_API}?dni={dni_value}", timeout=40)
        fam_r.raise_for_status()
        fam_data = (fam_r.json() or {}).get("data", {}) or {}
        titular_dni = _san(fam_data.get("dni", dni_value))
        titular_nom = _san(fam_data.get("nombres", ""))
        titular_ape = _san(fam_data.get("apellidos", ""))
        familiares  = fam_data.get("arbol", []) or []

        # ======== LAYOUT ========
        CANVAS_W = 1800
        RIGHT_W  = 460
        MARGIN   = 26
        LEFT_W   = CANVAS_W - RIGHT_W - 2*MARGIN
        PAD      = 22
        EXTRA_TOP_CLEARANCE = 10
        CARD_W, CARD_H = 150, 150
        FAMILY_TEXT_AREA_H = 121
        GRID_GX, GRID_GY = 26, 60
        TEXT_W  = CARD_W

        # Placeholders
        FAM_PH = _load_placeholder((CARD_W, CARD_H))
        TIT_PH = _load_placeholder((200, 200))

        possible_cols = (LEFT_W - 2*PAD + GRID_GX) // (CARD_W + GRID_GX)
        COLS = max(6, min(10, int(possible_cols)))
        rows = max(1, math.ceil(len(familiares)/COLS))
        grid_bottom = PAD + EXTRA_TOP_CLEARANCE + rows*(CARD_H + FAMILY_TEXT_AREA_H + GRID_GY)
        BASE_H = max(1120, grid_bottom + 220)

        # Fondo degradado
        bg = _hgrad(CANVAS_W, BASE_H, (12, 24, 52, 255), (22, 40, 80, 255))
        if bg.mode != "RGBA":
            bg = bg.convert("RGBA")
        draw = ImageDraw.Draw(bg)

        # Panel izquierdo
        left_box = (MARGIN, MARGIN, MARGIN + LEFT_W, BASE_H - MARGIN)
        _rounded(draw, left_box, 18, fill=(250, 250, 252, 255), outline=(230, 233, 240, 255), width=2)

        # Panel derecho
        right = _hgrad(RIGHT_W, BASE_H, (8, 18, 44, 255), (16, 52, 120, 255))
        bg = _acompose(bg, right, (CANVAS_W - RIGHT_W, 0))
        draw = ImageDraw.Draw(bg)

        f_title = _font(36); f_tag = _font(12); f_text = _font(15); f_small = _font(10)
        draw.text((CANVAS_W - RIGHT_W + 36, 44), "ÁRBOL GENEALÓGICO\nVISUAL", fill="white", font=f_title)

        # Tarjeta titular
        card_x = CANVAS_W - RIGHT_W + 42
        card_y = 154
        card_w, card_h = 340, 500

        sombra = Image.new("RGBA", (card_w+10, card_h+10), (0,0,0,0))
        ImageDraw.Draw(sombra).rounded_rectangle((5,5,card_w,card_h), 24, fill=(0,0,0,70))
        bg = _acompose(bg, sombra, (card_x+5, card_y+5))
        draw = ImageDraw.Draw(bg)

        _rounded(draw, (card_x, card_y, card_x + card_w, card_y + card_h), 22, fill=(255,255,255,255))

        PH = 200
        ppos = (card_x + (card_w - PH)//2, card_y + 28)

        # Foto titular (con retries/cache) o placeholder
        foto_tit = _fetch_foto(titular_dni, FOTO_API, (PH, PH), session=SESSION, timeout=18, retries=3)
        tit_to_draw = foto_tit if foto_tit is not None else TIT_PH
        bg = _acompose(bg, tit_to_draw, ppos)
        draw = ImageDraw.Draw(bg)

        tx, ty = card_x + 22, ppos[1] + PH + 22
        draw.text((tx, ty), "PERSONA PRINCIPAL", fill=(36, 180, 120, 255), font=_font(20)); ty += 30
        for s in [titular_dni, titular_nom.upper(), titular_ape.upper()]:
            for line in _wrap(draw, s, f_text, card_w - 44, 2):
                draw.text((tx, ty), line, fill=(28,28,28,255), font=f_text); ty += 24

        # Cuadro de total familiares
        tot_box = (card_x, card_y + card_h + 28, card_x + card_w, card_y + card_h + 80)
        _rounded(draw, tot_box, 16, fill=(255,255,255,255))
        draw.text((tot_box[0] + 20, tot_box[1] + 14),
                  f"Total Familiares: {len(familiares)}",
                  fill=(26,26,26,255), font=_font(20))

        # Marca de agua
        wm_text = "@TRONCHITOBOT"
        wm_font = _font(28)
        wm_x = card_x + 60
        wm_y = tot_box[3] + 10
        draw.text((wm_x, wm_y), wm_text, fill=(255,255,255,90), font=wm_font)

        # Grilla familiares
        start_x = MARGIN + PAD
        start_y = MARGIN + PAD + EXTRA_TOP_CLEARANCE
        for i, fam in enumerate(familiares):
            c = i % COLS
            r = i // COLS
            x = start_x + c*(CARD_W + GRID_GX)
            y = start_y + r*(CARD_H + FAMILY_TEXT_AREA_H + GRID_GY)

            _rounded(draw, (x-6, y-6, x + CARD_W + 6, y + CARD_H + FAMILY_TEXT_AREA_H + 6),
                     14, fill=(255,255,255,235), outline=(220,223,230,255), width=2)

            fam_dni = _san(fam.get("dni", ""))

            # Foto familiar con cache + retries; si None, usa placeholder
            fam_img = _fetch_foto(fam_dni, FOTO_API, (CARD_W, CARD_H), session=SESSION, timeout=12, retries=3)
            if fam_img is None:
                fam_img = FAM_PH
            bg = _acompose(bg, fam_img, (x, y))
            draw = ImageDraw.Draw(bg)

            nom   = _san(fam.get("nombres",""))
            ap_pa = _san(fam.get("apellidoPaterno",""))
            ap_ma = _san(fam.get("apellidoMaterno",""))
            sexo  = _san(fam.get("sexo",""))
            tipo  = _san(fam.get("tipo",""))
            edad  = _san_edad(fam.get("edad",""))
            ubig  = _san(fam.get("ubigeo",""))

            ty2 = y + CARD_H + 6
            for line in _wrap(draw, tipo.upper(), f_tag, TEXT_W, 1):
                draw.text((x, ty2), line, fill=(180,30,30,255), font=f_tag)
                ty2 += 16

            blocks = [
                (fam_dni, 1),
                (nom.upper(), 1),
                ((ap_pa + " " + ap_ma).strip().upper(), 2),
                (((sexo.upper() if sexo != "N/A" else "N/A") +
                  (f" — {edad} AÑOS" if edad not in ("", "N/A") else "")), 1),
                (ubig.upper(), 3),
            ]
            for txt, ml in blocks:
                if not txt: continue
                for line in _wrap(draw, txt, f_small, TEXT_W, ml):
                    draw.text((x, ty2), line, fill=(40,40,40,255), font=f_small)
                    ty2 += 16

        # ================== SALIDA COMO ARCHIVO (JPG) ==================
        jpg_io = BytesIO()
        rgb_bg = bg.convert("RGB")
        rgb_bg.save(jpg_io, format="JPEG", quality=90, optimize=True, progressive=True)
        jpg_io.seek(0)
        jpg_io.name = f"ARBOL GENEALOGICO - {dni_value}.jpg"

        caption = (
            f"[#TRONCHITOBOT] ➾ SISFOH X DNI\n\n"
            f"<b>TITULAR:</b> {titular_nom} {titular_ape}\n"
            f"<b>DNI:</b> <code>{titular_dni}</code>\n"
            f"<b>Total familiares:</b> {len(familiares)}\n\n"
            f" ➤ {bold('Estado de Cuenta del Usuario')}\n\n"
            f"Créditos disponibles ➤ <code>{credits}</code>\n"
            f"ID de usuario ➤ <code>{user_id}</code>\n"
            f"Usuario ➤ <code>{username}</code>\n"
        )

        await update.message.reply_document(
            document=InputFile(jpg_io),
            caption=caption,
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        await loading.delete()

    except Exception as e:
        try:
            await loading.delete()
        except:
            pass
        await update.message.reply_text(
            f"❌ ERROR AL PROCESAR CONSULTE DENUEVO EL DNI",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )

# ----------------- HANDLER -----------------
async def agvp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ARG_API  = "https://web-production-da283.up.railway.app/arg"
    FOTO_API = "https://web-production-da283.up.railway.app/foto"

    if len(context.args) != 1:
        await update.message.reply_text(
            "❗<b>USO CORRECTO:</b>\n/agvp <code>dni</code>\nEJEMPLO: <code>/agvp 12345678</code>",
            parse_mode="HTML", reply_to_message_id=update.message.message_id
        )
        return

    # Cargar base de datos
    try:
        with open("users_db.json", "r", encoding="utf-8") as f:
            users_db = json.load(f)
        users = users_db.get("users", {})
    except Exception:
        await update.message.reply_text("❌ Error al leer la base de datos.", parse_mode="HTML")
        return

    if str(user_id) not in users:
        await update.message.reply_text(
            "⚠️ No puedes usar este comando porque no estás registrado.\nUsa /register para poder registrarte.",
            parse_mode="HTML", reply_to_message_id=update.message.message_id
        )
        return

    info = users[str(user_id)]
    credits = info.get("credits", "—")
    if isinstance(credits, (int, float)) and credits == int(credits):
        credits = int(credits)
    username = info.get("username", "Desconocido")
    dni_value = context.args[0]

    loading = await update.message.reply_photo(
        photo="TRONCHITOBOT.png",
        caption="[⏳] GENERANDO ÁRBOL GENEALÓGICO VISUAL (PDF)...",
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )

    # Sesión HTTP compartida (igual que /agv)
    SESSION = requests.Session()
    SESSION.headers.update({"User-Agent": "TRONCHITOBOT/1.0"})

    try:
        # === API familia ===
        fam_r = SESSION.get(f"{ARG_API}?dni={dni_value}", timeout=40)
        fam_r.raise_for_status()
        fam_data = (fam_r.json() or {}).get("data", {}) or {}
        titular_dni = _san(fam_data.get("dni", dni_value))
        titular_nom = _san(fam_data.get("nombres", ""))
        titular_ape = _san(fam_data.get("apellidos", ""))
        familiares  = fam_data.get("arbol", []) or []

        # ======== LAYOUT (idéntico a /agv) ========
        CANVAS_W = 1800
        RIGHT_W  = 460
        MARGIN   = 26
        LEFT_W   = CANVAS_W - RIGHT_W - 2*MARGIN
        PAD      = 22
        EXTRA_TOP_CLEARANCE = 10
        CARD_W, CARD_H = 150, 150
        FAMILY_TEXT_AREA_H = 121
        GRID_GX, GRID_GY = 26, 60
        TEXT_W  = CARD_W

        # Placeholders (idénticos a /agv)
        FAM_PH = _load_placeholder((CARD_W, CARD_H))
        TIT_PH = _load_placeholder((200, 200))

        possible_cols = (LEFT_W - 2*PAD + GRID_GX) // (CARD_W + GRID_GX)
        COLS = max(6, min(10, int(possible_cols)))
        rows = max(1, math.ceil(len(familiares)/COLS))
        grid_bottom = PAD + EXTRA_TOP_CLEARANCE + rows*(CARD_H + FAMILY_TEXT_AREA_H + GRID_GY)
        BASE_H = max(1120, grid_bottom + 220)

        # Fondo degradado y paneles
        bg = _hgrad(CANVAS_W, BASE_H, (12, 24, 52, 255), (22, 40, 80, 255))
        if bg.mode != "RGBA":
            bg = bg.convert("RGBA")
        draw = ImageDraw.Draw(bg)

        left_box = (MARGIN, MARGIN, MARGIN + LEFT_W, BASE_H - MARGIN)
        _rounded(draw, left_box, 18, fill=(250, 250, 252, 255), outline=(230, 233, 240, 255), width=2)

        right = _hgrad(RIGHT_W, BASE_H, (8, 18, 44, 255), (16, 52, 120, 255))
        bg = _acompose(bg, right, (CANVAS_W - RIGHT_W, 0))
        draw = ImageDraw.Draw(bg)

        f_title = _font(36); f_tag = _font(12); f_text = _font(15); f_small = _font(10)
        draw.text((CANVAS_W - RIGHT_W + 36, 44), "ÁRBOL GENEALÓGICO\nVISUAL", fill="white", font=f_title)

        # Tarjeta titular (usa _fetch_foto como /agv)
        card_x = CANVAS_W - RIGHT_W + 42
        card_y = 154
        card_w, card_h = 340, 500

        sombra = Image.new("RGBA", (card_w+10, card_h+10), (0,0,0,0))
        ImageDraw.Draw(sombra).rounded_rectangle((5,5,card_w,card_h), 24, fill=(0,0,0,70))
        bg = _acompose(bg, sombra, (card_x+5, card_y+5))
        draw = ImageDraw.Draw(bg)

        _rounded(draw, (card_x, card_y, card_x + card_w, card_y + card_h), 22, fill=(255,255,255,255))

        PH = 200
        ppos = (card_x + (card_w - PH)//2, card_y + 28)

        foto_tit = _fetch_foto(titular_dni, FOTO_API, (PH, PH), session=SESSION, timeout=18, retries=3)
        tit_to_draw = foto_tit if foto_tit is not None else TIT_PH
        bg = _acompose(bg, tit_to_draw, ppos)
        draw = ImageDraw.Draw(bg)

        tx, ty = card_x + 22, ppos[1] + PH + 22
        draw.text((tx, ty), "PERSONA PRINCIPAL", fill=(36, 180, 120, 255), font=_font(20)); ty += 30
        for s in [titular_dni, titular_nom.upper(), titular_ape.upper()]:
            for line in _wrap(draw, s, f_text, card_w - 44, 2):
                draw.text((tx, ty), line, fill=(28,28,28,255), font=f_text); ty += 24

        # Total familiares + marca de agua
        tot_box = (card_x, card_y + card_h + 28, card_x + card_w, card_y + card_h + 80)
        _rounded(draw, tot_box, 16, fill=(255,255,255,255))
        draw.text((tot_box[0] + 20, tot_box[1] + 14),
                  f"Total Familiares: {len(familiares)}",
                  fill=(26,26,26,255), font=_font(20))

        wm_text = "@TRONCHITOBOT"
        wm_font = _font(28)
        wm_x = card_x + 60
        wm_y = tot_box[3] + 10
        draw.text((wm_x, wm_y), wm_text, fill=(255,255,255,90), font=wm_font)

        # Grilla de familiares (idéntica a /agv: _fetch_foto + placeholder)
        start_x = MARGIN + PAD
        start_y = MARGIN + PAD + EXTRA_TOP_CLEARANCE
        for i, fam in enumerate(familiares):
            c = i % COLS
            r = i // COLS
            x = start_x + c*(CARD_W + GRID_GX)
            y = start_y + r*(CARD_H + FAMILY_TEXT_AREA_H + GRID_GY)

            _rounded(draw, (x-6, y-6, x + CARD_W + 6, y + CARD_H + FAMILY_TEXT_AREA_H + 6),
                     14, fill=(255,255,255,235), outline=(220,223,230,255), width=2)

            fam_dni = _san(fam.get("dni", ""))

            fam_img = _fetch_foto(fam_dni, FOTO_API, (CARD_W, CARD_H), session=SESSION, timeout=12, retries=3)
            if fam_img is None:
                fam_img = FAM_PH
            bg = _acompose(bg, fam_img, (x, y))
            draw = ImageDraw.Draw(bg)

            nom   = _san(fam.get("nombres",""))
            ap_pa = _san(fam.get("apellidoPaterno",""))
            ap_ma = _san(fam.get("apellidoMaterno",""))
            sexo  = _san(fam.get("sexo",""))
            tipo  = _san(fam.get("tipo",""))
            edad  = _san_edad(fam.get("edad",""))
            ubig  = _san(fam.get("ubigeo",""))

            ty2 = y + CARD_H + 6
            for line in _wrap(draw, tipo.upper(), f_tag, TEXT_W, 1):
                draw.text((x, ty2), line, fill=(180,30,30,255), font=f_tag)
                ty2 += 16

            blocks = [
                (fam_dni, 1),
                (nom.upper(), 1),
                ((ap_pa + " " + ap_ma).strip().upper(), 2),
                (((sexo.upper() if sexo != "N/A" else "N/A") +
                  (f" — {edad} AÑOS" if edad not in ("", "N/A") else "")), 1),
                (ubig.upper(), 3),
            ]
            for txt, ml in blocks:
                if not txt: continue
                for line in _wrap(draw, txt, _font(10), TEXT_W, ml):
                    draw.text((x, ty2), line, fill=(40,40,40,255), font=_font(10))
                    ty2 += 16

        # === Exportar a PDF (misma imagen renderizada) ===
        pdf_bytes = BytesIO()
        rgb_bg = bg.convert("RGB")
        rgb_bg.save(pdf_bytes, format="PDF")
        pdf_bytes.seek(0)
        pdf_bytes.name = f"ARBOL GENEALOGICO - {dni_value}.pdf"

        caption = (
            f"[#TRONCHITOBOT] ➾ ÁRBOL GENEALÓGICO VISUAL (PDF)\n\n"
            f"<b>TITULAR:</b> {titular_nom} {titular_ape}\n"
            f"<b>DNI:</b> <code>{titular_dni}</code>\n"
            f"<b>Total familiares:</b> {len(familiares)}\n\n"
            f" ➤ {bold('Estado de Cuenta del Usuario')}\n\n"
            f"Créditos disponibles ➤ <code>{credits}</code>\n"
            f"ID de usuario ➤ <code>{user_id}</code>\n"
            f"Usuario ➤ <code>{username}</code>\n"
        )

        await update.message.reply_document(
            document=InputFile(pdf_bytes),
            caption=caption,
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        await loading.delete()

    except Exception as e:
        try:
            await loading.delete()
        except:
            pass
        await update.message.reply_text(
            f"❌ ERROR AL PROCESAR PDF: {e}",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )

# 🔧 Limpieza de campos
def safe_field(value: str) -> str:
    """
    Devuelve un valor limpio y legible.
    Convierte vacíos, '/', '\\r)', 'null', etc. en 'N/A'.
    """
    if not value:
        return "N/A"
    v = str(value).strip().replace("\\r", "").replace("\\n", "")
    if v in ["", "/", "null", "None", "Ninguno", "NINGUNA", "\\r)", "r)", ")"]:
        return "N/A"
    return v

# 🧩 Limpia y separa titulares extraños
def formatea_titulares(raw: str) -> str:
    """
    Intenta extraer nombres desde un string de titulares tipo:
    "''GOMEZ GONZALES'JOSEPH'GOMEZ SICCHA'JOSEPH ALEJANDRO'SICCHA MACASSI'LUPE ELIZABETH''"
    """
    if not raw:
        return "No registrado"
    texto = raw.strip("' ").replace("''", "'")
    partes = re.split(r"'+", texto)
    nombres = [p.strip() for p in partes if p.strip()]
    if not nombres:
        return "No registrado"
    return "\n".join([f"• {n}" for n in nombres])

async def placa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # 1) Validación de argumentos
    if len(context.args) != 1:
        await update.message.reply_text(
            "❗ <b>Uso correcto:</b>\n"
            "/placa <code>placa</code>\n"
            "Ejemplo: <code>/placa ABC123</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    placa_raw = context.args[0].strip().upper()
    placa = re.sub(r"[\s\-]+", "", placa_raw)
    if not re.fullmatch(r"[A-Z0-9]{5,8}", placa):
        await update.message.reply_text(
            "La placa ingresada no es válida.",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # 2) Verificar créditos
    if not await verifica_creditos(update, user_id, 'vehiculos_placa'):
        return

    # 3) Cargar datos de usuario
    username = "Desconocido"
    credits = "—"
    try:
        with open("users_db.json", "r", encoding="utf-8") as f:
            users_db = json.load(f)
        users = users_db.get("users", {})
        if str(user_id) in users:
            user_info = users[str(user_id)]
            username = user_info.get("username", "Desconocido")
            credits = user_info.get("credits", "—")
            if isinstance(credits, (int, float)):
                credits = int(credits) if credits == int(credits) else round(credits, 2)
    except Exception:
        pass

    # 4) Mensaje de carga
    loading_message = await update.message.reply_photo(
        photo="TRONCHITOBOT.png",
        caption="Procesando solicitud en SUNARP...",
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )

    # 5) Llamada a la API SUNARP
    url = f"https://sunarp-api.onrender.com/placa/{placa}"
    timeout = aiohttp.ClientTimeout(total=15, connect=5, sock_read=10)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await update.message.reply_text(
                        f"No se pudieron obtener datos (HTTP {resp.status}).",
                        parse_mode="HTML",
                        reply_to_message_id=update.message.message_id
                    )
                    return
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    await update.message.reply_text(
                        "La respuesta del servidor no es válida.",
                        parse_mode="HTML",
                        reply_to_message_id=update.message.message_id
                    )
                    return

        if not data:
            await update.message.reply_text(
                "No se encontraron datos para la placa ingresada.",
                parse_mode="HTML",
                reply_to_message_id=update.message.message_id
            )
            return

        # 6) Construir mensaje mejorado
        mensaje = (
            f"{bold('[#TRONCHITOBOT] ➾ CONSULTA SUNARP POR PLACA')}\n\n"
    
            f"{bold('🧾 INFORMACIÓN GENERAL DEL VEHÍCULO')}\n"
            f"{italic('──────────────────────────────')}\n"
            f"{bold('Placa:')} <code>{safe_field(data.get('placa'))}</code>\n"
            f"{bold('Registro:')} {safe_field(data.get('nro_registro'))}\n"
            f"{bold('Sede N°:')} {safe_field(data.get('nro_sede'))}\n"
            f"{bold('Color:')} {safe_field(data.get('color'))}\n"
            f"{bold('Estado:')} {safe_field(data.get('estado'))}\n"
            f"{bold('Marca:')} {safe_field(data.get('marca'))}\n"
            f"{bold('Modelo:')} {safe_field(data.get('modelo'))}\n"
            f"{bold('Motor:')} {safe_field(data.get('motor'))}\n"
            f"{bold('Serie:')} {safe_field(data.get('serie'))}\n"
            f"{bold('VIN:')} {safe_field(data.get('vin'))}\n"
            f"{bold('Placa anterior:')} {safe_field(data.get('anterior'))}\n"
            f"{bold('Vidente:')} {safe_field(data.get('vidente'))}\n\n"

            f"{bold('📑 PROPIEDAD Y REGISTRO')}\n"
            f"{italic('──────────────────────────────')}\n"
            f"{bold('Propietario(s):')}\n{formatea_titulares(data.get('titulares'))}\n"
            f"{bold('Total de titulares:')} {safe_field(data.get('nro_titulares'))}\n"
            f"{bold('Sede actual:')} {safe_field(data.get('sede'))}\n"
            f"{bold('Tarjeta:')} <code>{safe_field(data.get('tarjeta'))}</code>\n"
            f"{bold('Titular principal:')} {safe_field(data.get('titular'))}\n"
            f"{bold('Oficina:')} {safe_field(data.get('oficina'))}\n"
            f"{bold('Creado el:')} {safe_field(data.get('creado'))}\n"
            f"{bold('Última actualización:')} {safe_field(data.get('actualizado'))}\n\n"

            f"{bold('📂 HISTORIAL Y ESTADO')}\n"
            f"{italic('──────────────────────────────')}\n"
            f"{bold('Deuda de papeletas:')} {safe_field(data.get('deuda_papeletas'))}\n"
            f"{bold('N° de papeletas:')} {safe_field(data.get('nro_papeletas'))}\n"
            f"{bold('SOAT(s):')} {safe_field(data.get('soats'))}\n"
            f"{bold('Año de fabricación:')} {safe_field(data.get('fabricacion'))}\n\n"

            f"{bold('➤  ESTADO DE CUENTA')}\n"
            f"{italic('──────────────────────────────')}\n"
            f"{bold('Créditos disponibles ➤ ')} <code>{credits}</code>\n"
            f"{bold('ID de usuario ➤ ')} <code>{user_id}</code>\n"
            f"{bold('Usuario ➤ ')} {username}\n"
        )

        # 7) Envío del resultado
        await update.message.reply_text(
            mensaje,
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )

    except asyncio.TimeoutError:
        await update.message.reply_text(
            "El servicio tardó demasiado en responder. Inténtalo nuevamente.",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
    except aiohttp.ClientError as ce:
        await update.message.reply_text(
            f"Error de conexión: {str(ce)}",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
    except Exception:
        await update.message.reply_text(
            "Ocurrió un error inesperado al procesar la solicitud.",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
    finally:
        try:
            await loading_message.delete()
        except Exception:
            pass

# 🔧 Limpieza de campos
def safe_field(value: str) -> str:
    """
    Devuelve un valor limpio y legible.
    Convierte vacíos, '/', '\\r)', 'null', etc. en 'N/A'.
    """
    if not value:
        return "N/A"
    v = str(value).strip().replace("\\r", "").replace("\\n", "")
    if v in ["", "/", "null", "None", "Ninguno", "NINGUNA", "\\r)", "r)", ")"]:
        return "N/A"
    return v

# 🧩 Limpia y separa titulares extraños
def formatea_titulares(raw: str) -> str:
    """
    Intenta extraer nombres desde un string de titulares tipo:
    "''GOMEZ GONZALES'JOSEPH'GOMEZ SICCHA'JOSEPH ALEJANDRO'SICCHA MACASSI'LUPE ELIZABETH''"
    """
    if not raw:
        return "No registrado"
    texto = raw.strip("' ").replace("''", "'")
    partes = re.split(r"'+", texto)
    nombres = [p.strip() for p in partes if p.strip()]
    if not nombres:
        return "No registrado"
    return "\n".join([f"• {n}" for n in nombres])

async def taj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # 1) Validación de argumentos
    if len(context.args) != 1:
        await update.message.reply_text(
            "❗ <b>Uso correcto:</b>\n"
            "/taj <code>nro_tarjeta</code>\n"
            "Ejemplo: <code>/taj 1234567</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    tarjeta = re.sub(r"\s+", "", context.args[0])
    if not re.fullmatch(r"\d{5,12}", tarjeta):
        await update.message.reply_text(
            "El número de tarjeta no es válido.",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # 2) Verificar créditos
    if not await verifica_creditos(update, user_id, 'vehiculos_tarjeta'):
        return

    # 3) Datos de usuario para Estado de Cuenta
    username = "Desconocido"
    credits = "—"
    try:
        with open("users_db.json", "r", encoding="utf-8") as f:
            users_db = json.load(f)
        users = users_db.get("users", {})
        if str(user_id) in users:
            user_info = users[str(user_id)]
            username = user_info.get("username", "Desconocido")
            credits = user_info.get("credits", "—")
            if isinstance(credits, (int, float)):
                credits = int(credits) if credits == int(credits) else round(credits, 2)
    except Exception:
        pass

    # 4) Mensaje de carga
    loading_message = await update.message.reply_photo(
        photo="TRONCHITOBOT.png",
        caption="Procesando solicitud en SUNARP...",
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )

    # 5) Llamada HTTP con aiohttp
    url = f"https://sunarp-api.onrender.com/tarjeta/{tarjeta}"
    timeout = aiohttp.ClientTimeout(total=20, connect=5, sock_read=12)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await update.message.reply_text(
                        f"No se pudieron obtener datos (HTTP {resp.status}).",
                        parse_mode="HTML",
                        reply_to_message_id=update.message.message_id
                    )
                    return
                try:
                    payload = await resp.json(content_type=None)
                except Exception:
                    await update.message.reply_text(
                        "La respuesta del servidor no es válida.",
                        parse_mode="HTML",
                        reply_to_message_id=update.message.message_id
                    )
                    return

        vehiculos = payload.get("data", []) if isinstance(payload, dict) else []
        if not (isinstance(vehiculos, list) and vehiculos):
            await update.message.reply_text(
                "No se encontraron registros para la tarjeta ingresada.",
                parse_mode="HTML",
                reply_to_message_id=update.message.message_id
            )
            return

        # 6) Mensaje moderno (sin emojis, secciones claras)
        mensaje = f"{bold('[#TRONCHITOBOT] ➾ CONSULTA SUNARP POR TARJETA')}\n\n"

        for idx, v in enumerate(vehiculos, 1):
            placa       = safe_field(v.get('placa'))
            nro_reg     = safe_field(v.get('nro_registro'))
            color       = safe_field(v.get('color'))
            estado      = safe_field(v.get('estado'))
            marca       = safe_field(v.get('marca'))
            modelo      = safe_field(v.get('modelo'))
            motor       = safe_field(v.get('motor'))
            serie       = safe_field(v.get('serie'))
            vin         = safe_field(v.get('vin'))
            anterior    = safe_field(v.get('anterior'))
            titulares   = formatea_titulares(v.get('titulares'))
            nro_tits    = safe_field(v.get('nro_titulares'))
            nro_sede    = safe_field(v.get('nro_sede'))
            nro_taj     = safe_field(v.get('tarjeta'))
            oficina     = safe_field(v.get('oficina'))
            creado      = safe_field(v.get('creado'))
            actualizado = safe_field(v.get('actualizado'))
            deuda       = safe_field(v.get('deuda_papeletas'))
            nro_pap     = safe_field(v.get('nro_papeletas'))
            soats       = safe_field(v.get('soats'))

            mensaje += (
                f"{bold(f'『 RESULTADO #{idx} 』')}\n"
                f"{bold('PLACA:')} <code>{placa}</code>\n\n"

                f"{bold('🧾 INFORMACIÓN DEL VEHÍCULO')}\n"
                f"{italic('──────────────────────────────')}\n"
                f"{bold('Registro:')} {nro_reg}\n"
                f"{bold('Color:')} {color}\n"
                f"{bold('Estado:')} {estado}\n"
                f"{bold('Marca:')} {marca}\n"
                f"{bold('Modelo:')} {modelo}\n"
                f"{bold('Motor:')} {motor}\n"
                f"{bold('Serie:')} {serie}\n"
                f"{bold('VIN:')} {vin}\n"
                f"{bold('Placa anterior:')} {anterior}\n\n"

                f"{bold('📑 PROPIEDAD Y REGISTRO')}\n"
                f"{italic('──────────────────────────────')}\n"
                f"{bold('Propietario(s):')}\n{titulares}\n"
                f"{bold('Total de titulares:')} {nro_tits}\n"
                f"{bold('Sede N°:')} {nro_sede}\n"
                f"{bold('Tarjeta:')} <code>{nro_taj}</code>\n"
                f"{bold('Oficina:')} {oficina}\n"
                f"{bold('Creado el:')} {creado}\n"
                f"{bold('Última actualización:')} {actualizado}\n\n"

                f"{bold('📂 HISTORIAL Y ESTADO')}\n"
                f"{italic('──────────────────────────────')}\n"
                f"{bold('Deuda de papeletas:')} {deuda}\n"
                f"{bold('N° de papeletas:')} {nro_pap}\n"
                f"{bold('SOAT(s):')} {soats}\n\n"
            )

        # Bloque Estado de Cuenta (solo ⚡ aquí)
        mensaje += (
            f" ➤ {bold('ESTADO DE CUENTA')}\n\n"
            f"{bold('Créditos disponibles ➤ ')} <code>{credits}</code>\n"
            f"{bold('ID de usuario ➤ ')} <code>{user_id}</code>\n"
            f"{bold('Usuario ➤ ')} {username}\n"
        )

        # 7) Envío (divide si excede el límite de Telegram)
        if len(mensaje) > 4000:
            partes = [mensaje[i:i+4000] for i in range(0, len(mensaje), 4000)]
            for parte in partes:
                await update.message.reply_text(
                    parte, parse_mode="HTML", reply_to_message_id=update.message.message_id
                )
                await asyncio.sleep(0)
        else:
            await update.message.reply_text(
                mensaje, parse_mode="HTML", reply_to_message_id=update.message.message_id
            )

    except asyncio.TimeoutError:
        await update.message.reply_text(
            "El servicio tardó demasiado en responder. Inténtalo nuevamente.",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
    except aiohttp.ClientError as ce:
        await update.message.reply_text(
            f"Error de conexión: {str(ce)}",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
    except Exception:
        await update.message.reply_text(
            "Ocurrió un error inesperado al procesar la solicitud.",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
    finally:
        try:
            await loading_message.delete()
        except Exception:
            pass

async def telp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # 1) Verificar argumentos
    if len(context.args) != 1:
        await update.message.reply_text(
            "❗ <b>Uso correcto:</b>\n"
            "/telp <code>número_telefono</code>\n"
            "Ejemplo: <code>/telp 999888777</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    numero = context.args[0].strip()
    # Valida 7–12 dígitos (ajusta a 9 si prefieres)
    if not re.fullmatch(r"\d{7,12}", numero):
        await update.message.reply_text(
            "El número ingresado no es válido.",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # 2) Verificar créditos
    if not await verifica_creditos(update, user_id, 'telefonia_menu'):
        return

    # 3) Cargar base de datos de usuarios
    username = "Desconocido"
    credits = "—"
    try:
        with open("users_db.json", "r", encoding="utf-8") as f:
            users_db = json.load(f)
        users = users_db.get("users", {})
        if str(user_id) in users:
            user_info = users[str(user_id)]
            username = user_info.get("username", "Desconocido")
            credits = user_info.get("credits", "—")
            if isinstance(credits, (int, float)):
                credits = int(credits) if credits == int(credits) else round(credits, 2)
    except Exception:
        pass

    # 4) Mensaje de carga
    loading_message = await update.message.reply_photo(
        photo="TRONCHITOBOT.png",
        caption="Procesando solicitud en OSIPTEL...",
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )

    # 5) Llamada HTTP asíncrona con aiohttp (API dentro del comando)
    timeout = aiohttp.ClientTimeout(total=12, connect=5, sock_read=7)
    url = f"http://161.132.51.34:1520/api/osipteldb?tel={numero}"

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await update.message.reply_text(
                        f"No se pudieron obtener datos (HTTP {resp.status}).",
                        parse_mode="HTML",
                        reply_to_message_id=update.message.message_id
                    )
                    return

                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    await update.message.reply_text(
                        "La respuesta del servidor no es JSON válido.",
                        parse_mode="HTML",
                        reply_to_message_id=update.message.message_id
                    )
                    return

        lista = data.get("listaAni", []) if isinstance(data, dict) else []
        if not (isinstance(lista, list) and lista):
            await update.message.reply_text(
                "No se encontraron datos para ese número.",
                parse_mode="HTML",
                reply_to_message_id=update.message.message_id
            )
            return

        # 6) Construir mensaje único con tu formato
        mensaje = f"{bold('[#TRONCHITOBOT] • TELEFONÍA POR NÚMERO')}\n\n"

        for idx, d in enumerate(lista, 1):
            registro   = d.get('registro')   or "N/A"
            telefono   = d.get('telefono')   or "N/A"
            documento  = d.get('documento')  or "N/A"
            empresa    = d.get('empresa')    or "N/A"
            operador   = d.get('operador')   or "N/A"
            plan       = d.get('plan')       or "N/A"
            correo     = (d.get('correo') or "").strip() or "No registra"
            titular    = (d.get('titular') or "").strip() or "No encontrado"
            fecha      = d.get('fecha')      or "N/A"

            mensaje += (
                f" — {bold(f'Resultado #{idx}')}\n"
                f"REGISTRO: {registro}\n"
                f"TELEFONO: <code>{telefono}</code>\n"
                f"DNI: <code>{documento}</code>\n"
                f"EMPRESA: {empresa}\n"
                f"OPERADOR: {operador}\n"
                f"PLAN: {plan}\n"
                f"CORREO: {correo}\n"
                f"TITULAR: {titular}\n"
                f"FECHA DE REGISTRO: {fecha}\n\n"
            )

        # 7) Estado de cuenta (con ⚡)
        mensaje += (
            f" ➤ {bold('Estado de Cuenta del Usuario')}\n\n"
            f"Créditos disponibles ➤ <code>{credits}</code>\n"
            f"ID de usuario ➤ <code>{user_id}</code>\n"
            f"Usuario ➤ <code>{username}</code>\n"
        )

        # 8) Enviar (dividir si excede el límite)
        if len(mensaje) > 4000:
            partes = [mensaje[i:i+4000] for i in range(0, len(mensaje), 4000)]
            for parte in partes:
                await update.message.reply_text(parte, parse_mode="HTML", reply_to_message_id=update.message.message_id)
                await asyncio.sleep(0)
        else:
            await update.message.reply_text(mensaje, parse_mode="HTML", reply_to_message_id=update.message.message_id)

    except asyncio.TimeoutError:
        await update.message.reply_text(
            "El servicio tardó demasiado en responder. Inténtalo nuevamente.",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
    except aiohttp.ClientError as ce:
        await update.message.reply_text(
            f"Error de conexión: {str(ce)}",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
    except Exception:
        await update.message.reply_text(
            "Ocurrió un error inesperado al procesar la solicitud.",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
    finally:
        try:
            await loading_message.delete()
        except Exception:
            pass

EMAIL_PROT_RE = re.compile(r"email\s*protected", re.IGNORECASE)

def _val(x, default="N/A"):
    s = "" if x is None else str(x).strip()
    return s if s else default

def _load_user_state(user_id):
    username, credits = "Desconocido", "—"
    try:
        with open("users_db.json", "r", encoding="utf-8") as f:
            users_db = json.load(f)
        info = (users_db.get("users") or {}).get(str(user_id)) or {}
        username = info.get("username", "Desconocido")
        credits  = info.get("credits", "—")
        if isinstance(credits, (int, float)):
            credits = int(credits) if credits == int(credits) else round(credits, 2)
    except Exception:
        pass
    return username, credits

# ----------------- /cel -----------------
async def cel(update, context):
    user_id = update.effective_user.id

    # 1) Validación
    if len(context.args) != 1:
        await update.message.reply_text(
            "❗ <b>Uso correcto:</b>\n/cel <code>DNI</code>\nEjemplo: <code>/cel 44443333</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # 2) Créditos
    if not await verifica_creditos(update, user_id, "telefonia_cel"):
        return

    # 3) Estado de cuenta
    username, credits = _load_user_state(user_id)

    dni = context.args[0].strip()
    url = f"https://web-production-da283.up.railway.app/telp?tel={dni}"

    # 4) Imagen de espera
    loading = await update.message.reply_photo(
        photo="TRONCHITOBOT.png",
        caption=f"[⏳] Consultando teléfonos para DNI <code>{escape(dni)}</code>...",
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )

    try:
        r = requests.get(url, timeout=30)
        if r.status_code != 200:
            await loading.delete()
            await update.message.reply_text(
                f"⚠️ Error {r.status_code} al consultar el servicio.",
                parse_mode="HTML",
                reply_to_message_id=update.message.message_id
            )
            return

        data = (r.json() or {}).get("data") or {}
        titular_dni   = _val(data.get("dni", dni))
        titular_nom   = _val(data.get("nombres"))
        titular_apell = _val(data.get("apellidos"))
        telefonos     = data.get("telefonos") or []

        # Normalizar emails
        norm_tels = []
        for t in telefonos:
            tel   = _val(t.get("telefono"))
            oper  = _val(t.get("operador"))
            perio = _val(t.get("periodo"))
            em    = str(t.get("email") or "").strip()
            if not em or EMAIL_PROT_RE.search(em):
                em = "No registrada"
            norm_tels.append((tel, oper, perio, em))

        # 5) Construir mensaje
        lines = []
        lines.append("[#TRONCHITOBOT] ➾ TELÉFONOS POR DNI\n")
        lines.append(f"DNI ➾ <code>{titular_dni}</code>")
        lines.append(f"NOMBRES ➾ {titular_nom}")
        lines.append(f"APELLIDOS ➾ {titular_apell}")
        lines.append(f"NÚMERO DE REGISTROS ➾ {len(norm_tels)}\n")

        if not norm_tels:
            lines.append("No se encontraron teléfonos registrados.")
        else:
            for i, (tel, oper, perio, em) in enumerate(norm_tels, start=1):
                lines.append(f"— Registro #{i}")
                lines.append(f"TELÉFONO ➾ <code>{tel}</code>")
                lines.append(f"OPERADOR ➾ {oper}")
                lines.append(f"PERIODO ➾ {perio}")
                lines.append(f"EMAIL ➾ {em}\n")

        # Estado de cuenta
        lines.append(" ➤  Estado de Cuenta del Usuario")
        lines.append(f"Créditos disponibles ➤ <code>{credits}</code>")
        lines.append(f"ID de usuario ➤ <code>{user_id}</code>")
        lines.append(f"Usuario ➤ <code>{escape(username)}</code>")

        msg = "\n".join(lines)

        await loading.delete()
        await update.message.reply_text(
            msg,
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )

    except Exception as e:
        try:
            await loading.delete()
        except:
            pass
        await update.message.reply_text(
            f"❌ Error en /cel: <code>{escape(str(e))}</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )

async def osiptel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # 🧩 Verificar argumentos
    if len(context.args) != 1:
        await update.message.reply_text(
            "❗ <b>Uso correcto:</b>\n"
            "/osiptel <code>dni</code>\n"
            "Ejemplo: <code>/osiptel 12345678</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    dni = context.args[0].strip()
    if not re.fullmatch(r"\d{8}", dni):
        await update.message.reply_text(
            "El número de DNI no es válido. Debe contener exactamente 8 dígitos.",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # 🧩 Verificar créditos
    if not await verifica_creditos(update, user_id, 'telefonia_osiptel'):
        return

    # 🧩 Cargar base de datos de usuarios
    username = "Desconocido"
    credits = "—"
    try:
        with open("users_db.json", "r", encoding="utf-8") as f:
            users_db = json.load(f)
        users = users_db.get("users", {})
        if str(user_id) in users:
            user_info = users[str(user_id)]
            username = user_info.get("username", "Desconocido")
            credits = user_info.get("credits", "—")
            if isinstance(credits, (int, float)):
                credits = int(credits) if credits == int(credits) else round(credits, 2)
    except Exception:
        pass

    # 🧩 Mensaje temporal
    loading_message = await update.message.reply_photo(
        photo="TRONCHITOBOT.png",
        caption="⏳ Procesando solicitud en OSIPTEL...",
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )

    url = f"http://161.132.51.34:1520/api/osipteldb?tel={dni}"

    try:
        # Llamada HTTP sin bloquear el loop
        response = await asyncio.to_thread(requests.get, url, timeout=12)

        if response.status_code != 200:
            await update.message.reply_text(
                f"No se pudo obtener información. (Código HTTP {response.status_code})",
                parse_mode="HTML",
                reply_to_message_id=update.message.message_id
            )
            return

        try:
            data = response.json()
        except ValueError:
            await update.message.reply_text(
                "La respuesta del servidor no tiene un formato válido.",
                parse_mode="HTML",
                reply_to_message_id=update.message.message_id
            )
            return

        lista = data.get("listaAni", [])
        if not isinstance(lista, list) or not lista:
            await update.message.reply_text(
                "No se encontraron registros para el DNI ingresado.",
                parse_mode="HTML",
                reply_to_message_id=update.message.message_id
            )
            return

        # 🧩 Construir el mensaje completo
        mensaje = f"{bold('[CONSULTA OSIPTEL - TELEFONÍA POR DNI]')}\n\n"

        for idx, d in enumerate(lista, 1):
            registro  = d.get('registro')  or "N/A"
            telefono  = d.get('telefono')  or "N/A"
            documento = d.get('documento') or "N/A"
            empresa   = d.get('empresa')   or "N/A"
            operador  = d.get('operador')  or "N/A"
            plan      = d.get('plan')      or "N/A"
            correo    = (d.get('correo') or "").strip() or "No registrado"
            titular   = (d.get('titular') or "").strip() or "No encontrado"
            fecha     = d.get('fecha')     or "N/A"

            mensaje += (
                f" — {bold(f'Resultado #{idx}')}\n"
                f"REGISTRO: {registro}\n"
                f"TELEFONO: <code>{telefono}</code>\n"
                f"DNI: <code>{documento}</code>\n"
                f"EMPRESA: {empresa}\n"
                f"OPERADOR: {operador}\n"
                f"PLAN: {plan}\n"
                f"CORREO: {correo}\n"
                f"TITULAR: {titular}\n"
                f"FECHA DE REGISTRO: {fecha}\n\n"
            )

        # 🧩 Estado de cuenta del usuario
        mensaje += (
            f" ➤ {bold('Estado de Cuenta del Usuario')}\n\n"
            f"Créditos disponibles ➤ <code>{credits}</code>\n"
            f"ID de usuario ➤ <code>{user_id}</code>\n"
            f"Usuario ➤ <code>{username}</code>\n"
        )

        # Dividir en partes si excede el límite de Telegram
        if len(mensaje) > 4000:
            partes = [mensaje[i:i+4000] for i in range(0, len(mensaje), 4000)]
            for parte in partes:
                await update.message.reply_text(parte, parse_mode="HTML", reply_to_message_id=update.message.message_id)
                await asyncio.sleep(0)
        else:
            await update.message.reply_text(mensaje, parse_mode="HTML", reply_to_message_id=update.message.message_id)

    except requests.Timeout:
        await update.message.reply_text(
            "El servicio de OSIPTEL no respondió a tiempo. Por favor, intenta nuevamente.",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
    except requests.RequestException as e:
        await update.message.reply_text(
            f"Error al conectarse con el servicio: {e}",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
    except Exception as e:
        await update.message.reply_text(
            "Ocurrió un error inesperado al procesar la solicitud.",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
    finally:
        try:
            await loading_message.delete()
        except Exception:
            pass

async def riesgos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # === 🧩 API CONFIGURADA ===
    API_URL = "https://web-production-da283.up.railway.app/risk"  # API final
    # ===========================

    # Validar argumentos
    if len(context.args) != 1:
        await update.message.reply_text(
            "❗<b>USO CORRECTO:</b>\n/riesgos <code>dni</code>\nEJEMPLO: <code>/riesgos 12345678</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # Leer base de usuarios
    try:
        with open("users_db.json", "r", encoding="utf-8") as f:
            users_db = json.load(f)
        users = users_db.get("users", {})
    except Exception:
        await update.message.reply_text("❌ Error al leer la base de datos.", parse_mode="HTML")
        return

    if str(user_id) not in users:
        await update.message.reply_text(
            "⚠️ No puedes usar este comando porque no estás registrado.\nUsa /register para poder registrarte.",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    user_info = users[str(user_id)]
    credits = user_info.get("credits", "—")
    username = user_info.get("username", "Desconocido")
    if isinstance(credits, (int, float)) and credits == int(credits):
        credits = int(credits)

    dni_value = context.args[0]

    loading_message = await update.message.reply_photo(
        photo="TRONCHITOBOT.png",
        caption="[⏳] PROCESANDO REPORTE DE RIESGOS...",
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )

    try:
        # 🔗 Consumir la API
        url = f"{API_URL}?dni={dni_value}"
        resp = requests.get(url, timeout=40)
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}")

        payload = resp.json() if resp.content else {}
        data = (payload or {}).get("data", {}) or {}

        # ---- Titular ----
        titular_dni = data.get("dni", "") or ""
        titular_nombres = data.get("nombres", "") or ""
        titular_apellidos = data.get("apellidos", "") or ""
        riesgos = data.get("riesgo", []) or []

        # Campos extra del titular
        known_titular = {"dni", "nombres", "apellidos", "riesgo"}
        extras_titular = {k: v for k, v in data.items() if k not in known_titular}

        # ---- Armar respuesta ----
        lineas = []
        lineas.append("[#TRONCHITOBOT] ➾ REPORTE DE RIESGOS\n")

        # Titular
        lineas.append("[👤] TITULAR")
        lineas.append(f"DNI ➾ <code>{titular_dni}</code>")
        lineas.append(f"NOMBRES ➾ {titular_nombres}")
        lineas.append(f"APELLIDOS ➾ {titular_apellidos}")

        # Extras del titular, si los hay
        for k, v in extras_titular.items():
            lineas.append(f"{k.upper()} ➾ {v}")

        # Riesgos
        lineas.append("\n[📊] DETALLE DE RIESGOS")
        if not riesgos:
            lineas.append("No se encontraron registros de riesgo.")
        else:
            # Resumen por moneda
            totales_por_moneda = {}
            for i, r in enumerate(riesgos, start=1):
                entidad = r.get("entidad", "")
                descripcion = r.get("descripcion", "")
                moneda = r.get("moneda", "")
                saldo_str = r.get("saldo", "0")
                clasif = r.get("clasificacion", "")

                # Suma por moneda (robusto a strings)
                try:
                    saldo_num = Decimal(str(saldo_str).replace(",", ""))
                except (InvalidOperation, TypeError):
                    saldo_num = Decimal("0")
                totales_por_moneda[moneda] = totales_por_moneda.get(moneda, Decimal("0")) + saldo_num

                # Item
                lineas.append(f"\n— Registro #{i}")
                lineas.append(f"ENTIDAD ➾ {entidad}")
                lineas.append(f"DESCRIPCIÓN ➾ {descripcion}")
                lineas.append(f"MONEDA ➾ {moneda}")
                lineas.append(f"SALDO ➾ <code>{saldo_str}</code>")
                lineas.append(f"CLASIFICACIÓN ➾ {clasif}")

                # Extras por registro
                known_r = {"entidad", "descripcion", "moneda", "saldo", "clasificacion"}
                extras_r = {k: v for k, v in r.items() if k not in known_r}
                for k, v in extras_r.items():
                    lineas.append(f"{k.upper()} ➾ {v}")

            # Resumen final por moneda
            lineas.append("\n[🧮] RESUMEN POR MONEDA")
            for mon, total in totales_por_moneda.items():
                lineas.append(f"{mon or '—'} ➾ <code>{str(total)}</code>")

        # Pie de estado de cuenta
        lineas.append("\n[⚡] ESTADO DE CUENTA")
        lineas.append(f"CREDITOS ➾ <code>{credits}</code> - <code>{user_id}</code>")
        lineas.append(f"USUARIO ➾ {username}")

        mensaje = "\n".join(lineas)

        await update.message.reply_text(
            mensaje,
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        await loading_message.delete()

    except Exception as e:
        try:
            await loading_message.delete()
        except:
            pass
        await update.message.reply_text(
            f"❌ ERROR AL PROCESAR: {e}",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )

async def ftv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # === 🧩 API CONFIGURADA ===
    API_URL = "https://web-production-da283.up.railway.app/foto"
    # ===========================

    # Validar argumentos
    if len(context.args) != 1:
        await update.message.reply_text(
            "❗<b>USO CORRECTO:</b>\n/ftv <code>dni</code>\nEJEMPLO: <code>/ftv 12345678</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # Leer base de usuarios
    try:
        with open("users_db.json", "r", encoding="utf-8") as f:
            users_db = json.load(f)
        users = users_db.get("users", {})
    except Exception:
        await update.message.reply_text("❌ Error al leer la base de datos.", parse_mode="HTML")
        return

    if str(user_id) not in users:
        await update.message.reply_text(
            "⚠️ No puedes usar este comando porque no estás registrado.\nUsa /register para poder registrarte.",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    user_info = users[str(user_id)]
    credits = user_info.get("credits", "—")
    username = user_info.get("username", "Desconocido")
    if isinstance(credits, (int, float)) and credits == int(credits):
        credits = int(credits)

    dni_value = context.args[0]

    loading_message = await update.message.reply_photo(
        photo="TRONCHITOBOT.png",
        caption="[⏳] OBTENIENDO FOTO DEL DNI...",
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )

    try:
        # 🔗 Consumir la API
        url = f"{API_URL}?dni={dni_value}"
        resp = requests.get(url, timeout=40)
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}")

        payload = resp.json() if resp.content else {}
        data = (payload or {}).get("data", {}) or {}

        # ---- Extraer datos ----
        titular_dni = data.get("dni", "")
        titular_nombres = data.get("nombres", "")
        titular_apellidos = data.get("apellidos", "")
        foto_b64 = data.get("foto")

        # Mensaje descriptivo
        caption = (
            f"[#TRONCHITOBOT] ➾ FOTO RENIEC\n\n"
            f"DNI ➾ <code>{titular_dni}</code>\n"
            f"NOMBRES ➾ {titular_nombres}\n"
            f"APELLIDOS ➾ {titular_apellidos}\n\n"
            f"[⚡] ESTADO DE CUENTA\n"
            f"CREDITOS ➾ <code>{credits}</code> - <code>{user_id}</code>\n"
            f"USUARIO ➾ {username}"
        )

        if foto_b64:
            try:
                # Decodificar la imagen Base64
                encoded = foto_b64.split(",", 1)[1] if foto_b64.startswith("data:image") else foto_b64
                photo_bytes = base64.b64decode(encoded)
                bio = BytesIO(photo_bytes)
                bio.name = f"{dni_value}.jpg"

                await update.message.reply_photo(
                    photo=InputFile(bio),
                    caption=caption,
                    parse_mode="HTML",
                    reply_to_message_id=update.message.message_id
                )
                await loading_message.delete()
                return
            except Exception as e:
                await update.message.reply_text(
                    f"⚠️ Error al procesar la imagen: {e}",
                    parse_mode="HTML",
                    reply_to_message_id=update.message.message_id
                )
        else:
            await update.message.reply_text(
                "❌ No se encontró una foto en la respuesta.",
                parse_mode="HTML",
                reply_to_message_id=update.message.message_id
            )

        await loading_message.delete()

    except Exception as e:
        try:
            await loading_message.delete()
        except:
            pass
        await update.message.reply_text(
            f"❌ ERROR AL PROCESAR: {e}",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )

async def denuncias(update, context):
    user_id = update.effective_user.id

    # 1) Validar argumentos
    if len(context.args) != 1:
        await update.message.reply_text(
            "❗ <b>Uso correcto:</b>\n/denuncia_pdf <code>DNI</code>\nEjemplo: <code>/denuncia_pdf 10000006</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # 2) Verificar créditos (no descuenta aquí)
    if not await verifica_creditos(update, user_id, 'denuncia_pdf'):
        return

    # 3) Cargar usuario (solo para estado de cuenta)
    username = "Desconocido"
    credits = "—"
    try:
        with open("users_db.json", "r", encoding="utf-8") as f:
            users_db = json.load(f)
        users = users_db.get("users", {})
        if str(user_id) in users:
            info = users[str(user_id)]
            username = info.get("username", "Desconocido")
            credits = info.get("credits", "—")
            if isinstance(credits, (int, float)):
                credits = int(credits) if credits == int(credits) else round(credits, 2)
    except Exception:
        pass

    dni = context.args[0].strip()

    # API principal (PDFs en base64)
    url_api = f"http://161.132.45.149:3001/api/denuncias-json/{dni}?token=f0c156bb-b90b-48d7-8aa4-66265c4c45d0"
    # API opcional para nombre de persona
    url_dni = f"https://web-production-da283.up.railway.app/dni?dni={dni}"

    # 4) Loading
    loading_message = await update.message.reply_photo(
        photo="TRONCHITOBOT.png",
        caption=f"[⏳] Buscando denuncias PDF para DNI {escape(dni)}...",
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )

    try:
        # 5) Consultar APIs
        resp_pdf = requests.get(url_api, timeout=30)
        if resp_pdf.status_code != 200:
            await loading_message.delete()
            await update.message.reply_text(
                f"⚠️ Error {resp_pdf.status_code} al consultar el servicio de denuncias.",
                parse_mode="HTML",
                reply_to_message_id=update.message.message_id
            )
            return

        data_pdf = resp_pdf.json() or {}
        denuncias = data_pdf.get("denuncias") or []

        # Nombre desde RENIEC (opcional)
        nombre = "N/A"
        try:
            resp_dni = requests.get(url_dni, timeout=20)
            if resp_dni.status_code == 200:
                j = resp_dni.json() or {}
                if "data" in j and j["data"]:
                    nombre = (j["data"].get("nombre") or "N/A")
                elif isinstance(j, dict):
                    nombre = j.get("nombre", "N/A")
        except Exception:
            pass

        if not denuncias:
            await loading_message.delete()
            await update.message.reply_text(
                f"❌ No se encontraron denuncias para el DNI <code>{escape(dni)}</code>.",
                parse_mode="HTML",
                reply_to_message_id=update.message.message_id
            )
            return

        # 6) Enviar cada PDF
        await loading_message.delete()

        for idx, item in enumerate(denuncias, start=1):
            try:
                b64 = (item or {}).get("base64") or ""
                meta = (item or {}).get("pdf_data") or {}

                comisaria = meta.get("comisaria", "N/A")
                fecha_registro = meta.get("fecha_registro", "N/A")
                clave = meta.get("clave", "N/A")

                # Nombre del archivo: DENUNCIA {idx} - {dni}.pdf
                nombre_archivo = f"DENUNCIA {idx} - {dni}.pdf"

                # Decode base64 → BytesIO
                raw = base64.b64decode(b64)
                bio = BytesIO(raw)
                bio.seek(0)
                bio.name = nombre_archivo

                # Caption limpio y sin emojis (excepto ⚡)
                caption = (
                    "<b>BÚSQUEDA DE DENUNCIA POR DNI</b>\n\n"
                    f"DNI: <code>{escape(dni)}</code>\n"
                    f"Nombre: {escape(str(nombre))}\n"
                    f"Comisaría: {escape(str(comisaria))}\n"
                    f"Fecha de registro: {escape(str(fecha_registro))}\n"
                    f"Clave: {escape(str(clave))}\n\n"
                    "[⚡] <b>ESTADO DE CUENTA</b>\n"
                    f"CREDITOS ➾ <code>{credits}</code> - <code>{user_id}</code>\n"
                    f"USUARIO ➾ {escape(username)}"
                )

                await update.message.reply_document(
                    document=InputFile(bio),
                    caption=caption,
                    parse_mode="HTML",
                    reply_to_message_id=update.message.message_id
                )

            except Exception as e_each:
                await update.message.reply_text(
                    f"⚠️ No se pudo enviar un PDF (#{idx}): <code>{escape(str(e_each))}</code>",
                    parse_mode="HTML",
                    reply_to_message_id=update.message.message_id
                )

    except Exception as e:
        try:
            await loading_message.delete()
        except:
            pass
        await update.message.reply_text(
            f"❌ Error al obtener denuncias: <code>{escape(str(e))}</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        
def _ci(val: str) -> str:
    """capitalize simple (Mujer -> Mujer, hombre -> Hombre)"""
    try:
        s = str(val).strip()
        return s[:1].upper() + s[1:].lower() if s else s
    except Exception:
        return str(val)

def _find_key_ci(obj, key_targets):
    """
    Busca recursivamente la PRIMERA coincidencia de cualquier clave en key_targets
    sin importar mayúsculas/minúsculas, en dicts y listas.
    """
    if not isinstance(key_targets, (list, tuple, set)):
        key_targets = [key_targets]
    targets = {str(k).lower() for k in key_targets}

    dq = collections.deque([obj])
    while dq:
        cur = dq.popleft()
        if isinstance(cur, dict):
            # Primero intenta coincidencia directa en este nivel
            for k, v in cur.items():
                if str(k).lower() in targets:
                    return v
            # Si no, sigue recorriendo
            for v in cur.values():
                if isinstance(v, (dict, list, tuple)):
                    dq.append(v)
        elif isinstance(cur, (list, tuple)):
            for v in cur:
                if isinstance(v, (dict, list, tuple)):
                    dq.append(v)
    return None

async def denunciasv(update, context):
    user_id = update.effective_user.id

    # 1) Validar argumentos
    if len(context.args) != 1:
        await update.message.reply_text(
            "❗ <b>Uso correcto:</b>\n/denunciasv <code>DNI</code>\nEjemplo: <code>/denunciasv 10000006</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # 2) Verificar créditos
    if not await verifica_creditos(update, user_id, 'denunciasv'):
        return

    # 3) Estado de cuenta
    username = "Desconocido"
    credits = "—"
    try:
        with open("users_db.json", "r", encoding="utf-8") as f:
            users_db = json.load(f)
        users = users_db.get("users", {})
        if str(user_id) in users:
            info = users[str(user_id)]
            username = info.get("username", "Desconocido")
            credits = info.get("credits", "—")
            if isinstance(credits, (int, float)):
                credits = int(credits) if credits == int(credits) else round(credits, 2)
    except Exception:
        pass

    dni = context.args[0].strip()

    # 4) APIs
    url_denuncias = f"http://161.132.45.149:3001/api/denuncias-json/{dni}?token=f0c156bb-b90b-48d7-8aa4-66265c4c45d0"
    url_dni       = f"https://web-production-da283.up.railway.app/dni?dni={dni}"

    # 5) Loading
    loading = await update.message.reply_photo(
        photo="TRONCHITOBOT.png",
        caption=f"[⏳] Consultando información para DNI {escape(dni)}...",
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )

    try:
        # 6) Consultas
        r_den = requests.get(url_denuncias, timeout=30)
        r_dni = requests.get(url_dni,       timeout=20)

        if r_den.status_code != 200:
            await loading.delete()
            await update.message.reply_text(
                f"⚠️ Error {r_den.status_code} al consultar el servicio de denuncias.",
                parse_mode="HTML",
                reply_to_message_id=update.message.message_id
            )
            return

        jd = r_den.json() or {}
        denuncias = jd.get("denuncias") or []
        num_denuncias = len(denuncias)

        jdni = r_dni.json() if r_dni.status_code == 200 else {}

        # La API puede devolver {"data": {...}} o llano. Unificamos a un dict raíz combinando ambos.
        if isinstance(jdni, dict):
            root = jdni.copy()
            if isinstance(jdni.get("data"), dict):
                # "data" suele tener lo bueno; mezclamos sin sobreescribir claves ya existentes
                for k, v in jdni["data"].items():
                    root.setdefault(k, v)
        else:
            root = {}

        # ===== Nombre, Edad, Sexo =====
        # Nombre: intenta varias claves comunes
        nombre = (
            _find_key_ci(root, ["nombre", "nombres", "nombres_completos", "Nombre", "Nombres"])
            or "N/A"
        )

        # Edad/Sexo: usar EXACTAMENTE lo que venga en la API (claves "Edad" y "Sexo")
        # con fallback case-insensitive y recursivo.
        edad = _find_key_ci(root, ["Edad", "edad"]) or "N/A"
        sexo = _find_key_ci(root, ["Sexo", "sexo"]) or "N/A"

        # Normalizar sexo (capitalizar simple)
        if isinstance(sexo, str):
            sexo = _ci(sexo)

        # Foto (si viene en base64)
        foto_b64 = _find_key_ci(root, ["foto", "Foto"]) or ""

        # 7) Caption (sin emojis salvo ⚡)
        caption = (
            "<b>CONSULTA DE DENUNCIAS</b>\n\n"
            f"DNI: <code>{escape(dni)}</code>\n"
            f"Nombre completo: {escape(str(nombre))}\n"
            f"Edad: {escape(str(edad))}\n"
            f"Sexo: {escape(str(sexo))}\n"
            f"Número de denuncias: {num_denuncias}\n\n"
            "[⚡] <b>ESTADO DE CUENTA</b>\n"
            f"CREDITOS ➾ <code>{credits}</code> - <code>{user_id}</code>\n"
            f"USUARIO ➾ {escape(username)}"
        )

        await loading.delete()

        # 8) Responder con foto + datos
        if foto_b64:
            try:
                payload = foto_b64.split(",", 1)[1] if isinstance(foto_b64, str) and foto_b64.startswith("data:image") else foto_b64
                raw = base64.b64decode(payload)
                bio = BytesIO(raw); bio.seek(0); bio.name = f"foto_{dni}.jpg"
                await update.message.reply_photo(
                    photo=InputFile(bio),
                    caption=caption,
                    parse_mode="HTML",
                    reply_to_message_id=update.message.message_id
                )
            except Exception:
                await update.message.reply_photo(
                    photo="TRONCHITOBOT.png",
                    caption=caption,
                    parse_mode="HTML",
                    reply_to_message_id=update.message.message_id
                )
        else:
            await update.message.reply_photo(
                photo="TRONCHITOBOT.png",
                caption=caption,
                parse_mode="HTML",
                reply_to_message_id=update.message.message_id
            )

    except Exception as e:
        try:
            await loading.delete()
        except:
            pass
        await update.message.reply_text(
            f"❌ Error en /denunciasv: <code>{escape(str(e))}</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        

def _val(x, default="N/A"):
    s = "" if x is None else str(x).strip()
    return s if s else default

# /seeker {dni}
async def seeker(update, context):
    user_id = update.effective_user.id

    # 0) Validación
    if len(context.args) != 1:
        await update.message.reply_text(
            "❗ <b>Uso correcto:</b>\n/seeker <code>DNI</code>\nEjemplo: <code>/seeker 44443333</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # 1) Verificación de créditos (no descuenta aquí)
    if not await verifica_creditos(update, user_id, "seeker"):
        return

    # 2) Estado de cuenta (para pie de cada mensaje)
    username = "Desconocido"
    credits = "—"
    try:
        with open("users_db.json", "r", encoding="utf-8") as f:
            users_db = json.load(f)
        users = users_db.get("users", {})
        if str(user_id) in users:
            info = users[str(user_id)]
            username = info.get("username", "Desconocido")
            credits = info.get("credits", "—")
            if isinstance(credits, (int, float)):
                credits = int(credits) if credits == int(credits) else round(credits, 2)
    except Exception:
        pass

    dni = context.args[0].strip()

    # 3) Endpoints
    url_dni  = f"https://web-production-da283.up.railway.app/dni?dni={dni}"
    url_telp = f"https://web-production-da283.up.railway.app/telp?tel={dni}"
    url_arg  = f"https://web-production-da283.up.railway.app/arg?dni={dni}"
    url_risk = f"https://web-production-da283.up.railway.app/risk?dni={dni}"

    # ===== 1) DNI (con FOTO base64) =====
    try:
        r = requests.get(url_dni, timeout=25)
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}")
        j = r.json() or {}
        data = j.get("data") or {}

        dni_resp = _val(data.get("dni", dni))
        nombre   = _val(data.get("nombre"))
        datos    = data.get("datos") or {}

        fecha_nac   = _val(datos.get("Fecha de Nacimiento"))
        edad        = _val(datos.get("Edad"))
        sexo        = _val(datos.get("Sexo"))
        estado_civil= _val(datos.get("Estado"))
        padre       = _val(datos.get("Padre"))
        madre       = _val(datos.get("Madre"))
        ubicacion   = _val(datos.get("Ubicación"))
        direccion   = _val(datos.get("Dirección"))
        ubigeo_nac  = _val(datos.get("Ubigeo Nacimiento"))
        fecha_fallec= _val(datos.get("Fecha de Fallecimiento"))

        foto_b64 = data.get("foto") or ""

        mensaje = (
            f"[#TRONCHITOBOT] ➾ RENIEC X DNI\n\n"
            f"DNI ➾ <code>{escape(dni_resp)}</code>\n"
            f"NOMBRE COMPLETO ➾ {escape(nombre)}\n"
            f"SEXO ➾ {escape(sexo)}\n"
            f"EDAD ➾ {escape(edad)}\n"
            f"ESTADO CIVIL ➾ {escape(estado_civil)}\n"
            f"FECHA DE FALLECIMIENTO ➾ {escape(fecha_fallec)}\n\n"
            f"[🎂] NACIMIENTO\n\n"
            f"FECHA NACIMIENTO ➾ {escape(fecha_nac)}\n"
            f"PADRE ➾ {escape(padre)}\n"
            f"MADRE ➾ {escape(madre)}\n"
            f"UBIGEO NACIMIENTO ➾ {escape(ubigeo_nac)}\n\n"
            f"[📋] INFORMACIÓN GENERAL\n\n"
            f"UBICACIÓN ➾ {escape(ubicacion)}\n"
            f"DIRECCIÓN ➾ {escape(direccion)}\n\n"
            f"[⚡] ESTADO DE CUENTA\n\n"
            f"CREDITOS ➾ <code>{credits}</code> - <code>{user_id}</code>\n"
            f"USUARIO ➾ {escape(username)}\n"
        )

        # Enviar como foto si tenemos base64 válido; si no, como texto
        try:
            if foto_b64:
                payload = foto_b64.split(",", 1)[1] if foto_b64.startswith("data:image") else foto_b64
                raw = base64.b64decode(payload)
                bio = BytesIO(raw); bio.seek(0); bio.name = f"foto_{dni}.jpg"
                await update.message.reply_photo(
                    photo=InputFile(bio),
                    caption=mensaje,
                    parse_mode="HTML",
                    reply_to_message_id=update.message.message_id
                )
            else:
                await update.message.reply_text(
                    mensaje, parse_mode="HTML", reply_to_message_id=update.message.message_id
                )
        except Exception:
            await update.message.reply_text(
                mensaje, parse_mode="HTML", reply_to_message_id=update.message.message_id
            )

    except Exception as e:
        await update.message.reply_text(
            f"[#TRONCHITOBOT] ➾ RENIEC X DNI\n\nNo se pudo obtener datos de DNI. Detalle: <code>{escape(str(e))}</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )

    # ===== 2) TELP =====
    try:
        r = requests.get(url_telp, timeout=25)
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}")
        j = r.json() or {}
        data = j.get("data") or {}

        telp_dni   = _val(data.get("dni", dni))
        nombres    = _val(data.get("nombres"))
        apellidos  = _val(data.get("apellidos"))
        telefonos  = data.get("telefonos") or []

        lineas = []
        lineas.append("[#TRONCHITOBOT] ➾ TELÉFONOS")
        lineas.append("")
        lineas.append(f"DNI ➾ <code>{escape(telp_dni)}</code>")
        lineas.append(f"NOMBRES ➾ {escape(nombres)}")
        lineas.append(f"APELLIDOS ➾ {escape(apellidos)}")
        lineas.append("")
        lineas.append("[📞] REGISTROS")
        if telefonos:
            for i, t in enumerate(telefonos, start=1):
                telefono = _val(t.get("telefono"))
                operador = _val(t.get("operador"))
                periodo  = _val(t.get("periodo"))
                email    = _val(t.get("email"), "")
                lineas.append(f"\n— Teléfono #{i}")
                lineas.append(f"NUMERO ➾ <code>{escape(telefono)}</code>")
                lineas.append(f"OPERADOR ➾ {escape(operador)}")
                lineas.append(f"PERIODO ➾ {escape(periodo)}")
                if email:
                    lineas.append(f"EMAIL ➾ {escape(email)}")
        else:
            lineas.append("No se encontraron teléfonos.")

        lineas.append("\n[⚡] ESTADO DE CUENTA")
        lineas.append(f"CREDITOS ➾ <code>{credits}</code> - <code>{user_id}</code>")
        lineas.append(f"USUARIO ➾ {escape(username)}")

        msg_telp = "\n".join(lineas)

        await update.message.reply_text(
            msg_telp, parse_mode="HTML", reply_to_message_id=update.message.message_id
        )

    except Exception as e:
        await update.message.reply_text(
            f"[#TRONCHITOBOT] ➾ TELÉFONOS\n\nNo se pudo obtener teléfonos. Detalle: <code>{escape(str(e))}</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )

    # ===== 3) ARG (ÁRBOL) =====
    try:
        r = requests.get(url_arg, timeout=25)
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}")
        j = r.json() or {}
        data = j.get("data") or {}

        titular_dni       = _val(data.get("dni", dni))
        titular_nombres   = _val(data.get("nombres"))
        titular_apellidos = _val(data.get("apellidos"))
        arbol             = data.get("arbol") or []

        # extras del titular (cualquier otro campo en data)
        known_tit = {"dni", "nombres", "apellidos", "arbol"}
        extras_titular = {k: v for k, v in data.items() if k not in known_tit}

        lineas = []
        lineas.append("[#TRONCHITOBOT] ➾ ÁRBOL GENEALÓGICO\n")
        lineas.append("[👤] TITULAR")
        lineas.append(f"DNI ➾ <code>{escape(titular_dni)}</code>")
        lineas.append(f"NOMBRES ➾ {escape(titular_nombres)}")
        lineas.append(f"APELLIDOS ➾ {escape(titular_apellidos)}")

        for k, v in extras_titular.items():
            lineas.append(f"{escape(k.upper())} ➾ {escape(_val(v))}")

        lineas.append("\n[👨‍👩‍👧‍👦] FAMILIARES")
        if not arbol:
            lineas.append("No se encontraron familiares.")
        else:
            for i, fam in enumerate(arbol, start=1):
                fam_dni   = _val(fam.get("dni"))
                fam_nom   = _val(fam.get("nombres"))
                fam_ap_pa = _val(fam.get("apellidoPaterno"))
                fam_ap_ma = _val(fam.get("apellidoMaterno"))
                fam_edad  = _val(fam.get("edad"))
                fam_sexo  = _val(fam.get("sexo"))
                fam_tipo  = _val(fam.get("tipo"))
                fam_ubigeo= _val(fam.get("ubigeo"))

                lineas.append(f"\n— Familiar #{i}")
                lineas.append(f"DNI ➾ <code>{escape(fam_dni)}</code>")
                lineas.append(f"NOMBRES ➾ {escape(fam_nom)}")
                lineas.append(f"AP. PATERNO ➾ {escape(fam_ap_pa)}")
                lineas.append(f"AP. MATERNO ➾ {escape(fam_ap_ma)}")
                lineas.append(f"EDAD ➾ {escape(fam_edad)}")
                lineas.append(f"SEXO ➾ {escape(fam_sexo)}")
                lineas.append(f"TIPO ➾ {escape(fam_tipo)}")
                lineas.append(f"UBIGEO ➾ {escape(fam_ubigeo)}")

                known_fam = {
                    "dni", "nombres", "apellidoPaterno", "apellidoMaterno",
                    "edad", "sexo", "tipo", "ubigeo"
                }
                extras_fam = {k: v for k, v in fam.items() if k not in known_fam}
                for k, v in extras_fam.items():
                    lineas.append(f"{escape(k.upper())} ➾ {escape(_val(v))}")

        lineas.append("\n[⚡] ESTADO DE CUENTA")
        lineas.append(f"CREDITOS ➾ <code>{credits}</code> - <code>{user_id}</code>")
        lineas.append(f"USUARIO ➾ {escape(username)}")

        msg_arg = "\n".join(lineas)

        await update.message.reply_text(
            msg_arg, parse_mode="HTML", reply_to_message_id=update.message.message_id
        )

    except Exception as e:
        await update.message.reply_text(
            f"[#TRONCHITOBOT] ➾ ÁRBOL GENEALÓGICO\n\nNo se pudo obtener el árbol. Detalle: <code>{escape(str(e))}</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )

    # ===== 4) RISK =====
    try:
        r = requests.get(url_risk, timeout=25)
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}")
        j = r.json() or {}
        data = j.get("data") or {}

        titular_dni       = _val(data.get("dni", dni))
        titular_nombres   = _val(data.get("nombres"))
        titular_apellidos = _val(data.get("apellidos"))
        riesgos           = data.get("riesgo") or []

        known_tit = {"dni", "nombres", "apellidos", "riesgo"}
        extras_titular = {k: v for k, v in data.items() if k not in known_tit}

        lineas = []
        lineas.append("[#TRONCHITOBOT] ➾ REPORTE DE RIESGOS\n")
        lineas.append("[👤] TITULAR")
        lineas.append(f"DNI ➾ <code>{escape(titular_dni)}</code>")
        lineas.append(f"NOMBRES ➾ {escape(titular_nombres)}")
        lineas.append(f"APELLIDOS ➾ {escape(titular_apellidos)}")

        for k, v in extras_titular.items():
            lineas.append(f"{escape(k.upper())} ➾ {escape(_val(v))}")

        lineas.append("\n[📊] DETALLE DE RIESGOS")
        if not riesgos:
            lineas.append("No se encontraron registros de riesgo.")
            totales_por_moneda = {}
        else:
            totales_por_moneda = {}
            for i, rr in enumerate(riesgos, start=1):
                entidad = _val(rr.get("entidad"))
                descripcion = _val(rr.get("descripcion"), "")
                moneda = _val(rr.get("moneda"))
                saldo_str = _val(rr.get("saldo"), "0")
                clasif = _val(rr.get("clasificacion"))

                # Suma por moneda
                try:
                    saldo_num = Decimal(str(saldo_str).replace(",", ""))
                except (InvalidOperation, TypeError):
                    saldo_num = Decimal("0")
                totales_por_moneda[moneda] = totales_por_moneda.get(moneda, Decimal("0")) + saldo_num

                lineas.append(f"\n— Registro #{i}")
                lineas.append(f"ENTIDAD ➾ {escape(entidad)}")
                lineas.append(f"DESCRIPCIÓN ➾ {escape(descripcion)}")
                lineas.append(f"MONEDA ➾ {escape(moneda)}")
                lineas.append(f"SALDO ➾ <code>{escape(str(saldo_str))}</code>")
                lineas.append(f"CLASIFICACIÓN ➾ {escape(clasif)}")

                known_r = {"entidad", "descripcion", "moneda", "saldo", "clasificacion"}
                extras_r = {k: v for k, v in rr.items() if k not in known_r}
                for k, v in extras_r.items():
                    lineas.append(f"{escape(k.upper())} ➾ {escape(_val(v))}")

            lineas.append("\n[🧮] RESUMEN POR MONEDA")
            for mon, total in totales_por_moneda.items():
                lineas.append(f"{escape(mon or '—')} ➾ <code>{escape(str(total))}</code>")

        lineas.append("\n[⚡] ESTADO DE CUENTA")
        lineas.append(f"CREDITOS ➾ <code>{credits}</code> - <code>{user_id}</code>")
        lineas.append(f"USUARIO ➾ {escape(username)}")

        msg_risk = "\n".join(lineas)

        await update.message.reply_text(
            msg_risk, parse_mode="HTML", reply_to_message_id=update.message.message_id
        )

    except Exception as e:
        await update.message.reply_text(
            f"[#TRONCHITOBOT] ➾ REPORTE DE RIESGOS\n\nNo se pudo obtener datos de riesgo. Detalle: <code>{escape(str(e))}</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )   

# ----------------- helpers -----------------
INVALID_FECHA_RE = re.compile(r"fecha\s+inv[aá]lida", re.IGNORECASE)
EMAIL_PROT_RE    = re.compile(r"email\s*protected", re.IGNORECASE)

def _font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()

def _wrap(draw, text, font, max_w, max_lines=None):
    """
    Envuelve texto en varias líneas.
    Si se pasa max_lines, limita el número de líneas y agrega '…' si se trunca.
    Compatible con las versiones de /seekerpdf y /agv.
    """
    s = "" if text is None else str(text).strip()
    if not s:
        return [""]

    words, cur, lines = s.split(), "", []

    def fits(t):
        try:
            return draw.textlength(t, font=font) <= max_w
        except Exception:
            # Fallback si textlength no está disponible
            try:
                x0, y0, x1, y1 = draw.textbbox((0, 0), t, font=font)
                return (x1 - x0) <= max_w
            except Exception:
                return len(t) * (getattr(font, "size", 12) * 0.6) <= max_w

    for w in words:
        t = (cur + " " + w).strip()
        if fits(t):
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
            # Si ya alcanzó el máximo de líneas, cortamos
            if max_lines and len(lines) >= max_lines:
                break

    if cur and (not max_lines or len(lines) < max_lines):
        lines.append(cur)

    # Si hay límite de líneas y se excedió, agrega "…"
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]

    if max_lines and len(lines) == max_lines and len(" ".join(words)) > len(" ".join(lines)):
        while lines and fits(lines[-1] + "…") is False and lines[-1]:
            lines[-1] = lines[-1][:-1]
        if lines:
            lines[-1] = (lines[-1] + "…") if lines[-1] else "…"

    return lines


def _rounded(draw, box, r, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)

def _hgrad(w, h, c1, c2):
    base = Image.new("RGB", (w, h), c1)
    top  = Image.new("RGB", (w, h), c2)
    mask = Image.linear_gradient("L").resize((w,1)).resize((w,h))
    return Image.composite(top, base, mask)

def _b64_photo_to_image(b64_str, size):
    if not b64_str: return None
    try:
        payload = b64_str.split(",", 1)[1] if str(b64_str).startswith("data:image") else b64_str
        raw = base64.b64decode(payload)
        im = Image.open(BytesIO(raw)).convert("RGB")
        return im.resize(size)
    except Exception:
        return None

def _val(x, default="N/A"):
    s = "" if x is None else str(x).strip()
    return s if s else default

def _clean(v):
    """Normaliza valores: 'Fecha inválida' => 'N/A'."""
    s = _val(v)
    if INVALID_FECHA_RE.search(s):
        return "N/A"
    return s

def _kv(draw, x, y, label, value, label_w, col_w, font_label, font_value, line_h=28):
    value = _clean(value)
    value_w = col_w - label_w
    draw.text((x, y), f"{label}:", fill=(95,105,125), font=font_label)
    lines = _wrap(draw, value, font_value, value_w)
    for i, ln in enumerate(lines):
        draw.text((x + label_w, y + i*line_h), ln, fill=(20,26,36), font=font_value)
    return y + max(line_h, line_h*len(lines))

# ----------------- handler -----------------
async def seekerpdf(update, context):
    user_id = update.effective_user.id

    # Validación
    if len(context.args) != 1:
        await update.message.reply_text(
            "❗ <b>Uso correcto:</b>\n/seekerpdf <code>DNI</code>\nEjemplo: <code>/seekerpdf 44443333</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # Créditos
    if not await verifica_creditos(update, user_id, "seekerpdf"):
        return

    # Estado de cuenta (para la caption)
    username = "Desconocido"
    credits = "—"
    try:
        with open("users_db.json", "r", encoding="utf-8") as f:
            users_db = json.load(f)
        info = (users_db.get("users") or {}).get(str(user_id)) or {}
        username = info.get("username", "Desconocido")
        credits = info.get("credits", "—")
        if isinstance(credits, (int, float)):
            credits = int(credits) if credits == int(credits) else round(credits, 2)
    except Exception:
        pass

    dni = context.args[0].strip()

    # URLs
    url_dni  = f"https://web-production-da283.up.railway.app/dni?dni={dni}"
    url_telp = f"https://web-production-da283.up.railway.app/telp?tel={dni}"
    url_arg  = f"https://web-production-da283.up.railway.app/arg?dni={dni}"
    url_risk = f"https://web-production-da283.up.railway.app/risk?dni={dni}"

    # Loading
    loading = await update.message.reply_photo(
        photo="TRONCHITOBOT.png",
        caption=f"[⏳] Generando reporte PDF para DNI {escape(dni)}...",
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )

    try:
        # Llamadas
        r_dni  = requests.get(url_dni,  timeout=30)
        r_telp = requests.get(url_telp, timeout=30)
        r_arg  = requests.get(url_arg,  timeout=30)
        r_risk = requests.get(url_risk, timeout=30)

        data_dni  = (r_dni.json()  or {}).get("data", {})  if r_dni.status_code  == 200 else {}
        data_telp = (r_telp.json() or {}).get("data", {}) if r_telp.status_code == 200 else {}
        data_arg  = (r_arg.json()  or {}).get("data", {})  if r_arg.status_code  == 200 else {}
        data_risk = (r_risk.json() or {}).get("data", {}) if r_risk.status_code == 200 else {}

        # ===== DNI
        dni_resp = _clean(data_dni.get("dni") or dni)
        nombre   = _clean(data_dni.get("nombre"))
        d = data_dni.get("datos") or {}
        f_nac    = _clean(d.get("Fecha de Nacimiento"))
        edad     = _clean(d.get("Edad"))
        sexo     = _clean(d.get("Sexo"))
        estado   = _clean(d.get("Estado"))
        padre    = _clean(d.get("Padre"))
        madre    = _clean(d.get("Madre"))
        ubica    = _clean(d.get("Ubicación"))
        direc    = _clean(d.get("Dirección"))
        ub_nac   = _clean(d.get("Ubigeo Nacimiento"))
        f_fall   = _clean(d.get("Fecha de Fallecimiento"))
        foto_b64 = data_dni.get("foto") or ""

        # ===== TELP
        telefonos = data_telp.get("telefonos") or []
        # Normalizar emails
        for t in telefonos:
            em = t.get("email", "")
            if (not em) or EMAIL_PROT_RE.search(str(em)) or str(em).strip() == "":
                t["email"] = "No registrada"

        # ===== ARG
        arbol = data_arg.get("arbol") or []
        # Limpiar “fecha inválida” en campos del árbol
        for f in arbol:
            for k in list(f.keys()):
                f[k] = _clean(f.get(k))

        # ===== RISK
        riesgos = data_risk.get("riesgo") or []
        for r in riesgos:
            if not _val(r.get("descripcion")) or _val(r.get("descripcion")) in {"", "-"}:
                r["descripcion"] = "N/A"

        # ===== Tamaños/estilos
        W, M = 1700, 36
        HEADER_H = 260
        PHOTO_W, PHOTO_H = 220, 220
        PHOTO_PAD = 16
        LABEL_W = 240
        COL_GAP = 40
        LINE_H = 28

        # alturas
        block_personal_h = 170
        tel_rows = max(1, len(telefonos))
        risk_rows = max(1, len(riesgos))
        arg_rows = max(1, len(arbol))
        tel_h  = 68 + tel_rows  * 42 + 30     # +más aire entre título y subtítulos
        risk_h = 68 + risk_rows * 42 + 130
        arg_h  = 68 + arg_rows  * 68 + 30     # árbol usa filas más altas
        H = M + HEADER_H + 16 + block_personal_h + 24 + tel_h + 24 + risk_h + 24 + arg_h + M

        # Canvas
        bg = _hgrad(W, H, (245, 248, 253), (235, 241, 249))
        draw = ImageDraw.Draw(bg)

        # Fuentes
        f_h1   = _font(52)
        f_h2   = _font(28)
        f_lbl  = _font(22)
        f_txt  = _font(21)
        f_head = _font(22)          # subtítulos un poco más grandes
        f_txt_small = _font(18)     # para columnas estrechas (Ap., Nombres, Ubigeo)
        f_txt_tight = _font(20)     # para “Tipo” con interlínea más cerrada

        # ===== Encabezado
        y = M
        _rounded(draw, (M, y, W-M, y+HEADER_H), 18, fill=(255,255,255), outline=(220,225,235), width=2)

        photo_x = W - M - PHOTO_W - PHOTO_PAD
        photo_y = y + (HEADER_H - PHOTO_H)//2
        ph = _b64_photo_to_image(foto_b64, (PHOTO_W, PHOTO_H))
        if ph:
            bg.paste(ph, (photo_x, photo_y))
        else:
            _rounded(draw, (photo_x, photo_y, photo_x+PHOTO_W, photo_y+PHOTO_H), 12,
                     fill=(245,245,245), outline=(220,225,235), width=2)

        text_left  = M + 24
        text_right = photo_x - PHOTO_PAD
        text_w     = text_right - text_left

        draw.text((text_left, y+18), nombre,  fill=(14,25,44), font=f_h1)
        draw.text((text_left, y+90), dni_resp, fill=(60,70,90), font=f_h2)

        col_w = (text_w - COL_GAP) // 2
        x1, x2 = text_left, text_left + col_w + COL_GAP
        yy1 = yy2 = y + 140
        yy1 = _kv(draw, x1, yy1, "Fecha de Nacimiento", f_nac, LABEL_W, col_w, f_lbl, f_txt, LINE_H)
        yy1 = _kv(draw, x1, yy1, "Edad",                 edad, LABEL_W, col_w, f_lbl, f_txt, LINE_H)
        yy1 = _kv(draw, x1, yy1, "Sexo",                 sexo, LABEL_W, col_w, f_lbl, f_txt, LINE_H)

        yy2 = _kv(draw, x2, yy2, "Ubicación",          ubica, LABEL_W, col_w, f_lbl, f_txt, LINE_H)
        yy2 = _kv(draw, x2, yy2, "Dirección",          direc, LABEL_W, col_w, f_lbl, f_txt, LINE_H)
        yy2 = _kv(draw, x2, yy2, "Ubigeo Nacimiento",  ub_nac, LABEL_W, col_w, f_lbl, f_txt, LINE_H)

        y += HEADER_H + 16

        # ===== Datos personales
        _rounded(draw, (M, y, W-M, y+block_personal_h), 18, fill=(255,255,255), outline=(220,225,235), width=2)
        draw.text((M+24, y+18), "Datos personales", fill=(14,25,44), font=f_h2)
        col_w2 = (W - 2*M - 48 - COL_GAP) // 2
        x1 = M + 24
        x2 = x1 + col_w2 + COL_GAP
        yy1 = yy2 = y + 62
        yy1 = _kv(draw, x1, yy1, "Estado", estado, LABEL_W, col_w2, f_lbl, f_txt, LINE_H)
        yy1 = _kv(draw, x1, yy1, "Padre",  padre,  LABEL_W, col_w2, f_lbl, f_txt, LINE_H)
        yy1 = _kv(draw, x1, yy1, "Madre",  madre,  LABEL_W, col_w2, f_lbl, f_txt, LINE_H)
        yy2 = _kv(draw, x2, yy2, "F. Fallecimiento", f_fall, LABEL_W, col_w2, f_lbl, f_txt, LINE_H)

        y += block_personal_h + 24

        # ===== Tabla compacta (con más separación entre título y subtítulos)
        def draw_table(title, cols, rows, start_y, small_cols_idx=None, tight_cols_idx=None,
                       row_h=42, header_h=28):
            """
            small_cols_idx: índices de columnas con fuente pequeña (apellidos, nombres, ubigeo)
            tight_cols_idx: índices con interlínea más cerrada (p. ej. 'Tipo')
            row_h: altura de fila
            header_h: altura de la barra de encabezado
            """
            small_cols_idx = set(small_cols_idx or [])
            tight_cols_idx = set(tight_cols_idx or [])

            x1, x2 = M, W-M
            # mayor aire entre título y subtítulos:
            title_y  = start_y + 14
            header_y = start_y + 64

            # caja tabla
            table_h = (header_y - start_y) + header_h + 12 + len(rows)*row_h + 24
            _rounded(draw, (x1, start_y, x2, start_y + table_h), 18,
                     fill=(255,255,255), outline=(220,225,235), width=2)

            # título
            draw.text((x1+24, title_y), title, fill=(14,25,44), font=f_h2)

            # barra subtítulos (más “pill”)
            _rounded(draw, (x1+18, header_y, x2-18, header_y+header_h), 14, fill=(30,93,160))
            total_w = (x2 - 18) - (x1 + 18)

            # subtítulos
            acc_x = x1 + 26
            for label, frac in cols:
                wcol = int(total_w * frac)
                draw.text((acc_x+4, header_y + (header_h//2 - 10)), label, fill=(255,255,255), font=f_head)
                acc_x += wcol

            # filas
            ry = header_y + header_h + 12
            fracs = [c[1] for c in cols]
            for r in rows:
                acc_x = x1 + 24
                for c_idx, (cell, frac) in enumerate(zip(r, fracs)):
                    wcol = int(total_w * frac)
                    # selección de fuente e interlínea
                    use_font = f_txt_small if c_idx in small_cols_idx else f_txt
                    line_step = 14 if c_idx in tight_cols_idx else 20
                    max_lines = 3 if c_idx in small_cols_idx else 2
                    lines = _wrap(draw, _clean(cell), use_font, wcol-12)[:max_lines]

                    # centrado vertical dentro de la fila
                    block_h = line_step * max(1, len(lines))
                    y0 = ry + max(0, (row_h - block_h)//2)

                    for li, ln in enumerate(lines):
                        draw.text((acc_x+6, y0 + li*line_step), ln, fill=(20,26,36), font=use_font)
                    acc_x += wcol
                ry += row_h
            return start_y + table_h

        # ===== Teléfonos
        tel_cols = [("Teléfono",0.30), ("Operador",0.20), ("Periodo",0.20), ("Email",0.30)]
        tel_rows = [[_clean(t.get("telefono")), _clean(t.get("operador")),
                     _clean(t.get("periodo")),  _clean(t.get("email"))]
                    for t in telefonos] or [["—","—","—","—"]]
        y = draw_table("Teléfonos", tel_cols, tel_rows, y, row_h=42, header_h=28) + 24

        # ===== Riesgo
        risk_cols = [("Entidad",0.36), ("Moneda",0.10), ("Saldo",0.18), ("Clasificación",0.18), ("Descripción",0.18)]
        risk_rows, tot_mon = [], {}
        for rr in (riesgos or []):
            ent = _clean(rr.get("entidad"))
            mon = _clean(rr.get("moneda"))
            sal = _clean(rr.get("saldo"))
            cla = _clean(rr.get("clasificacion"))
            des = _clean(rr.get("descripcion")) or "N/A"
            try: val = Decimal(str(sal).replace(",",""))
            except (InvalidOperation, TypeError): val = Decimal("0")
            tot_mon[mon] = tot_mon.get(mon, Decimal("0")) + val
            risk_rows.append([ent, mon, sal, cla, des])
        if not risk_rows: risk_rows = [["—","—","—","—","—"]]
        y = draw_table("Riesgo", risk_cols, risk_rows, y,
                       small_cols_idx={0,4}, row_h=42, header_h=28)

        if tot_mon:
            draw.text((M+36, y+10), "Resumen por moneda:", fill=(60,70,90), font=_font(22))
            yy = y + 42
            for mon, total in tot_mon.items():
                draw.text((M+40, yy), f"{mon or '—'}: {total}", fill=(20,26,36), font=f_txt)
                yy += 26
            y = yy + 12
        y += 24

        # ===== Árbol genealógico (más alto y con 'Tipo' más junto)
        arg_cols = [
            ("DNI",      0.12),
            ("Ap. Pat.", 0.12),
            ("Ap. Mat.", 0.12),
            ("Nombres",  0.17),
            ("Edad",     0.06),
            ("Sexo",     0.08),
            ("Tipo",     0.10),
            ("Ubigeo",   0.23),
        ]  # 1.00

        arg_rows = [[
            _clean(f.get("dni")),
            _clean(f.get("apellidoPaterno")),
            _clean(f.get("apellidoMaterno")),
            _clean(f.get("nombres")),
            _clean(f.get("edad")),
            _clean(f.get("sexo")),
            _clean(f.get("tipo")),
            _clean(f.get("ubigeo")),
        ] for f in (arbol or [])] or [["—","—","—","—","—","—","—","—"]]

        # small en: Ap. Pat.(1), Ap. Mat.(2), Nombres(3), Ubigeo(7)
        # tight en: Tipo(6) -> líneas más juntas si parte
        y = draw_table("Árbol genealógico", arg_cols, arg_rows, y,
                       small_cols_idx={1,2,3,7}, tight_cols_idx={14},
                       row_h=68, header_h=28)

        # ===== Exportar PDF
        pdf_bytes = BytesIO()
        bg.save(pdf_bytes, format="PDF")
        pdf_bytes.seek(0)
        pdf_bytes.name = f"SEEKER_{dni}.pdf"

        await loading.delete()

        # Enviar PDF con estado de cuenta en la caption (mismo mensaje)
        caption = (
            f"BUSQUEDA DE SEEKER POR DNI\n\n"
            f"SEEKER PARA EL DNI <code>{escape(dni)}</code>\n\n"
            "[⚡] ESTADO DE CUENTA\n"
            f"CREDITOS ➾ <code>{credits}</code> - <code>{user_id}</code>\n"
            f"USUARIO ➾ {escape(username)}"
        )

        await update.message.reply_document(
            document=InputFile(pdf_bytes),
            filename=pdf_bytes.name,
            caption=caption,
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )

    except Exception as e:
        try:
            await loading.delete()
        except:
            pass
        await update.message.reply_text(
            f"❌ Error en generar el documento, consulte nuevamente",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )


# ------------ Validación / Normalización ------------
DOMAIN_RE = re.compile(r"^(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,63}$")

def _normalize_domain(raw: str):
    s = (raw or "").strip()
    if not s:
        return False, "Ingresa un dominio (ej. <code>example.com</code>)."
    if s.lower().startswith(("http://", "https://")):
        return False, "No uses <code>http://</code> ni <code>https://</code>. Solo el dominio (ej. <code>example.com</code>)."
    if any(c in s for c in ("/", "?", "#")):
        return False, "Solo el dominio, sin rutas ni parámetros. Ej: <code>example.com</code> o <code>www.example.com</code>"

    s = s.strip(".").lower()
    hostname = s
    root = s[4:] if s.startswith("www.") else s
    if not DOMAIN_RE.match(hostname) and not DOMAIN_RE.match(root):
        return False, "Dominio inválido. Ejemplos válidos: <code>example.com</code>, <code>www.ejemplo.pe</code>"
    canonical = hostname if DOMAIN_RE.match(hostname) else root
    return True, {"input": raw, "hostname": canonical, "root": root}

def _load_user_state(user_id):
    username, credits = "Desconocido", "—"
    try:
        with open("users_db.json", "r", encoding="utf-8") as f:
            users_db = json.load(f)
        info = (users_db.get("users") or {}).get(str(user_id)) or {}
        username = info.get("username", "Desconocido")
        credits  = info.get("credits", "—")
        if isinstance(credits, (int, float)):
            credits = int(credits) if credits == int(credits) else round(credits, 2)
    except Exception:
        pass
    return username, credits


# ----------------- /intelx -----------------
async def intelx(update, context):
    user_id = update.effective_user.id

    # 1️⃣ Validar argumento
    if len(context.args) != 1:
        await update.message.reply_text(
            "❗ <b>Uso correcto:</b>\n/intelx <code>dominio</code>\n"
            "Ejemplos: <code>example.com</code>  |  <code>www.example.com</code>\n"
            "<i>No uses http:// ni https://</i>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    # 2️⃣ Lógica de créditos
    if not await verifica_creditos(update, user_id, "intelx"):
        return

    # 3️⃣ Estado de cuenta
    username, credits = _load_user_state(user_id)

    # 4️⃣ Normalizar dominio
    raw_domain = context.args[0]
    ok, data = _normalize_domain(raw_domain)
    if not ok:
        await update.message.reply_text(
            f"[#TRONCHITOBOT] ➾ INTELX\n\n{data}\n\n"
            "[⚡] ESTADO DE CUENTA\n"
            f"CREDITOS ➾ <code>{credits}</code> - <code>{user_id}</code>\n"
            f"USUARIO ➾ {escape(username)}",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        return

    host  = data["hostname"]
    root  = data["root"]

    # 5️⃣ Imagen de espera personalizada
    loading = await update.message.reply_photo(
        photo="TRONCHITOBOT.png",
        caption=f"[⏳] Consultando <code>{escape(host)}</code> en IntelX...",
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )

    # 6️⃣ Llamada a la API
    try:
        api_url = f"https://api.milanesa.dev/v1/cloud/search?url={quote_plus(host)}"
        r = requests.get(api_url, timeout=45)
        status = r.status_code

        content_text = ""
        try:
            parsed = r.json()
            content_text = json.dumps(parsed, ensure_ascii=False, indent=2)
        except Exception:
            content_text = r.text or ""

        if not content_text:
            content_text = f"(Sin resultados o error de servidor. HTTP {status})"

        # 7️⃣ Crear archivo .txt con todo el contenido
        filename = f"{root} - Users.txt"
        txt_bytes = BytesIO(content_text.encode("utf-8", errors="replace"))
        txt_bytes.name = filename
        txt_bytes.seek(0)

        await loading.delete()

        # 8️⃣ Enviar el archivo y estado de cuenta
        caption = (
            f"[#TRONCHITOBOT] ➾ INTELX\n"
            f"Dominio ➾ <code>{escape(host)}</code>\n\n"
            f"[⚡] ESTADO DE CUENTA\n"
            f"CREDITOS ➾ <code>{credits}</code> - <code>{user_id}</code>\n"
            f"USUARIO ➾ {escape(username)}"
        )

        await update.message.reply_document(
            document=InputFile(txt_bytes),
            filename=filename,
            caption=caption,
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )

    except Exception as e:
        try:
            await loading.delete()
        except:
            pass
        await update.message.reply_text(
            f"❌ Error en /intelx: <code>{escape(str(e))}</code>",
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id
        )
        
# ------------------- AUTOEXPULSION -------------------
async def verify_admin_later(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    bot = context.bot
    try:
        member = await bot.get_chat_member(chat_id, bot.id)
        if member.status != "administrator":
            await bot.send_message(
                chat_id,
                "⚠️ No tengo permisos de administrador después de 5 minutos.\n"
                "Me retiro automáticamente por seguridad.",
                parse_mode="HTML"
            )
            await asyncio.sleep(5)
            await bot.leave_chat(chat_id)
            print(f"[🚪] Bot se autoexpulsó del grupo {chat_id}")
        else:
            print(f"[✅] Bot tiene admin en {chat_id}, se queda.")
    except Exception as e:
        print(f"[❌] Error verificando admin en {chat_id}: {e}")

# ------------------- NUEVO GRUPO -------------------
async def on_bot_added(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    chat = update.effective_chat
    my_member = update.my_chat_member

    # Verificamos que sea el bot agregado
    if my_member.new_chat_member.user.id != bot.id:
        return

    status = my_member.new_chat_member.status
    if status in ("member", "restricted"):
        await bot.send_message(
            chat.id,
            "👋 ¡Gracias por agregarme al grupo!\n\n"
            "Para funcionar correctamente necesito permisos de <b>administrador</b>.\n"
            "Si en 5 minutos no me los otorgan, me retiraré automáticamente.",
            parse_mode="HTML"
        )
        # Programar verificación en 5 minutos
        context.job_queue.run_once(verify_admin_later, when=300, chat_id=chat.id)
    elif status == "administrator":
        print(f"[✅] Bot agregado como admin al grupo {chat.id}")

# ------------------- GRUPOS REGISTRADOS AL INICIAR -------------------
async def check_groups_on_start(app):
    try:
        with open("users_db.json", "r", encoding="utf-8") as f:
            db = json.load(f)
        groups = db.get("groups", {})

        for chat_id_str in groups.keys():
            chat_id = int(chat_id_str)
            try:
                member = await app.bot.get_chat_member(chat_id, app.bot.id)
                if member.status != "administrator":
                    await app.bot.send_message(
                        chat_id,
                        "⚠️ No tengo permisos de administrador.\n"
                        "Si no me dan admin, me retiraré en 5 minutos.",
                        parse_mode="HTML"
                    )
                    app.job_queue.run_once(verify_admin_later, when=300, chat_id=chat_id)
                else:
                    print(f"[✅] Bot tiene admin en grupo {chat_id}")
            except Exception as e:
                print(f"[❌] Error verificando grupo {chat_id}: {e}")
    except FileNotFoundError:
        print("[⚠️] No se encontró users_db.json")


# ----------- INICIALIZACIÓN DEL BOT -----------

aplication = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN") or "8439214411:AAGZpGYeTV3JSLPEtPwhd1NbTLrD46Caz_o").build()

aplication.add_handler(CommandHandler("start", inicio))
aplication.add_handler(CommandHandler("register", registro))
aplication.add_handler(CommandHandler("me", information))
aplication.add_handler(CommandHandler("cmds", cmds))
aplication.add_handler(CommandHandler("dnis", dnis))
aplication.add_handler(CommandHandler("nm", nm))
aplication.add_handler(CommandHandler("ftv", ftv))
aplication.add_handler(CommandHandler("ag",ag))
aplication.add_handler(CommandHandler("agv",agv))
aplication.add_handler(CommandHandler("agvp",agvp))
aplication.add_handler(CommandHandler("denuncias",denuncias))
aplication.add_handler(CommandHandler("denunciasv",denunciasv))
aplication.add_handler(CommandHandler("telp", telp))
aplication.add_handler(CommandHandler("cel", cel))
aplication.add_handler(CommandHandler("osiptel", osiptel))
aplication.add_handler(CommandHandler("placa", placa))
aplication.add_handler(CommandHandler("riesgos", riesgos))
aplication.add_handler(CommandHandler("taj", taj))
aplication.add_handler(CommandHandler("seeker",seeker))
aplication.add_handler(CommandHandler("seekerpdf",seekerpdf))
aplication.add_handler(CommandHandler("intelx", intelx))
aplication.add_handler(CommandHandler("cred", cred))
aplication.add_handler(CommandHandler("uncred", uncred))
aplication.add_handler(CommandHandler("sub", sub))
aplication.add_handler(CommandHandler("unsub", unsub))
aplication.add_handler(CommandHandler("grupopremium", addgroupremium))
aplication.add_handler(CommandHandler("ungrupopremium", removegroupremium))
aplication.add_handler(CommandHandler("infogrupo", infogrupo))
aplication.add_handler(CommandHandler("info", info))
aplication.add_handler(CommandHandler("seller", seller))
aplication.add_handler(CommandHandler("unseller", unseller))
aplication.add_handler(CommandHandler("buy", buy))
aplication.add_handler(CommandHandler("terminos", terminos))
aplication.add_handler(CommandHandler("delete", delete))
aplication.add_handler(CommandHandler("anuncio", anuncio))
aplication.add_handler(ChatMemberHandler(auto_register_group, chat_member_types=ChatMemberHandler.MY_CHAT_MEMBER))
aplication.add_handler(ChatMemberHandler(on_bot_added, chat_member_types=ChatMemberHandler.MY_CHAT_MEMBER))
aplication.add_handler(MessageHandler(filters.ALL & (~filters.StatusUpdate.ALL), auto_register_group_on_message))   
aplication.add_handler(CallbackQueryHandler(callback_handler)) 
aplication.run_polling(allowed_updates=Update.ALL_TYPES)
