from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.sequence import pad_sequences
import uvicorn
import os
import sqlite3 
from datetime import datetime
import CoreTex

app = FastAPI(title="Vortex Sentinel API", version="Manager CRM Edition")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- BASE DE DATOS (CRM & KPIS) ---
def init_db():
    conn = sqlite3.connect('historial_vortex.db')
    c = conn.cursor()
    # Estructura completa: Fecha, Texto Original, Anonimizado, Tipo, Riesgo, Acción, Usuario, Email, Referencia
    c.execute('''CREATE TABLE IF NOT EXISTS tickets
                 (fecha TEXT, original TEXT, anonimo TEXT, tipo TEXT, riesgo REAL, accion TEXT, 
                  usuario TEXT, email TEXT, ref TEXT)''')
    conn.commit()
    conn.close()

def guardar_ticket_db(original, anonimo, tipo, riesgo, accion, usuario, email, ref):
    try:
        conn = sqlite3.connect('historial_vortex.db')
        c = conn.cursor()
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO tickets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                  (fecha, original, anonimo, tipo, riesgo, accion, usuario, email, ref))
        conn.commit()
        conn.close()
        print("💾 Guardado en DB.")
    except Exception as e: print(f"⚠️ Error DB: {e}")

# Variables Globales
api_model = None
api_tokenizer = None
api_scaler = None

class TicketInput(BaseModel):
    texto: str

class TicketOutput(BaseModel):
    ticket_id: str
    usuario: str
    email_usuario: str
    texto_anonimizado: str
    tipo_ticket: str
    emocion: str
    riesgo_churn: float
    es_phishing: bool
    accion_recomendada: str
    respuesta_sugerida: str

@app.on_event("startup")
def load_brain():
    global api_model, api_tokenizer, api_scaler
    init_db()
    print("🧠 Iniciando Vortex Sentinel CRM...")
    filename = 'dataset_tickets.csv'
    df = None 
    if os.path.exists(filename):
        try: df = pd.read_csv(filename)
        except: pass
    if df is None: df = pd.DataFrame({'Texto_Ticket': ['ejemplo'], 'sentimiento': [0.5], 'target_churn': [0]})
    if 'description' in df.columns: df.rename(columns={'description': 'Texto_Ticket'}, inplace=True)
    if 'body' in df.columns: df.rename(columns={'body': 'Texto_Ticket'}, inplace=True)
    df = CoreTex.preparar_datos_simulados(df)
    try:
        api_model, api_tokenizer, api_scaler = CoreTex.entrenar_modelo_completo(df)
        print("✅ Cerebro Cargado.")
    except Exception as e: print(f"❌ Error carga: {e}")

# --- ENDPOINTS DE DATOS ---

@app.get("/ver_historial")
def ver_historial():
    try:
        conn = sqlite3.connect('historial_vortex.db')
        c = conn.cursor()
        c.execute("SELECT * FROM tickets ORDER BY fecha DESC LIMIT 50")
        filas = c.fetchall()
        conn.close()
        historial = []
        for f in filas:
            historial.append({
                "fecha": f[0], "original": f[1], "anonimo": f[2], 
                "tipo": f[3], "riesgo": f[4], "accion": f[5],
                "usuario": f[6], "email": f[7], "ref": f[8]
            })
        return historial
    except Exception as e: return {"error": str(e)}

@app.delete("/borrar_historial")
def borrar_historial():
    try:
        conn = sqlite3.connect('historial_vortex.db')
        c = conn.cursor()
        c.execute("DELETE FROM tickets"); conn.commit(); conn.close()
        return {"mensaje": "Historial borrado"}
    except Exception as e: return {"error": str(e)}

