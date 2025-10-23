from telegram import InputFile, Update
from telegram.ext import ContextTypes
from database import user_db, ADMIN_USER_ID

async def anuncio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ No tienes permisos para usar este comando.")
        return

    if not context.args:
        await update.message.reply_text("❗ Uso: /broadcast <mensaje>")
        return

    mensaje = " ".join(context.args)
    enviados = 0
    fallidos = []

    # 🔹 Enviar a usuarios
    for user_id in list(user_db.data.get("users", {})):
        try:
            with open("TRONCHITOBOT.png", "rb") as f:
                await context.bot.send_photo(
                    chat_id=int(user_id),
                    photo=InputFile(f),
                    caption=f"📢 <b>ANUNCIO</b>\n\n{mensaje}",
                    parse_mode="HTML"
                )
            enviados += 1
        except Exception as e:
            fallidos.append(f"Usuario {user_id}: {e}")

    # 🔹 Enviar a grupos
    for group_id, group_data in list(user_db.data.get("groups", {}).items()):
        try:
            chat_id = group_data.get("chat_id", int(group_id))
            with open("TRONCHITOBOT.png", "rb") as f:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=InputFile(f),
                    caption=f"📢 <b>ANUNCIO IMPORTANTE !!!</b>\n\n{mensaje}",
                    parse_mode="HTML"
                )
            enviados += 1
        except Exception as e:
            fallidos.append(f"Grupo {group_id}: {e}")

    # 🔹 Responder con resumen
    reply_text = f"✅ Anuncio enviado.\n📤 Enviados: {enviados}\n"
    if fallidos:
        reply_text += "⚠️ Fallidos:\n" + "\n".join(fallidos)

    await update.message.reply_text(reply_text, parse_mode="HTML")

# ==============================
# 🤖 Registro automático de grupos nuevos
# ==============================
async def auto_register_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    new_status = update.my_chat_member.new_chat_member.status

    if chat.type in ["group", "supergroup"] and new_status in ["member", "administrator"]:
        user_db.set_group_subscription(chat.id, "Free")
        print(f"📌 Grupo registrado automáticamente: {chat.title} ({chat.id})")

# ==============================
# 📥 Registro de grupos antiguos mediante mensajes
# ==============================
async def auto_register_group_on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type in ["group", "supergroup"]:
        if not user_db.get_group(chat.id):
            user_db.set_group_subscription(chat.id, "Free")
            print(f"📌 Grupo registrado desde mensaje: {chat.title} ({chat.id})")
