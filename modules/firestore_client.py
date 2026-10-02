# -*- coding: utf-8 -*-
"""
Cliente de Firestore — persistencia de leads clasificados.

Guarda cada resultado de /clasificar en la colección
'leads_clasificados'. La autenticación se resuelve con Application
Default Credentials (ADC), configuradas con
`gcloud auth application-default login` en desarrollo local, o con
la identidad de servicio del contenedor una vez desplegado en
Cloud Run. El Project ID se pasa explícitamente porque las
credenciales de usuario (a diferencia de una cuenta de servicio) no
lo traen incluido.
"""

import logging
import os
from datetime import datetime, timezone

from google.cloud import firestore

logger = logging.getLogger("clasificador_leads.firestore_client")

COLECCION = "leads_clasificados"

_project_id = os.getenv("GCP_PROJECT_ID")
if not _project_id:
    raise RuntimeError(
        "GCP_PROJECT_ID no está configurada en las variables de entorno. "
        "Agrégala a tu archivo .env."
    )

# Cliente único y reutilizable — crear una conexión nueva en cada
# petición sería un desperdicio de recursos.
_db = firestore.Client(project=_project_id)


def guardar_clasificacion(
    remitente: str,
    canal: str,
    texto: str,
    categoria_final: str,
    resultado_filtro: dict,
    resultado_ia: dict | None,
) -> str:
    """
    Guarda un registro de clasificación en Firestore.

    Args:
        remitente: quién envió el mensaje.
        canal: canal de origen (whatsapp, email, etc.).
        texto: contenido original del mensaje.
        categoria_final: 'alta_prioridad', 'informativo' o 'spam'.
        resultado_filtro: dict devuelto por analizar_mensaje().
        resultado_ia: dict con categoria/justificacion/confianza, o
            None si el mensaje se detuvo en el filtro de spam.

    Returns:
        El ID del documento creado en Firestore.
    """
    documento = {
        "remitente": remitente,
        "canal": canal,
        "texto": texto,
        "categoria_final": categoria_final,
        "resultado_filtro": resultado_filtro,
        "resultado_ia": resultado_ia,
        "fecha": datetime.now(timezone.utc),
    }

    try:
        _, doc_ref = _db.collection(COLECCION).add(documento)
        logger.info("Clasificación guardada en Firestore con id=%s", doc_ref.id)
        return doc_ref.id
    except Exception as exc:
        logger.error("No se pudo guardar en Firestore: %s", exc)
        return ""