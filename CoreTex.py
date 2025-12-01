import pandas as pd
import numpy as np
import google.generativeai as genai
import json
import re
import matplotlib.pyplot as plt
import seaborn as sns
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dense, Embedding, LSTM, concatenate
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from sklearn.preprocessing import StandardScaler
import os
import unicodedata
import time # <--- IMPORTANTE PARA DARLE RESPIRO A LA API

# --- CONFIGURACIÓN ---
API_KEY = os.getenv("AIzaSyAfTpyNJYdSqZJtZme8jo06IhEWKwNWzLI")
try:
    genai.configure(api_key=API_KEY)
    model_gemini = genai.GenerativeModel('gemini-1.5-flash')
    print("✅ Gemini: CONECTADO")
except:
    model_gemini = None

MAX_LEN = 50
MAX_VOCAB = 5000
global_tokenizer = None
global_scaler = None

# ==========================================
# 🛠️ HERRAMIENTAS
# ==========================================

def anonimizar_regex(texto):
    if not isinstance(texto, str): return str(texto)
    texto = re.sub(r'http[s]?://\S+|www\.\S+', '<URL>', texto)
    texto = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '<EMAIL>', texto)
    texto = re.sub(r'\b(?:\d{4}[ -]?){3,4}\d{1,4}\b', '<TARJETA>', texto)
    texto = re.sub(r'\b\d{7,15}\b', '<TEL>', texto)
    texto = re.sub(r'(?i)\b(contraseña|password|clave|pin)\s*[:=]?\s+(\S+)', r'\1 <SECRETO>', texto)
    return texto

def extraer_metadatos(texto):
    datos = { "nombre": "Cliente", "email": "No detectado", "ticket_ref": f"GEN-{np.random.randint(1000,9999)}" }
    
    match_email = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', texto)
    if match_email:
        datos['email'] = match_email.group(0)
        if datos['nombre'] == "Cliente":
            datos['nombre'] = datos['email'].split('@')[0].replace('.', ' ').title()

    match_nombre = re.search(r'(?i)(?:soy|nombre es|me llamo)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)', texto)
    if match_nombre: datos['nombre'] = match_nombre.group(1)

    match_ticket = re.search(r'(?i)(?:ticket|caso|folio|ref)[:\s#]+(\d+)', texto)
    if match_ticket: datos['ticket_ref'] = f"REF-{match_ticket.group(1)}"
    
    return datos

def generar_respuesta_sugerida(texto_original, tipo_ticket, accion):
    """
    Intenta usar IA. Si falla, usa una PLANTILLA profesional.
    """
    
    # 1. PLANTILLAS DE RESPALDO (Por si la IA falla)
    templates = {
        "FUGA": f"Estimado cliente,\n\nEntendemos su frustración y le pedimos sinceras disculpas. Su caso ha sido escalado a Gerencia como PRIORIDAD MÁXIMA.\n\nEn los próximos 10 minutos recibirá una llamada de nuestro Director de Cuentas para ofrecerle una solución inmediata.\n\nAtentamente,\nEquipo de Retención.",
        "VENTA": f"Hola,\n\n¡Gracias por su interés! Nos alegra saber que desea expandir sus servicios con nosotros.\n\nHe notificado a nuestro equipo comercial y le enviaremos la cotización solicitada a su correo en breve. ¿Tiene disponibilidad hoy para una breve llamada?\n\nSaludos,\nEquipo de Ventas.",
        "PHISHING": f"ALERTA DE SEGURIDAD:\n\nHemos detectado que este mensaje contiene enlaces o solicitudes sospechosas. Por su seguridad, NO haga clic en ningún enlace ni descargue archivos.\n\nNuestro equipo de seguridad informática ya está investigando el origen de este mensaje.\n\nSoporte de Seguridad.",
        "MEDIO": f"Estimado cliente,\n\nLamentamos que su experiencia no haya sido la esperada. Valoramos mucho su feedback.\n\nVamos a revisar su caso detalladamente para asegurar que esto no vuelva a ocurrir. Nos pondremos en contacto pronto con una actualización.\n\nSoporte al Cliente.",
        "SOPORTE": f"Hola,\n\nHemos recibido su solicitud y se ha generado un ticket de soporte. Un agente técnico revisará su caso y le responderá lo antes posible.\n\nGracias por contactarnos."
    }

    # Seleccionar template base
    template_backup = templates.get("SOPORTE")
    if "FUGA" in tipo_ticket or "CRÍTICO" in tipo_ticket: template_backup = templates["FUGA"]
    elif "VENTA" in tipo_ticket: template_backup = templates["VENTA"]
    elif "PHISHING" in tipo_ticket: template_backup = templates["PHISHING"]
    elif "MEDIO" in tipo_ticket or "DECEPCIONADO" in accion: template_backup = templates["MEDIO"]

    # 2. INTENTAR CON IA
    if model_gemini:
        try:
            # Pausa de 1 segundo para no saturar a Google (Evita el error 429)
            time.sleep(1.0) 
            
            prompt = f"""
            Actúa como agente de soporte. Redacta respuesta corta para:
            Mensaje: "{texto_original}"
            Contexto: {tipo_ticket} - {accion}
            """
            res = model_gemini.generate_content(prompt)
            return res.text.strip()
        except Exception as e:
            print(f"⚠️ IA Ocupada ({e}). Usando plantilla.")
            return template_backup # <--- AQUÍ ESTÁ EL TRUCO: DEVOLVEMOS LA PLANTILLA
    
    return template_backup

