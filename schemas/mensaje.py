# -*- coding: utf-8 -*-
"""
Schemas (contratos de datos) para el Clasificador de Leads.

Un schema Pydantic no es lógica de negocio: es la definición de la
"forma" que debe tener un dato antes de que cualquier función lo
toque. FastAPI usa estas clases para validar automáticamente las
peticiones entrantes y para generar la documentación de /docs.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class CategoriaLead(str, Enum):
    """
    Conjunto cerrado de categorías posibles para un mensaje clasificado.
    Heredar de (str, Enum) permite que FastAPI lo serialice como texto
    simple en el JSON de respuesta, sin perder la validación estricta.
    """
    ALTA_PRIORIDAD = "alta_prioridad"
    INFORMATIVO = "informativo"


class MensajeEntrante(BaseModel):
    """
    Representa un mensaje o correo que llega desde cualquier canal
    (WhatsApp, email, formulario web) y que necesita ser clasificado
    en Alta Prioridad, Informativo o Spam.
    """

    remitente: str = Field(
        ...,  # "..." significa que el campo es obligatorio
        min_length=1,
        description="Nombre, número o identificador de quien envía el mensaje",
        examples=["Juan Pérez"],
    )

    texto: str = Field(
        ...,
        min_length=1,
        description="Contenido completo del mensaje a clasificar",
        examples=["Hola, quisiera información sobre sus cursos de inglés"],
    )

    canal: str = Field(
        default="desconocido",
        description="Canal de origen del mensaje",
        examples=["whatsapp", "email", "formulario"],
    )

    fecha_recibido: Optional[datetime] = Field(
        default=None,
        description=(
            "Momento en que se recibió el mensaje en el sistema de origen. "
            "Si no se envía, el servidor la asigna al procesar la petición."
        ),
    )


class ResultadoClasificacion(BaseModel):
    """
    Resultado que devuelve la Capa 2 (Groq) para un mensaje que ya
    pasó el filtro de spam. Esta es la forma exacta que le pedimos
    al modelo que respete en su salida JSON.
    """

    categoria: CategoriaLead = Field(
        ..., description="Clasificación asignada al mensaje"
    )
    justificacion: str = Field(
        ..., description="Explicación breve de por qué se asignó esa categoría"
    )
    confianza: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Nivel de confianza del modelo, de 0.0 a 1.0",
    )