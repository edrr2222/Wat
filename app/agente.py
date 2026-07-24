"""
BogotáGuía — Agente LangChain
---------------------------------------------------------
Combina dos técnicas:

1. RAG (Retrieval-Augmented Generation): la base de conocimiento
   en conocimiento/*.md se indexa en Chroma (vectorial, local) y
   se consulta por significado, no por palabras exactas.

2. Agente con herramientas: el LLM decide POR SÍ SOLO cuándo
   buscar en la base de conocimiento y cuándo consultar el clima
   real (API gratuita Open-Meteo, sin necesidad de clave).

Nota de versión: desde LangChain 1.0, la forma recomendada de
construir agentes es `create_agent` (basada en LangGraph), que
reemplaza al patrón anterior de `create_tool_calling_agent` +
`AgentExecutor`. La memoria de conversación ahora se maneja con
un checkpointer de LangGraph + un `thread_id`, en vez de
`RunnableWithMessageHistory`.
"""
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
CONOCIMIENTO_DIR = BASE_DIR / "conocimiento"
CHROMA_DIR = BASE_DIR.parent / "chroma_db"
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")


def _embeddings():
    # text-embedding-004 fue retirado por Google; gemini-embedding-001 es su reemplazo estable.
    return GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")


def construir_vectorstore() -> Chroma:
    """Indexa (o re-indexa) la base de conocimiento en Chroma."""
    loader = DirectoryLoader(
        str(CONOCIMIENTO_DIR), glob="*.md", loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    documentos = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
    fragmentos = splitter.split_documents(documentos)

    return Chroma.from_documents(fragmentos, _embeddings(), persist_directory=str(CHROMA_DIR))


def obtener_vectorstore() -> Chroma:
    if CHROMA_DIR.exists() and any(CHROMA_DIR.iterdir()):
        return Chroma(persist_directory=str(CHROMA_DIR), embedding_function=_embeddings())
    return construir_vectorstore()


# ---------------------------------------------------------
# Herramientas que el agente puede decidir usar
# ---------------------------------------------------------
@tool
def buscar_informacion_turistica(consulta: str) -> str:
    """Busca información sobre atractivos, excursiones y consejos prácticos de Bogotá
    y sus alrededores. Úsala siempre que el usuario pregunte por lugares, planes,
    actividades, transporte, comida o recomendaciones turísticas."""
    vectorstore = obtener_vectorstore()
    resultados = vectorstore.similarity_search(consulta, k=4)
    if not resultados:
        return "No se encontró información relevante en la base de conocimiento."
    return "\n\n---\n\n".join(
        f"[Fuente: {Path(r.metadata.get('source', 'desconocida')).stem}]\n{r.page_content}"
        for r in resultados
    )


_COORDENADAS = {
    "bogota": (4.7110, -74.0721),
    "zipaquira": (5.0246, -74.0035),
    "guatavita": (4.9333, -73.8306),
    "suesca": (5.1041, -73.7975),
    "villa de leyva": (5.6333, -73.5250),
    "la calera": (4.7186, -73.9694),
}


@tool
def consultar_clima(ciudad: str = "Bogota") -> str:
    """Consulta el clima ACTUAL de una ciudad o municipio (Bogotá, Zipaquirá, Guatavita,
    Suesca, Villa de Leyva, La Calera) usando la API gratuita Open-Meteo. Úsala cuando
    el usuario pregunte si va a llover, si debería llevar sombrilla, o para recomendar
    un plan según el clima."""
    lat, lon = _COORDENADAS.get(ciudad.strip().lower(), _COORDENADAS["bogota"])
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon, "current": "temperature_2m,precipitation,weather_code"},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()["current"]
        return (
            f"Clima actual en {ciudad}: {data['temperature_2m']}°C, "
            f"precipitación {data['precipitation']}mm (código de clima {data['weather_code']})."
        )
    except Exception as e:
        return f"No se pudo consultar el clima en este momento: {e}"


SYSTEM_PROMPT = (
    "Eres BogotáGuía, un asistente turístico experto en Bogotá y sus alrededores "
    "(Zipaquirá, Guatavita, Suesca, Villa de Leyva, La Calera, entre otros). "
    "Responde siempre en español, de forma cálida, concreta y sin relleno. "
    "SIEMPRE usa la herramienta buscar_informacion_turistica antes de recomendar "
    "lugares o planes — no inventes atractivos ni datos que no encuentres ahí. "
    "Usa consultar_clima cuando el clima sea relevante para la recomendación "
    "(por ejemplo, planes al aire libre). Si el usuario pregunta algo fuera de "
    "turismo en Bogotá y sus alrededores, indícalo amablemente y redirige la "
    "conversación hacia cómo sí puedes ayudarle."
)


def construir_agente():
    """
    Devuelve un agente LangChain (API >=1.0) con:
    - Herramientas de RAG y clima
    - Memoria de conversación persistente en el proceso, indexada por thread_id
      (cada sesión de chat del frontend usa su propio thread_id)
    """
    llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0.4)

    return create_agent(
        model=llm,
        tools=[buscar_informacion_turistica, consultar_clima],
        system_prompt=SYSTEM_PROMPT,
        checkpointer=InMemorySaver(),
    )
