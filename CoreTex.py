import google.generativeai as genai
import json
import re
import os
import numpy as np
import time

# --- TU API KEY ---
API_KEY = os.getenv("AIzaSyAfTpyNJYdSqZJtZme8jo06IhEWKwNWzLI")

try:
    genai.configure(api_key=API_KEY)
    model_gemini = genai.GenerativeModel('gemini-1.5-flash')
    print("✅ CoreTex AI: MODO EMPÁTICO ACTIVO")
except:
    model_gemini = None
    print("⚠️ CoreTex AI: MODO OFFLINE")

# --- HERRAMIENTAS ---
def extraer_metadatos(texto):
    email = re.search(r'[\w\.-]+@[\w\.-]+', texto)
    nombre = "Cliente"
    if "Soy" in texto or "soy" in texto:
        try:
            parts = re.split(r'soy|Soy', texto)
            if len(parts) > 1:
                nombre = parts[1].split(",")[0].strip().split(".")[0]
        except: pass
    
    return {
        'email': email.group(0) if email else "no-email@vortex.ai",
        'nombre': nombre,
        'ticket_ref': f"REF-{np.random.randint(1000, 9999)}"
    }

def anonimizar_regex(texto):
    texto = re.sub(r'[\w\.-]+@[\w\.-]+', '🔒<EMAIL_OCULTO>', texto)
    texto = re.sub(r'\b\d{7,10}\b', '🔒<TEL_OCULTO>', texto)
    return texto

# --- MOTOR DE ANÁLISIS ---
def procesar_ticket_inteligente(texto_ticket):
    if not model_gemini: return _respuesta_dummy()

    prompt = f"""
    Analiza este ticket: "{texto_ticket}"
    
    REGLAS:
    1. Si hay quejas de lentitud, error o fallos -> EMOCION: "FRUSTRACION".
    2. Si hay amenazas de irse, estafa o insultos -> EMOCION: "IRA".
    3. Si es compra o pregunta -> EMOCION: "NEUTRAL" o "INTERES".

    Responde SOLO JSON:
    {{
        "emocion": "IRA, FRUSTRACION, URGENCIA, NEUTRAL, FELICIDAD",
        "intensidad": 1-10,
        "intencion": "SOPORTE, BAJA, VENTA, PHISHING",
        "es_phishing": boolean
    }}
    """

    try:
        response = model_gemini.generate_content(prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)
        
        base_riesgo = {
            "IRA": 90, "FRUSTRACION": 70, "URGENCIA": 60,
            "TRISTEZA": 40, "NEUTRAL": 10, "FELICIDAD": 0
        }
        
        emocion = data.get("emocion", "NEUTRAL").upper()
        intensidad = int(data.get("intensidad", 5))
        riesgo = base_riesgo.get(emocion, 20) + (intensidad * 2)
        
        if "no funciona" in texto_ticket.lower() or "error" in texto_ticket.lower():
            riesgo = max(riesgo, 60)

        riesgo = min(riesgo, 100)

        return {
            'riesgo_extra': float(riesgo),
            'sentimiento_valor': intensidad / 10,
            'sentimiento_etiqueta': emocion,
            'tipo_ticket': data.get("intencion", "SOPORTE").upper(),
            'phishing': data.get("es_phishing", False),
            'intencion': data.get("intencion", "")
        }

    except Exception as e:
        print(f"Error IA: {e}")
        return _respuesta_dummy()

def _respuesta_dummy():
    return {'riesgo_extra': 50.0, 'sentimiento_valor': 0.5, 'sentimiento_etiqueta': "NEUTRAL", 'tipo_ticket': "SOPORTE", 'phishing': False}

def recomendar_accion(riesgo, sentimiento, phishing):
    if phishing: return "🛑 BLOQUEO TOTAL"
    if riesgo >= 85: return "🔥 CONTENCIÓN DE FUGA"
    if riesgo >= 60: return "🛠️ SOPORTE PRIORITARIO"
    return "✅ ATENCIÓN ESTÁNDAR"

# --- GENERADOR DE RESPUESTAS (AQUÍ ESTÁ EL CAMBIO) ---
def generar_respuesta_sugerida(texto, tipo, accion):
    
    # 1. INTENTO CON IA (Plan A - Personalizado)
    if model_gemini:
        prompt = f"""
        Actúa como un agente de soporte senior. Redacta una respuesta para este cliente.
        Cliente dice: "{texto}"
        Contexto: {tipo} | Acción: {accion}

        REGLAS DE TONO (OBLIGATORIAS):
        - Si es FUGA o IRA: NO des las gracias. Pide disculpas sinceras y di que un gerente lo verá ya.
        - Si es FALLA TÉCNICA: Sé directo. "Entendemos el problema, ingeniería ya está revisando".
        - Si es PHISHING: Sé autoritario. "Alerta de seguridad. No toque nada".
        - NUNCA uses frases genéricas como "Gracias por su mensaje".

        Respuesta (Máx 30 palabras):
        """
        try:
            return model_gemini.generate_content(prompt).text.strip()
        except:
            pass # Si falla la IA, pasamos al Plan B (Abajo)

    # 2. PLAN B: PLANTILLAS TÁCTICAS (Si la IA falla, usa esto)
    tipo_upper = str(tipo).upper()
    
    if "PHISHING" in tipo_upper:
        return "⚠️ ALERTA: Hemos detectado un enlace peligroso. Por su seguridad, no haga clic y cambie su contraseña."
    
    if "FUGA" in tipo_upper or "IRA" in tipo_upper or "ESTAFA" in texto.upper():
        return "Lamentamos profundamente su experiencia. He escalado su caso como PRIORIDAD CRÍTICA a la gerencia."
    
    if "FALLA" in tipo_upper or "TECNICA" in tipo_upper or "FRUSTRACION" in tipo_upper:
        return "Entendemos el inconveniente técnico. Nuestro equipo de ingeniería ya está revisando los logs de su cuenta."
    
    if "VENTA" in tipo_upper or "OPORTUNIDAD" in tipo_upper:
        return "¡Excelente! Un ejecutivo comercial le enviará la propuesta personalizada en breve."

    return "Hemos recibido su solicitud. Un agente especializado está revisando los detalles."

# Dummies
def entrenar_modelo_completo(df): return None, None, None
def preparar_datos_simulados(df): return df