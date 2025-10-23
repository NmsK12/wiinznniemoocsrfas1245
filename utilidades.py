import re

def formatea_titulares(titulares_raw):
    if not titulares_raw:
        return "No registrado"
    # Quita comillas simples y dobles, espacios extra
    t = titulares_raw.replace('"', '').replace("\\", '').strip()
    # Reemplaza varias comillas simples seguidas por una sola
    t = re.sub(r"'+", "'", t)
    # Separa por comillas simples que preceden a una mayúscula (inicio de nombre)
    nombres = re.split(r"'\s*(?=[A-ZÁÉÍÓÚÑ])", t)
    # Limpia espacios y descarta vacíos
    nombres = [n.strip(" '") for n in nombres if n.strip(" '")]
    # Devuelve con viñetas
    if nombres:
        return '\n'.join(f"• {n}" for n in nombres)
    else:
        return titulares_raw.strip()