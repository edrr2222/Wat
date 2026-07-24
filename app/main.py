import os
from pathlib import Path

import json

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .agente import BASE_DIR, CLIENTE_ID, construir_agente
from .clientes import obtener_cliente

app = FastAPI(title="Asistente virtual multi-cliente")
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

cliente = obtener_cliente(CLIENTE_ID)
agente = construir_agente(CLIENTE_ID)


def _cargar_imagenes(cliente_id: str) -> dict:
    ruta = BASE_DIR / "conocimiento" / cliente_id / "imagenes.json"
    if not ruta.exists():
        return {}
    with open(ruta, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Descarta claves de comentario y entradas vacías (sin URL asignada aún)
    return {k: v for k, v in data.items() if not k.startswith("_") and v}


IMAGENES_CLIENTE = _cargar_imagenes(CLIENTE_ID)


class MensajeRequest(BaseModel):
    session_id: str
    mensaje: str


def _extraer_texto(content) -> str:
    """El contenido de un mensaje de LangChain puede ser un string simple o
    una lista de bloques (ej: [{"type": "text", "text": "..."}]) dependiendo
    del modelo. Esto normaliza ambos casos a un string plano."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        partes = []
        for bloque in content:
            if isinstance(bloque, str):
                partes.append(bloque)
            elif isinstance(bloque, dict) and bloque.get("type") == "text":
                partes.append(bloque.get("text", ""))
        return "".join(partes) if partes else str(content)
    return str(content)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"cliente": cliente})


@app.get("/api/imagenes")
def imagenes():
    return IMAGENES_CLIENTE


@app.post("/api/chat")
def chat(payload: MensajeRequest):
    resultado = agente.invoke(
        {"messages": [{"role": "user", "content": payload.mensaje}]},
        config={"configurable": {"thread_id": payload.session_id}},
    )
    ultima_respuesta = _extraer_texto(resultado["messages"][-1].content)
    return {"respuesta": ultima_respuesta}


@app.get("/api/health")
def health():
    return {"status": "ok", "cliente_activo": CLIENTE_ID}
