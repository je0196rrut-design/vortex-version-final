from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import pandas as pd
import numpy as np
import uvicorn
import os
import sqlite3 
import random
from datetime import datetime
import CoreTex
import unicodedata

app = FastAPI(title="Vortex Suite API", version="Final Ecosystem")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 1. BASE DE DATOS MAESTRA
# ==========================================
def init_db():
    conn = sqlite3.connect('historial_vortex.db')
    c = conn.cursor()
    # Estructura completa incluyendo 'respuesta_ia'
    c.execute('''CREATE TABLE IF NOT EXISTS tickets
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  fecha TEXT, original TEXT, anonimo TEXT, tipo TEXT, 
                  riesgo REAL, accion TEXT, usuario TEXT, email TEXT, ref TEXT, 
                  estado TEXT, respuesta_ia TEXT)''') 
    conn.commit()
    conn.close()

def normalizar_texto(texto):
    if not texto: return ""
    texto = str(texto).upper()
    texto = ''.join((c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn'))
    return texto

# ==========================================
# 2. MODELOS DE DATOS
# ==========================================
class ClientForm(BaseModel):
    nombre: str
    email: str
    mensaje: str

class TicketInput(BaseModel):
    texto: str
    id_db: Optional[int] = None

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

# ==========================================
# 3. ENDPOINTS DE ENTRADA (Simulación y Real)
# ==========================================

@app.post("/crear_ticket_cliente")
def crear_ticket_cliente(form: ClientForm):
    conn = sqlite3.connect('historial_vortex.db')
    c = conn.cursor()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ref = f"T-{np.random.randint(10000, 99999)}"
    # Guardamos vacía la respuesta IA porque aún no se procesa
    c.execute("INSERT INTO tickets (fecha, original, usuario, email, ref, estado, respuesta_ia) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (fecha, form.mensaje, form.nombre, form.email, ref, "PENDIENTE", ""))
    conn.commit()
    conn.close()
    return {"status": "ok", "ref": ref}

@app.post("/simular_trafico")
def simular_trafico():
    """Genera una mezcla estratégica: Ventas, Fallas y Fugas."""
    casos = [
        # VENTAS (Para que el Dashboard muestre dinero)
        ("Hola, quisiera cotizar el plan Enterprise para 50 usuarios.", "Pedro CEO", "ceo@tech.co"),
        ("Me interesa comprar licencias adicionales, ¿me pueden ayudar?", "Maria Sales", "maria@corp.com"),
        
        # SOPORTE TÉCNICO (Riesgo Medio)
        ("El sistema no funciona y me urge sacar un reporte.", "Luis Soporte", "luis@mail.com"),
        
        # FUGA / IRA (Riesgo Alto)
        ("Son unos estafadores, quiero cancelar mi suscripción YA.", "Carlos Furioso", "carlos@baja.com"),
        
        # PHISHING (Seguridad)
        ("Actualice sus datos aquí http://bit.ly/robo o perderá acceso.", "Hacker", "admin@fake.com")
    ]
    
    conn = sqlite3.connect('historial_vortex.db')
    c = conn.cursor()
    nuevos = []
    
    # Creamos 4 tickets de golpe
    for _ in range(4): 
        texto, user, mail = random.choice(casos)
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ref = f"T-{np.random.randint(1000,9999)}"
        c.execute("INSERT INTO tickets (fecha, original, usuario, email, ref, estado, respuesta_ia) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (fecha, texto, user, mail, ref, "PENDIENTE", ""))
        nuevos.append(user)
        
    conn.commit()
    conn.close()
    return {"mensaje": "Trafico simulado con éxito", "usuarios": nuevos}

# ==========================================
# 4. GESTIÓN DE DATOS (Privacidad y KPIs)
# ==========================================

@app.get("/tickets_pendientes")
def tickets_pendientes():
    """Entrega tickets al Agente CON PRIVACIDAD ACTIVADA."""
    conn = sqlite3.connect('historial_vortex.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM tickets WHERE estado = 'PENDIENTE' ORDER BY id DESC")
    filas = c.fetchall()
    conn.close()
    
    tickets_seguros = []
    for row in filas:
        t = dict(row)
        # 🔒 CENSURA DE DATOS PARA EL AGENTE
        t['email'] = "🔒<EMAIL_OCULTO>" 
        t['original'] = CoreTex.anonimizar_regex(t['original']) 
        tickets_seguros.append(t)
    return tickets_seguros

@app.get("/datos_grafica")
def datos_grafica():
    """KPIs para el Gerente."""
    conn = sqlite3.connect('historial_vortex.db')
    c = conn.cursor()
    
    # Datos Gráfica
    c.execute("SELECT riesgo, fecha FROM tickets WHERE estado='RESUELTO' ORDER BY fecha DESC LIMIT 20")
    data = c.fetchall()
    
    # Contadores
    c.execute("SELECT COUNT(*) FROM tickets WHERE estado='PENDIENTE'")
    pendientes = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tickets WHERE estado='RESUELTO'")
    resueltos = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tickets WHERE estado='RESUELTO' AND riesgo >= 60")
    criticos = c.fetchone()[0]
    # KPI DE VENTAS (Busca la palabra 'VENTA' o 'OPORTUNIDAD' en el tipo)
    c.execute("SELECT COUNT(*) FROM tickets WHERE estado='RESUELTO' AND (tipo LIKE '%VENTA%' OR tipo LIKE '%OPORTUNIDAD%')")
    ventas = c.fetchone()[0]

    conn.close()
    
    riesgos = [x[0] for x in reversed(data)]
    fechas = [x[1].split(' ')[1] for x in reversed(data)]
    
    return {
        "riesgos": riesgos, "fechas": fechas, 
        "kpi_pendientes": pendientes, "kpi_total": resueltos + pendientes, 
        "kpi_criticos": criticos, "kpi_ventas": ventas
    }

@app.get("/ver_historial")
def ver_historial():
    conn = sqlite3.connect('historial_vortex.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM tickets WHERE estado = 'RESUELTO' ORDER BY fecha DESC LIMIT 50")
    return [dict(row) for row in c.fetchall()]

@app.delete("/borrar_historial")
def borrar_historial():
    conn = sqlite3.connect('historial_vortex.db')
    c = conn.cursor()
    c.execute("DELETE FROM tickets")
    conn.commit()
    conn.close()
    return {"mensaje": "DB Limpia"}

# ==========================================
# 5. LÓGICA DE ANÁLISIS HÍBRIDA
# ==========================================

@app.post("/analizar_ticket", response_model=TicketOutput)
def analizar_ticket(ticket: TicketInput):
    texto_limpio_logica = normalizar_texto(ticket.texto)
    meta = CoreTex.extraer_metadatos(ticket.texto)
    texto_anonimo = CoreTex.anonimizar_regex(ticket.texto)

    # 1. CONSULTA A LA IA (Motor Emocional)
    print("🤖 Consultando IA...")
    info_ia = CoreTex.procesar_ticket_inteligente(ticket.texto)
    
    riesgo_final = info_ia['riesgo_extra']
    tipo_final = info_ia['tipo_ticket']
    emocion_final = info_ia['sentimiento_etiqueta']
    accion_final = "ANÁLISIS IA"

    # 2. REGLAS DE NEGOCIO (Prioridades)
    palabras_muerte = ["CANCELAR", "BAJA", "RENUNCIA", "ME VOY", "ESTAFA", "DEMANDA", "ABOGADO", "ROBO"]
    palabras_falla = ["NO FUNCIONA", "FALLA", "ERROR", "LENTO", "BUG", "PROBLEMA"]
    palabras_phishing = ["HTTP", "BIT.LY", "PASSWORD"]
    palabras_venta = ["COMPRAR", "CONTRATAR", "COTIZAR", "PRECIO", "COSTO", "PLAN", "UPGRADE", "INTERESADO", "ADQUIRIR"]

    if any(p in texto_limpio_logica for p in palabras_phishing):
        riesgo_final = 100.0
        tipo_final = "PHISHING"
        accion_final = "🛑 BLOQUEO DE SEGURIDAD"
        
    elif any(p in texto_limpio_logica for p in palabras_muerte):
        riesgo_final = max(riesgo_final, 90.0) 
        tipo_final = "FUGA_INMINENTE"
        accion_final = "🔥 ALERTA ROJA: RETENCIÓN"
        
    elif any(p in texto_limpio_logica for p in palabras_falla):
        riesgo_final = max(riesgo_final, 60.0)
        tipo_final = f"FALLA TÉCNICA ({emocion_final})"
        accion_final = "⚠️ SOPORTE PRIORITARIO"
        
    elif any(p in texto_limpio_logica for p in palabras_venta):
        riesgo_final = 10.0 # Riesgo bajo
        tipo_final = f"💰 OPORTUNIDAD VENTA ({emocion_final})"
        accion_final = "⭐ NOTIFICAR A VENTAS"

    # Si las reglas no impusieron una acción, usamos la recomendación de la IA
    if accion_final == "ANÁLISIS IA":
        accion_final = CoreTex.recomendar_accion(riesgo_final, info_ia['sentimiento_valor'], info_ia['phishing'])

    # 3. GENERAR RESPUESTA TÁCTICA
    resp_sugerida = CoreTex.generar_respuesta_sugerida(ticket.texto, tipo_final, accion_final)

    # 4. GUARDAR EN DB
    conn = sqlite3.connect('historial_vortex.db')
    c = conn.cursor()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if ticket.id_db: 
        c.execute("UPDATE tickets SET anonimo=?, tipo=?, riesgo=?, accion=?, estado='RESUELTO', fecha=?, respuesta_ia=? WHERE id=?", 
                  (texto_anonimo, tipo_final, riesgo_final, accion_final, fecha, resp_sugerida, ticket.id_db))
    else: 
        c.execute("INSERT INTO tickets (fecha, original, anonimo, tipo, riesgo, accion, usuario, email, ref, estado, respuesta_ia) VALUES (?,?,?,?,?,?,?,?,?,?,?)", 
                  (fecha, ticket.texto, texto_anonimo, tipo_final, riesgo_final, accion_final, meta['nombre'], meta['email'], meta['ticket_ref'], 'RESUELTO', resp_sugerida))
    
    conn.commit()
    conn.close()

    return TicketOutput(
        ticket_id=meta['ticket_ref'], usuario=meta['nombre'], email_usuario=meta['email'],
        texto_anonimizado=texto_anonimo, tipo_ticket=tipo_final, emocion=emocion_final, 
        riesgo_churn=riesgo_final, es_phishing=(tipo_final == "PHISHING"), 
        accion_recomendada=accion_final, respuesta_sugerida=resp_sugerida
    )

@app.on_event("startup")
def startup(): init_db()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)