import json
import os
from datetime import datetime

DATABASE_FILE = "users_db.json"

# 🔹 Configuración general
DEFAULT_CREDITS = 5            # Créditos que recibe un usuario nuevo
DEFAULT_ROLE = "user"          # Rol por defecto
DEFAULT_PLAN = "Free"          # Plan por defecto

# 🔹 Admin principal
ADMIN_USER_ID = 6251510385     # Tu ID real de Telegram
SELLER_MAX_CREDITS = 2000      # Tope para sellers

class UserDB:
    def __init__(self, db_path=DATABASE_FILE):
        self.db_path = db_path
        self.data = {"users": {}, "groups": {}}
        self._load()

    # 🔹 Carga de la base de datos
    def _load(self):
        if os.path.exists(self.db_path):
            with open(self.db_path, "r", encoding="utf-8") as f:
                try:
                    self.data = json.load(f)
                except Exception:
                    self.data = {"users": {}, "groups": {}}
        else:
            self.data = {"users": {}, "groups": {}}

        if "users" not in self.data:
            self.data["users"] = {}
        if "groups" not in self.data:
            self.data["groups"] = {}

        # 🔹 Inicializar audit_log en usuarios existentes
        for u in self.data["users"].values():
            if "audit_log" not in u:
                u["audit_log"] = []

    # 🔹 Guardar cambios en la base de datos
    def _save(self):
        if "users" not in self.data:
            self.data["users"] = {}
        if "groups" not in self.data:
            self.data["groups"] = {}
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    # =============================
    # 👤 SECCIÓN DE USUARIOS
    # =============================

    def register_user(self, user_id, username="", first_name="", last_name=""):
        user_id_str = str(user_id)
        is_admin = user_id == ADMIN_USER_ID

        if user_id_str in self.data["users"]:
            self.data["users"][user_id_str]["username"] = username or ""
            self.data["users"][user_id_str]["first_name"] = first_name or ""
            self.data["users"][user_id_str]["last_name"] = last_name or ""
            if "audit_log" not in self.data["users"][user_id_str]:
                self.data["users"][user_id_str]["audit_log"] = []
            self._save()
            return False

        self.data["users"][user_id_str] = {
            "username": username or "",
            "first_name": first_name or "",
            "last_name": last_name or "",
            "credits": "♾️" if is_admin else DEFAULT_CREDITS,
            "role": "admin" if is_admin else DEFAULT_ROLE,
            "plan": "Premium" if is_admin else DEFAULT_PLAN,
            "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "audit_log": [],
            "consultas": 0,
            "consultas_hoy": 0,
            "consultas_hoy_fecha": datetime.now().strftime("%Y-%m-%d")
        }
        self._save()
        return True

    def get_user(self, user_id):
        return self.data["users"].get(str(user_id))

    def update_credits(self, user_id, amount, tipo="accion", motivo=""):
        user_id_str = str(user_id)
        user = self.get_user(user_id_str)
        if not user:
            return False

        if "audit_log" not in user:
            user["audit_log"] = []

        # 🔹 Admin siempre tiene ♾️
        if user.get("role") == "admin":
            user["credits"] = "♾️"
        # 🔹 Caso especial: Créditos ilimitados
        elif str(amount).upper() in ["ILIMITADOS", "♾️"]:
            user["credits"] = "♾️"
        # 🔹 Sellers con tope
        elif user.get("role") == "seller":
            try:
                user["credits"] = min(
                    SELLER_MAX_CREDITS,
                    max(0, float(user.get("credits", 0)) + float(amount))
                )
            except ValueError:
                user["credits"] = 0
        # 🔹 Usuarios normales
        else:
            try:
                user["credits"] = max(0, float(user.get("credits", 0)) + float(amount))
            except ValueError:
                user["credits"] = 0

        # 🔹 Registrar auditoría
        user["audit_log"].append({
            "timestamp": datetime.now().isoformat(),
            "tipo": tipo,
            "motivo": motivo,
            "cantidad": amount
        })

        self._save()
        return True

    def consume_credits(self, user_id, amount=1, tipo="consulta", motivo=""):
        user_id_str = str(user_id)
        user = self.get_user(user_id_str)
        if not user:
            return False

        if user.get("credits") == "♾️" or user.get("role") == "admin":
            return True

        if float(user.get("credits", 0)) >= amount:
            self.update_credits(user_id, -amount, tipo, motivo)
            return True
        return False

    def set_role(self, user_id, role):
        user_id_str = str(user_id)
        if user_id_str in self.data["users"]:
            if self.data["users"][user_id_str]["role"] == "admin" and role != "admin":
                self.data["users"][user_id_str]["credits"] = DEFAULT_CREDITS
            if role == "seller":
                self.data["users"][user_id_str]["credits"] = SELLER_MAX_CREDITS
            self.data["users"][user_id_str]["role"] = role
            self._save()
            return True
        return False

    def set_subscription(self, user_id, plan):
        user_id_str = str(user_id)
        if user_id_str in self.data["users"]:
            self.data["users"][user_id_str]["plan"] = plan
            self._save()
            return True
        return False

    def set_expiration(self, user_id, expiration_date):
        """Establece la fecha de expiración de la suscripción de un usuario."""
        user_id_str = str(user_id)
        user = self.get_user(user_id_str)
        if not user:
            return False

        user["expiration"] = expiration_date.isoformat()

        if "audit_log" not in user:
            user["audit_log"] = []

        user["audit_log"].append({
            "timestamp": datetime.now().isoformat(),
            "tipo": "set_expiration",
            "motivo": "Se estableció fecha de expiración",
            "cantidad": None
        })

        self._save()
        return True

    def reset_subscription(self, user_id, default_plan=DEFAULT_PLAN, default_role=DEFAULT_ROLE, default_credits=DEFAULT_CREDITS):
        """Resetea plan y créditos al valor por defecto y registra auditoría."""
        user_id_str = str(user_id)
        user = self.get_user(user_id_str)
        if not user:
            return False

        user["plan"] = default_plan
        user["role"] = default_role
        user["credits"] = default_credits

        if "audit_log" not in user:
            user["audit_log"] = []

        user["audit_log"].append({
            "timestamp": datetime.now().isoformat(),
            "tipo": "reset_subscription",
            "motivo": "Suscripción reseteada",
            "cantidad": default_credits
        })

        self._save()
        return True

    def has_subscription(self, user_id):
        user = self.get_user(user_id)
        if user:
            return user.get("plan", "Free") == "Premium"
        return False

    # =============================
    # 📊 SECCIÓN DE CONSULTAS DE USUARIO
    # =============================

    def increment_consultas(self, user_id, cantidad=1):
        """
        Incrementa el contador total de consultas de un usuario.
        """
        user_id_str = str(user_id)
        user = self.get_user(user_id_str)
        if not user:
            return False

        user["consultas"] = int(user.get("consultas", 0)) + cantidad
        self._save()
        return True

    def increment_consultas_hoy(self, user_id, cantidad=1):
        """
        Incrementa el contador de consultas del día de un usuario.
        Reinicia automáticamente si cambia el día.
        """
        user_id_str = str(user_id)
        user = self.get_user(user_id_str)
        if not user:
            return False

        today_str = datetime.now().strftime("%Y-%m-%d")
        if user.get("consultas_hoy_fecha") != today_str:
            user["consultas_hoy"] = 0
            user["consultas_hoy_fecha"] = today_str

        user["consultas_hoy"] = int(user.get("consultas_hoy", 0)) + cantidad
        self._save()
        return True

    def get_consultas(self, user_id):
        """
        Retorna consultas totales y consultas del día.
        Reinicia el contador diario si cambió la fecha.
        """
        user = self.get_user(user_id)
        if not user:
            return 0, 0

        today_str = datetime.now().strftime("%Y-%m-%d")
        if user.get("consultas_hoy_fecha") != today_str:
            user["consultas_hoy"] = 0
            user["consultas_hoy_fecha"] = today_str
            self._save()

        return int(user.get("consultas", 0)), int(user.get("consultas_hoy", 0))

    def registrar_consulta(self, user_id, cantidad=1):
        """
        Incrementa ambos: consultas totales y del día para el usuario.
        Úsalo cuando el usuario realiza una consulta exitosa.
        """
        self.increment_consultas(user_id, cantidad)
        self.increment_consultas_hoy(user_id, cantidad)

    # =============================
    # 👥 SECCIÓN DE GRUPOS
    # =============================

    def get_group(self, group_id):
        if "groups" not in self.data:
            self.data["groups"] = {}
        return self.data["groups"].get(str(group_id))

    def set_group_subscription(self, group_id, plan):
        """
        Registra un grupo o actualiza su plan.
        Funciona con cualquier ID entero, incluidos los negativos.
        """
        try:
            group_id_int = int(group_id)
            # ✅ No rechazamos números negativos (Telegram usa IDs negativos para supergrupos)
        except ValueError:
            return False

        group_id_str = str(group_id)
        if "groups" not in self.data:
            self.data["groups"] = {}

        if group_id_str not in self.data["groups"]:
            self.data["groups"][group_id_str] = {
                "chat_id": group_id_int,  # Se guarda el chat_id
                "plan": plan,
                "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        else:
            # Actualiza plan si ya existe
            self.data["groups"][group_id_str]["plan"] = plan
            if "chat_id" not in self.data["groups"][group_id_str]:
                self.data["groups"][group_id_str]["chat_id"] = group_id_int

        self._save()
        return True

    def has_group_subscription(self, group_id):
        group = self.get_group(group_id)
        if group:
            return group.get("plan", "Free") == "Premium"
        return False

    def set_group_premium(self, group_id):
        return self.set_group_subscription(group_id, "Premium")

    def remove_group_premium(self, group_id):
        return self.set_group_subscription(group_id, "Free")

# 🔹 Instancia global
user_db = UserDB()