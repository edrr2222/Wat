# Asistente virtual multi-cliente (LangChain + RAG)

Asistente conversacional reutilizable para **cualquier tipo de negocio** — parques temáticos, restaurantes, hoteles, clínicas, lo que sea. Cada cliente se configura con un bloque corto de texto + sus propios documentos; el prompt del sistema se arma solo.

## Arquitectura

```
app/
├── clientes.py                    ← un bloque corto por cliente (nombre, tipo, descripción...)
├── agente.py                      ← 100% genérico, no sabe nada de ningún cliente en particular
├── conocimiento/
│   ├── jaime_duque/
│   │   ├── historia.md
│   │   ├── zonas.md
│   │   ├── tarifas.md
│   │   ├── consejos.md
│   │   └── fuentes.json           ← URLs que se rastrean automáticamente
│   └── restaurante_ejemplo/
│       └── info.md
chroma_db/
├── jaime_duque/                   ← base vectorial propia de este cliente
└── restaurante_ejemplo/           ← nunca se mezclan entre sí
ingest.py                          ← construye/actualiza la base de un cliente
```

## Cómo agregar un cliente nuevo (parque, restaurante, hospital, lo que sea)

1. Crea la carpeta `app/conocimiento/<id_cliente>/`
2. Dentro, agrega documentos `.md` con la información que quieras que el asistente use
3. (Opcional) Agrega un `fuentes.json` con URLs para que el sistema las rastree automáticamente:
   ```json
   { "urls": ["https://ejemplo.com/horarios", "https://ejemplo.com/menu"] }
   ```
4. Agrega un bloque en `app/clientes.py`:
   ```python
   "mi_cliente_nuevo": {
       "nombre": "Nombre del negocio",
       "tipo_negocio": "hospital / hotel / restaurante / lo que sea",
       "descripcion_corta": "Una o dos frases de contexto.",
       "carpeta_conocimiento": "mi_cliente_nuevo",
       "emoji": "🏥",
       "usa_clima": False,
       "sugerencias": ["Pregunta de ejemplo 1", "Pregunta de ejemplo 2"],
   }
   ```
5. Corre la ingesta:
   ```bash
   python ingest.py mi_cliente_nuevo
   ```
6. Cambia `CLIENTE_ACTIVO=mi_cliente_nuevo` en tu `.env`

Eso es todo — nunca tienes que tocar `agente.py`, `main.py` ni el prompt del sistema.

## Cómo correrlo

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env
```

Pon tu clave de Gemini en `.env`. Luego **construye la base de conocimiento del cliente activo**:

```bash
python ingest.py jaime_duque
```

Esto rastrea los `.md` y las URLs de `fuentes.json`, calcula embeddings, y los guarda en `chroma_db/jaime_duque/`. Tarda un poco (varios segundos por URL) — es normal, solo se hace una vez (o cada vez que quieras refrescar la info).

Luego levanta el servidor:
```bash
uvicorn app.main:app --reload
```

Abre `http://localhost:8000`.

## Cómo alimentar la base de conocimiento — resumen de opciones

| Fuente | Cómo |
|---|---|
| Texto que tú escribes | Archivo `.md` en la carpeta del cliente |
| Páginas web del cliente | `fuentes.json` con la lista de URLs — ya implementado |
| PDF (folleto, menú, manual) | Agregar `PyPDFLoader` de `langchain_community` en `ingest.py` |
| Excel/CSV (catálogo, inventario) | Agregar `CSVLoader` |
| Sitio completo (todas las páginas) | Reemplazar la lista manual de URLs por `SitemapLoader` |

La estructura de `ingest.py` ya está pensada para agregar estos otros cargadores sin romper nada — cada uno simplemente se agrega a la lista de `documentos` antes de dividir y guardar.

## ⚠️ Antes de mostrarle esto a un cliente real

- **Verifica los precios y horarios** — cambian con frecuencia y el asistente solo sabe lo que hayas indexado. Los datos de Jaime Duque en este repo están marcados con un aviso de verificación.
- **Vuelve a correr `python ingest.py <cliente>`** cada vez que la información de origen cambie — el asistente no se actualiza solo.

---

*Proyecto de portafolio. Los datos de "restaurante_ejemplo" son ficticios, solo para demostrar que la arquitectura funciona con cualquier tipo de negocio.*
