# -*- coding: utf-8 -*-
"""
Clasificador de Leads — Punto de entrada de la API.

Arquitectura: FastAPI (ASGI) desacoplada, pensada para desplegarse
en Google Cloud Run. Este archivo únicamente define la app y las
rutas de alto nivel; toda la lógica de negocio vive en modules/.
"""
import logging
import os
from dotenv import load_dotenv

# CRÍTICO: cargar .env ANTES de importar cualquier módulo que lo
# necesite en tiempo de importación (como firestore_client.py, que
# crea la conexión a Firestore apenas se importa).
load_dotenv()

from fastapi import Depends, FastAPI, HTTPException

from modules.seguridad import verificar_api_key
from modules.alertas import enviar_alerta_whatsapp
from modules.ai_classifier import clasificar_con_ia
from modules.firestore_client import guardar_clasificacion
from modules.spam_filter import analizar_mensaje
from schemas.mensaje import CategoriaLead
from schemas.mensaje import MensajeEntrante

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("clasificador_leads")

app = FastAPI(
    title="Clasificador de Leads",
    description=(
        "API que recibe mensajes o correos entrantes y los clasifica "
        "en Alta Prioridad, Informativo o Spam, notificando al "
        "vendedor correspondiente cuando aplica."
    ),
    version="0.1.0",
)


@app.get("/health", tags=["Sistema"])
def health_check() -> dict:
    """
    Endpoint de salud. Cloud Run (y cualquier balanceador de carga)
    lo usa para confirmar que el contenedor está vivo y respondiendo
    antes de enviarle tráfico real.
    """
    logger.info("Health check solicitado")
    return {
        "status": "ok",
        "servicio": "clasificador-leads",
        "version": app.version,
    }


@app.post("/filtrar-spam", tags=["Clasificación"])
def filtrar_spam(
    mensaje: MensajeEntrante,
    _: str = Depends(verificar_api_key),
    ) -> dict:
    """
    Endpoint de prueba para el Bloque 2: aplica únicamente el filtro
    de reglas (Capa 1) a un mensaje entrante y devuelve el resultado
    sin pasar todavía por la IA de Groq.
    """
    logger.info("Mensaje recibido de '%s' por canal '%s'", mensaje.remitente, mensaje.canal)

    resultado = analizar_mensaje(mensaje.texto)

    return {
        "remitente": mensaje.remitente,
        "canal": mensaje.canal,
        "resultado_filtro": resultado,
    }


@app.post("/clasificar", tags=["Clasificación"])
def clasificar(
    mensaje: MensajeEntrante,
    _:str = Depends(verificar_api_key)
    ) -> dict:
    """
    Endpoint principal: aplica primero el filtro de reglas (Capa 1).
    Si el mensaje se marca como spam, se detiene ahí y NUNCA llega a
    la IA. Si pasa el filtro, se clasifica con la IA (Capa 2). En
    ambos casos, el resultado se guarda en Firestore. Si la
    categoría final es Alta Prioridad, se dispara una alerta de
    WhatsApp al vendedor.
    """
    logger.info("Clasificando mensaje de '%s' por canal '%s'", mensaje.remitente, mensaje.canal)

    resultado_filtro = analizar_mensaje(mensaje.texto)

    if resultado_filtro["es_spam"]:
        guardar_clasificacion(
            remitente=mensaje.remitente,
            canal=mensaje.canal,
            texto=mensaje.texto,
            categoria_final="spam",
            resultado_filtro=resultado_filtro,
            resultado_ia=None,
        )
        return {
            "remitente": mensaje.remitente,
            "canal": mensaje.canal,
            "categoria_final": "spam",
            "resultado_filtro": resultado_filtro,
            "resultado_ia": None,
        }

    try:
        resultado_ia = clasificar_con_ia(mensaje.texto)
    except RuntimeError as exc:
        logger.error("Fallo la clasificación con IA: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))

    guardar_clasificacion(
        remitente=mensaje.remitente,
        canal=mensaje.canal,
        texto=mensaje.texto,
        categoria_final=resultado_ia.categoria,
        resultado_filtro=resultado_filtro,
        resultado_ia=resultado_ia.model_dump(),
    )

    if resultado_ia.categoria == CategoriaLead.ALTA_PRIORIDAD:
        mensaje_alerta = (
            f"🔥 Lead de Alta Prioridad\n"
            f"De: {mensaje.remitente} ({mensaje.canal})\n"
            f"Mensaje: {mensaje.texto[:200]}\n"
            f"Motivo: {resultado_ia.justificacion}"
        )
        enviar_alerta_whatsapp(mensaje_alerta)

    return {
        "remitente": mensaje.remitente,
        "canal": mensaje.canal,
        "categoria_final": resultado_ia.categoria,
        "resultado_filtro": resultado_filtro,
        "resultado_ia": resultado_ia,
    }