@app.get("/datos_grafica")
def datos_grafica():
    """Devuelve datos para la gráfica Y LOS KPIs."""
    try:
        conn = sqlite3.connect('historial_vortex.db')
        c = conn.cursor()
        
        # 1. Datos Gráfica
        c.execute("SELECT riesgo, fecha FROM tickets ORDER BY fecha DESC LIMIT 20")
        data = c.fetchall()
        riesgos = [x[0] for x in reversed(data)]
        fechas = [x[1].split(' ')[1] for x in reversed(data)]
        
        # 2. KPIs (Contadores)
        c.execute("SELECT COUNT(*) FROM tickets")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM tickets WHERE riesgo >= 80 OR tipo LIKE '%PHISHING%'")
        criticos = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM tickets WHERE tipo LIKE '%VENTA%'")
        ventas = c.fetchone()[0]
        
        conn.close()
        
        return {
            "riesgos": riesgos, "fechas": fechas,
            "kpi_total": total, "kpi_criticos": criticos, "kpi_ventas": ventas
        }
    except: return {"riesgos": [], "fechas": [], "kpi_total": 0, "kpi_criticos": 0, "kpi_ventas": 0}

# --- ENDPOINT ANALISIS ---
@app.post("/analizar_ticket", response_model=TicketOutput)
def analizar_ticket(ticket: TicketInput):
    texto_upper = ticket.texto.upper()
    meta = CoreTex.extraer_metadatos(ticket.texto)
    texto_limpio = CoreTex.anonimizar_regex(ticket.texto)

    # FILTRO 1: PHISHING
    patrones = ["HTTP", "BIT.LY", "EXPIRA", "ACTUALIZAR", "PASSWORD", "CREDENCIALES"]
    if "HTTP" in texto_upper or any(p in texto_upper for p in patrones):
        return crear_respuesta(meta, texto_limpio, "PHISHING", 100.0, "AMENAZA DIGITAL", "🛑 BLOQUEO DE SEGURIDAD", ticket.texto, True)

    # FILTRO 2: PÁNICO
    amenazas = ["ME VOY", "CANCELAR", "BAJA", "RENUNCIA", "PERDIENDO DINERO", "CAIDA", "DEMANDA", "COMPETENCIA", "NO FUNCIONA"]
    if any(a in texto_upper for a in amenazas):
        return crear_respuesta(meta, texto_limpio, "FUGA_INMINENTE", 100.0, "CRÍTICO", "🔥 ALERTA ROJA: CONTACTAR", ticket.texto)

    # FILTRO 3: VENTAS
    ventas = ["COMPRAR", "CONTRATAR", "COTIZAR", "NUEVO PLAN", "UPGRADE"]
    if any(v in texto_upper for v in ventas):
        return crear_respuesta(meta, texto_limpio, "VENTA", 5.0, "INTERESADO", "⭐ NOTIFICAR A VENTAS", ticket.texto)

    # FILTRO 4: DECEPCIÓN
    decepcion = ["NO ES LO QUE ESPERABA", "REGULAR", "LENTO", "DECEPCIONADO", "ESPERABA MAS"]
    if any(d in texto_upper for d in decepcion):
        return crear_respuesta(meta, texto_limpio, "RIESGO_MEDIO", 45.0, "DECEPCIONADO", "⚠️ SEGUIMIENTO", ticket.texto)

    # FILTRO 5: IA
    info = CoreTex.procesar_ticket_inteligente(ticket.texto)
    riesgo = info['riesgo_extra'] if info['riesgo_extra'] >= 40 else 15.0
    accion = CoreTex.recomendar_accion(riesgo, info['sentimiento_valor'], info['phishing'])
    
    return crear_respuesta(meta, texto_limpio, info['tipo_ticket'], riesgo, info['sentimiento_etiqueta'], accion, ticket.texto)

def crear_respuesta(meta, anonimo, tipo, riesgo, emocion, accion, original, es_phishing=False):
    resp_sugerida = CoreTex.generar_respuesta_sugerida(original, tipo, accion)
    # Guardamos en DB con los datos del cliente
    guardar_ticket_db(original, anonimo, tipo, riesgo, accion, meta['nombre'], meta['email'], meta['ticket_ref'])
    
    return TicketOutput(
        ticket_id=meta['ticket_ref'], usuario=meta['nombre'], email_usuario=meta['email'],
        texto_anonimizado=anonimo, tipo_ticket=tipo, emocion=emocion, riesgo_churn=riesgo,
        es_phishing=es_phishing, accion_recomendada=accion, respuesta_sugerida=resp_sugerida
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)