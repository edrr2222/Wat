# BogotáGuía

Asistente conversacional de turismo para Bogotá y sus alrededores, construido con **LangChain**. Combina dos técnicas de IA en un solo agente:

1. **RAG (Retrieval-Augmented Generation)** — responde basándose en una base de conocimiento propia (no inventa lugares), indexada vectorialmente con Chroma.
2. **Agente con herramientas (tool calling)** — el modelo decide por sí solo cuándo buscar en la base de conocimiento y cuándo consultar el clima real antes de responder.

## Stack

- **LangChain 1.0+** (`create_agent`, la API moderna basada en LangGraph — reemplaza al patrón anterior `create_tool_calling_agent` + `AgentExecutor`)
- **Chroma** — base de datos vectorial local (no necesita servidor aparte)
- **Google Gemini** (`gemini-2.5-flash` + `text-embedding-004`) — API gratuita
- **Open-Meteo** — API de clima gratuita, sin necesidad de clave
- **FastAPI** — expone el agente como chat web

> **Nota sobre versiones**: LangChain es una librería que cambia rápido. En octubre de 2025 lanzaron la versión 1.0, que reorganizó por completo el módulo de agentes — `AgentExecutor` se movió a un paquete separado (`langchain_classic`). Si en el futuro ves un error de import similar, es señal de que la librería volvió a cambiar; revisa la [documentación oficial de agentes](https://docs.langchain.com/oss/python/langchain/agents) para la sintaxis vigente.
>
> Lo mismo pasa con los **nombres de modelo de Gemini** — Google los renueva y retira con frecuencia (por ejemplo, `gemini-2.5-flash` dejó de estar disponible para cuentas nuevas en julio de 2026, y `text-embedding-004` fue retirado por completo, reemplazado por `gemini-embedding-001`). Por eso este proyecto usa el alias `gemini-flash-latest` en vez de un nombre de versión específico — Google lo mantiene apuntando siempre al modelo Flash estable más reciente. Si en el futuro te sale un error 404 de modelo no encontrado, revisa [ai.google.dev/gemini-api/docs/models](https://ai.google.dev/gemini-api/docs/models) para el nombre vigente.

## Cómo correrlo

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
copy .env.example .env       # o `cp` en macOS/Linux
```

Edita `.env` con tu clave gratuita de Gemini (créala en https://aistudio.google.com/apikey):
```
GEMINI_API_KEY=tu_clave_aqui
```

Luego:
```bash
uvicorn app.main:app --reload
```

Abre `http://localhost:8000`. La primera pregunta tarda un poco más porque indexa la base de conocimiento en Chroma automáticamente (queda guardada en `chroma_db/` para las siguientes veces).

## Cómo pensar la diferencia entre esto y el proyecto anterior ("¿Qué hago hoy?")

Vale la pena que entiendas la diferencia si te preguntan en una entrevista:

| | ¿Qué hago hoy? | BogotáGuía |
|---|---|---|
| Técnica | Búsqueda vectorial directa + vector de preferencia que se actualiza a mano | RAG orquestado por un agente LangChain |
| Quién decide qué buscar | Tu código (siempre busca) | El modelo decide si busca en la base de conocimiento, si consulta el clima, o ninguna de las dos |
| Conversación | Sin memoria de turnos previos | Memoria de conversación por `thread_id` (checkpointer de LangGraph) |
| Nivel de abstracción | Bajo — controlas cada paso manualmente | Alto — LangChain/LangGraph orquesta el ciclo de razonamiento-acción del agente |

## Estructura

```
bogota-guia-langchain/
├── requirements.txt
├── .env.example
└── app/
    ├── main.py                # FastAPI: sirve el chat y el endpoint /api/chat
    ├── agente.py               # Construcción del agente LangChain (RAG + herramientas + memoria)
    ├── conocimiento/            # Base de conocimiento en Markdown (lo que el RAG indexa)
    │   ├── atractivos.md
    │   ├── excursiones.md
    │   └── practico.md
    └── templates/index.html    # Interfaz de chat
```

## Siguientes pasos posibles

- Agregar más documentos a `conocimiento/` (basta con soltar un `.md` nuevo — se re-indexa solo)
- Cambiar Chroma por `pgvector` para reutilizar la misma infraestructura del proyecto "¿Qué hago hoy?"
- Agregar una herramienta de geolocalización para recomendar según cercanía real
- Añadir streaming de la respuesta (LangChain lo soporta nativamente) para que el chat se sienta más fluido

---

*Proyecto de portafolio. La información turística es de referencia — verifica horarios y precios actuales antes de viajar.*
