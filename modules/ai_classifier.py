# -*- coding: utf-8 -*-
"""
Clasificador con IA — Capa 2 del sistema de clasificación de leads.

Solo se invoca para mensajes que YA pasaron el filtro de reglas
(modules/spam_filter.py) sin marcarse como spam. Su trabajo es decidir
entre dos categorías (Alta Prioridad / Informativo) usando comprensión
de lenguaje natural, algo que un filtro de reglas no puede hacer bien.
"""

import json
import logging
import os

from groq import Groq

from schemas.mensaje import CategoriaLead, ResultadoClasificacion

logger = logging.getLogger("clasificador_leads.ai_classifier")

MODELO = "llama-3.1-8b-instant"

PROMPT_SISTEMA = """Eres un clasificador de mensajes de leads para un negocio.
Tu única tarea es leer el mensaje de un prospecto y decidir si es:

- "alta_prioridad": el prospecto muestra intención clara de compra o
  contratación, pregunta por precios, disponibilidad, quiere agendar
  una cita, o pide hablar con un vendedor.
- "informativo": el prospecto hace una pregunta general, pide
  información sin intención inmediata de compra, o el mensaje es de
  soporte/servicio a cliente sin urgencia comercial.

Responde ÚNICAMENTE con un objeto JSON válido, sin texto antes ni
después, sin backticks de markdown, con exactamente esta forma:

{
  "categoria": "alta_prioridad" o "informativo",
  "justificacion": "una oración breve explicando el motivo",
  "confianza": número decimal entre 0.0 y 1.0
}
"""


def clasificar_con_ia(texto: str) -> ResultadoClasificacion:
    """
    Envía el texto del mensaje a Groq/Llama y devuelve la clasificación
    ya validada como ResultadoClasificacion.

    Args:
        texto: contenido del mensaje a clasificar (ya pasó el filtro
            de spam antes de llegar aquí).

    Returns:
        ResultadoClasificacion con categoria, justificacion y confianza.

    Raises:
        RuntimeError: si la API de Groq falla o la respuesta no se
            puede interpretar como el JSON esperado. Se relanza como
            RuntimeError para que la capa de endpoint decida cómo
            responder al cliente (por ejemplo, con un 502).
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY no está configurada en las variables de entorno"
        )

    client = Groq(api_key=api_key)

    try:
        respuesta = client.chat.completions.create(
            model=MODELO,
            messages=[
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": texto},
            ],
            max_tokens=300,
            temperature=0.2,  # Baja, porque queremos consistencia, no creatividad
        )
    except Exception as exc:
        logger.error("Error al llamar a la API de Groq: %s", exc)
        raise RuntimeError(f"Fallo al consultar la IA: {exc}") from exc

    contenido_bruto = respuesta.choices[0].message.content.strip()

    # Limpieza defensiva por si el modelo agrega backticks de markdown
    # a pesar de la instrucción explícita de no hacerlo.
    contenido_limpio = (
        contenido_bruto.replace("```json", "").replace("```", "").strip()
    )

    try:
        datos = json.loads(contenido_limpio)
    except json.JSONDecodeError as exc:
        logger.error("La IA no devolvió JSON válido: %s", contenido_bruto)
        raise RuntimeError(
            f"La IA no devolvió un JSON interpretable: {exc}"
        ) from exc

    resultado = ResultadoClasificacion(
        categoria=CategoriaLead(datos["categoria"]),
        justificacion=datos["justificacion"],
        confianza=float(datos["confianza"]),
    )

    logger.info(
        "Mensaje clasificado como '%s' (confianza=%.2f)",
        resultado.categoria, resultado.confianza,
    )

    return resultado