# -*- coding: utf-8 -*-
"""
Seguridad — Bloque 7.

Define la dependencia que FastAPI ejecuta antes de correr cualquier
endpoint protegido. El cliente debe mandar la API key en el header
HTTP 'X-API-Key'. Si falta o no coincide, se corta la petición con
un 401 antes de que la lógica de negocio se ejecute.
"""

import os

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

# Esto le dice a FastAPI (y a /docs) que existe un esquema de
# seguridad basado en un header llamado 'X-API-Key'. Gracias a esto,
# /docs va a mostrar un botón "Authorize" donde puedes pegar tu key
# una sola vez y probar todos los endpoints protegidos sin repetirla.
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verificar_api_key(key_recibida: str = Security(api_key_header)) -> str:
    """
    Dependencia de seguridad: compara la key recibida contra la
    configurada en las variables de entorno.

    Args:
        key_recibida: valor del header X-API-Key, inyectado
            automáticamente por FastAPI gracias a Security().

    Returns:
        La key recibida, si es válida (por si el endpoint la
        necesitara, aunque normalmente no se usa el valor de retorno).

    Raises:
        HTTPException 401: si falta el header o la key no coincide.
    """
    api_key_esperada = os.getenv("API_KEY")

    if not api_key_esperada:
        # Esto protege contra un descuido: si алguien olvida
        # configurar API_KEY en producción, es mejor tronar fuerte
        # que dejar la API abierta sin darse cuenta.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API_KEY no está configurada en el servidor",
        )

    if key_recibida != api_key_esperada:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida o faltante",
        )

    return key_recibida