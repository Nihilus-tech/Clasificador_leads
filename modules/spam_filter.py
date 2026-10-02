# -*- coding: utf-8 -*-
"""
Filtro de spam basado en reglas — Capa 1 del sistema de clasificación.

Objetivo: detectar spam obvio de forma rápida y gratuita (sin usar la
API de Groq), acumulando "puntos de sospecha" por cada señal detectada.
Si el puntaje total alcanza el umbral, el mensaje se marca como spam
y NUNCA llega a la Capa 2 (la IA), ahorrando tiempo y costo.

Este módulo es intencionalmente conservador: preferimos dejar pasar
un mensaje dudoso a la IA (que es mejor entendiendo matices) antes que
descartar por error un lead real.
"""

import logging
import re
from typing import TypedDict

logger = logging.getLogger("clasificador_leads.spam_filter")

# Umbral de puntaje a partir del cual un mensaje se considera spam.
UMBRAL_SPAM = 5

# Palabras y frases típicas de spam masivo. Todo en minúsculas porque
# comparamos contra el texto ya normalizado.
PALABRAS_SPAM = [
    "gana dinero", "dinero fácil", "inversión garantizada",
    "haz clic aquí", "haz click aqui", "oferta exclusiva",
    "100% gratis", "gratis por tiempo limitado", "premio garantizado",
    "felicidades has ganado", "trabaja desde casa", "gana desde casa",
    "bitcoin", "criptomoneda gratis", "duplica tu dinero",
]


class ResultadoFiltroSpam(TypedDict):
    """Forma del resultado que devuelve analizar_mensaje()."""
    es_spam: bool
    puntaje: int
    razones: list[str]


def _contar_urls(texto: str) -> int:
    """Cuenta cuántas URLs aparecen en el texto."""
    patron_url = r"(https?://|www\.)\S+"
    return len(re.findall(patron_url, texto, flags=re.IGNORECASE))


def _porcentaje_mayusculas(texto: str) -> float:
    """
    Calcula qué porcentaje de las letras del texto están en mayúsculas.
    Ignora espacios, números y signos de puntuación para no distorsionar
    el cálculo con mensajes cortos.
    """
    letras = [c for c in texto if c.isalpha()]
    if not letras:
        return 0.0
    mayusculas = [c for c in letras if c.isupper()]
    return len(mayusculas) / len(letras)


def _tiene_repeticion_excesiva(texto: str) -> bool:
    """
    Detecta patrones como 'Gaaaana dineroooo' — 4 o más repeticiones
    consecutivas del mismo carácter.
    """
    return bool(re.search(r"(.)\1{3,}", texto))


def analizar_mensaje(texto: str) -> ResultadoFiltroSpam:
    """
    Analiza un texto y devuelve si se considera spam, el puntaje
    acumulado y la lista de razones (señales) que se detectaron.

    Args:
        texto: contenido del mensaje a analizar.

    Returns:
        Diccionario con es_spam (bool), puntaje (int) y razones (list[str]).
    """
    if not texto or not texto.strip():
        # Un mensaje vacío no es "spam" per se, pero tampoco es
        # clasificable — lo marcamos con una razón específica.
        return {
            "es_spam": True,
            "puntaje": UMBRAL_SPAM,
            "razones": ["mensaje vacío o sin contenido evaluable"],
        }

    texto_normalizado = texto.lower().strip()
    puntaje = 0
    razones: list[str] = []

    # Señal 1: palabras/frases de spam conocidas
    for frase in PALABRAS_SPAM:
        if frase in texto_normalizado:
            puntaje += 3
            razones.append(f"contiene frase de spam: '{frase}'")

    # Señal 2: exceso de URLs
    num_urls = _contar_urls(texto)
    if num_urls >= 3:
        puntaje += 4
        razones.append(f"contiene {num_urls} URLs (umbral: 3+)")
    elif num_urls == 2:
        puntaje += 2
        razones.append("contiene 2 URLs")

    # Señal 3: exceso de mayúsculas (solo aplica a mensajes con
    # suficiente longitud para que el cálculo tenga sentido)
    if len(texto) >= 15:
        pct_mayus = _porcentaje_mayusculas(texto)
        if pct_mayus >= 0.6:
            puntaje += 3
            razones.append(f"{pct_mayus:.0%} del texto está en mayúsculas")

    # Señal 4: repetición excesiva de caracteres
    if _tiene_repeticion_excesiva(texto):
        puntaje += 2
        razones.append("repetición excesiva de caracteres detectada")

    # Señal 5: exceso de signos de exclamación
    num_exclamaciones = texto.count("!")
    if num_exclamaciones >= 4:
        puntaje += 2
        razones.append(f"{num_exclamaciones} signos de exclamación")

    es_spam = puntaje >= UMBRAL_SPAM

    logger.info(
        "Mensaje analizado — puntaje=%s, es_spam=%s, razones=%s",
        puntaje, es_spam, razones,
    )

    return {
        "es_spam": es_spam,
        "puntaje": puntaje,
        "razones": razones,
    }