# -*- coding: utf-8 -*-
"""
Sistema de alertas — Bloque 6.

Envía un mensaje de WhatsApp al vendedor cuando un lead se clasifica
como Alta Prioridad, usando CallMeBot (servicio gratuito de alertas
personales, sin necesidad de una cuenta de WhatsApp Business).

Nota de diseño: esto es intencionalmente una alerta simple al
vendedor/administrador, NO una integración de conversación con el
lead. La integración completa de WhatsApp Business API (con Twilio)
está planeada como un proyecto aparte.
"""

import logging
import os

import requests

logger = logging.getLogger("clasificador_leads.alertas")

CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"


def enviar_alerta_whatsapp(mensaje: str) -> bool:
    """
    Envía un mensaje de WhatsApp vía CallMeBot.

    Args:
        mensaje: texto a enviar. CallMeBot lo recibe como parámetro
            de URL, así que 'requests' se encarga de codificarlo
            correctamente (espacios, saltos de línea, etc.).

    Returns:
        True si el envío fue exitoso, False si falló (nunca lanza
        una excepción hacia afuera, para no tumbar la respuesta
        principal de /clasificar por un fallo de notificación).
    """
    telefono = os.getenv("ALERTA_WHATSAPP_TELEFONO")
    apikey = os.getenv("ALERTA_WHATSAPP_APIKEY")

    if not telefono or not apikey:
        logger.warning(
            "ALERTA_WHATSAPP_TELEFONO o ALERTA_WHATSAPP_APIKEY no están "
            "configuradas — se omite el envío de alerta."
        )
        return False

    parametros = {
        "phone": telefono,
        "text": mensaje,
        "apikey": apikey,
    }

    try:
        respuesta = requests.get(CALLMEBOT_URL, params=parametros, timeout=10)
        respuesta.raise_for_status()
        logger.info("Alerta de WhatsApp enviada correctamente")
        return True
    except requests.RequestException as exc:
        logger.error("No se pudo enviar la alerta de WhatsApp: %s", exc)
        return False