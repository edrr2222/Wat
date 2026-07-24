"""
Asistente multi-cliente — Agente LangChain
---------------------------------------------------------
Este agente es GENÉRICO: no sabe nada de "Jaime Duque" ni de
ningún cliente específico. Toda esa información viene de:
  - app/clientes.py (el bloque corto de configuración)
  - app/conocimiento/<cliente_id>/ (documentos + fuentes.json)
    ya indexados por ingest.py en chroma_db/<cliente_id>/

Así, agregar un cliente nuevo nunca requiere tocar este archivo.
"""
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_chroma import Chroma
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langgraph.checkpoint.memory import InMemorySaver

from .clientes import obtener_cliente

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
CHROMA_ROOT = BASE_DIR.parent / "chroma_db"
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
CLIENTE_ID = os.environ.get("CLIENTE_ACTIVO", "jaime_duque")


def _embeddings():
    return GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")


def obtener_vectorstore(cliente_id: str) -> Chroma:
    destino = CHROMA_ROOT / cliente_id
    if not destino.exists() or not any(destino.iterdir()):
        raise RuntimeError(
            f"No hay una base de conocimiento indexada para '{cliente_id}'. "
            f"Corre primero: python ingest.py {cliente_id}"
        )
    return Chroma(persist_directory=str(destino), embedding_function=_embeddings())


# ---------------------------------------------------------
# Herramienta de búsqueda (genérica — el cliente se resuelve en tiempo de uso)
# ---------------------------------------------------------
@tool
def buscar_informacion(consulta: str) -> str:
    """Busca información relevante en la base de conocimiento del negocio actual.
    Úsala siempre que el usuario pregunte algo que requiera datos concretos
    (horarios, precios, ubicación, servicios, menú, atracciones, etc.)."""
    vectorstore = obtener_vectorstore(CLIENTE_ID)
    resultados = vectorstore.similarity_search(consulta, k=4)
    if not resultados:
        return "No se encontró información relevante en la base de conocimiento."
    return "\n\n---\n\n".join(
        f"[Fuente: {r.metadata.get('source', 'desconocida')}]\n{r.page_content}"
        for r in resultados
    )


@tool
def consultar_clima(ciudad: str) -> str:
    """Consulta el clima ACTUAL de una ciudad o municipio usando la API gratuita
    Open-Meteo (geocodificación automática). Úsala cuando el usuario pregunte
    si va a llover, si debería llevar sombrilla, o si el clima es relevante
    para la visita."""
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": ciudad, "count": 1, "language": "es"},
            timeout=8,
        ).json()
        if not geo.get("results"):
            return f"No se pudo ubicar '{ciudad}' para consultar el clima."
        lat, lon = geo["results"][0]["latitude"], geo["results"][0]["longitude"]

        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon, "current": "temperature_2m,precipitation"},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()["current"]
        return f"Clima actual en {ciudad}: {data['temperature_2m']}°C, precipitación {data['precipitation']}mm."
    except Exception as e:
        return f"No se pudo consultar el clima en este momento: {e}"


SYSTEM_PROMPT_TEMPLATE = """Eres el asistente virtual oficial de {nombre}, un(a) {tipo_negocio}.

Contexto del negocio: {descripcion_corta}

Responde siempre en español, de forma cálida, concreta y sin relleno.
SIEMPRE usa la herramienta buscar_informacion antes de responder preguntas
sobre {nombre} — no inventes información, precios, horarios ni datos que
no encuentres ahí.

Si el usuario pregunta algo que NO tiene relación con {nombre}, indícalo
amablemente y redirige la conversación hacia cómo sí puedes ayudarle
(información sobre {nombre})."""


def construir_agente(cliente_id: str = None):
    cliente_id = cliente_id or CLIENTE_ID
    cliente = obtener_cliente(cliente_id)

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        nombre=cliente["nombre"],
        tipo_negocio=cliente["tipo_negocio"],
        descripcion_corta=cliente["descripcion_corta"],
    )

    herramientas = [buscar_informacion]
    if cliente.get("usa_clima"):
        herramientas.append(consultar_clima)

    llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0.4)

    return create_agent(
        model=llm,
        tools=herramientas,
        system_prompt=system_prompt,
        checkpointer=InMemorySaver(),
    )