# ==========================================
# 🧠 CEREBRO ANALÍTICO
# ==========================================

def procesar_ticket_inteligente(texto):
    info = { "phishing": False, "tipo_ticket": "Soporte", "sentimiento_valor": 0.5, "sentimiento_etiqueta": "Neutral", "riesgo_extra": 0.0 }
    try:
        if model_gemini:
            prompt = f"""Analiza INTENCIÓN: "{texto}". JSON: {{ "phishing": bool, "tipo_ticket": str, "sentimiento_valor": float, "sentimiento_etiqueta": str, "riesgo_calculado": float }}"""
            res = model_gemini.generate_content(prompt)
            clean = res.text.replace("```json", "").replace("```", "").strip()
            match = re.search(r'\{.*\}', clean, re.DOTALL)
            if match: info.update(json.loads(match.group(0)))
    except: pass
    return info

def recomendar_accion(risk, sent, phishing):
    if phishing: return "🛑 BLOQUEO DE SEGURIDAD"
    if risk >= 90: return "🔥 ALERTA ROJA: RETENCIÓN INMEDIATA"
    elif risk >= 40: return "⚠️ ALERTA AMARILLA: SEGUIMIENTO"
    elif sent > 0.8: return "⭐ OPORTUNIDAD VENTA"
    else: return "✅ SOPORTE ESTÁNDAR"

# --- ENTRENAMIENTO ---
def preparar_datos_simulados(df):
    n = len(df)
    df['antiguedad'] = np.random.randint(1, 48, n)
    df['tiempo'] = np.random.randint(1, 72, n)
    df['target_churn'] = np.random.randint(0, 100, n)
    return df

def entrenar_modelo_completo(df):
    global global_tokenizer, global_scaler
    print("🧠 Entrenando Keras Local...")
    global_tokenizer = Tokenizer(num_words=MAX_VOCAB, oov_token="<OOV>")
    global_tokenizer.fit_on_texts(df['Texto_Ticket'].astype(str))
    X_text = pad_sequences(global_tokenizer.texts_to_sequences(df['Texto_Ticket'].astype(str)), maxlen=MAX_LEN, padding='post')
    global_scaler = StandardScaler()
    if 'sentimiento' not in df.columns: df['sentimiento'] = 0.5
    X_meta = global_scaler.fit_transform(df[['sentimiento', 'antiguedad', 'tiempo']])
    y = df['target_churn'].values
    in_text = Input(shape=(MAX_LEN,))
    emb = Embedding(MAX_VOCAB, 16)(in_text)
    lstm = LSTM(32)(emb)
    in_meta = Input(shape=(3,))
    dense = Dense(16, activation='relu')(in_meta)
    concat = concatenate([lstm, dense])
    out = Dense(1, activation='linear')(concat)
    model = Model(inputs=[in_text, in_meta], outputs=out)
    model.compile(optimizer='adam', loss='mse')
    model.fit([X_text, X_meta], y, epochs=3, verbose=0)
    return model, global_tokenizer, global_scaler