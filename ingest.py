"""
Script de ingesta — construye la base de conocimiento de un cliente
---------------------------------------------------------
Uso:
    python ingest.py jaime_duque
    python ingest.py restaurante_ejemplo

Qué hace:
    1. Carga todos los .md de app/conocimiento/<cliente_id>/
    2. Si existe fuentes.json en esa carpeta, rastrea cada URL listada
       y extrae su texto también
    3. Divide todo en fragmentos, calcula embeddings, y los guarda en
       una base vectorial Chroma PROPIA de ese cliente
       (chroma_db/<cliente_id>/) — así los clientes nunca se mezclan.

Por qué esto va separado de agente.py:
    Rastrear páginas web y calcular embeddings es lento (varios
    segundos por página). No queremos hacerlo dentro de una petición
    HTTP en vivo — se hace una vez, de antemano, y el agente solo LEE
    el resultado ya guardado.
"""
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader, WebBaseLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent / "app"
CONOCIMIENTO_DIR = BASE_DIR / "conocimiento"
CHROMA_ROOT = Path(__file__).resolve().parent / "chroma_db"


def _embeddings():
    return GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")


def cargar_documentos_markdown(carpeta_cliente: Path):
    if not any(carpeta_cliente.glob("*.md")):
        return []
    loader = DirectoryLoader(
        str(carpeta_cliente), glob="*.md", loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    return loader.load()


def cargar_documentos_web(carpeta_cliente: Path):
    fuentes_path = carpeta_cliente / "fuentes.json"
    if not fuentes_path.exists():
        return []

    with open(fuentes_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    urls = config.get("urls", [])
    if not urls:
        return []

    print(f"  Rastreando {len(urls)} URL(s)...")
    documentos = []
    for url in urls:
        try:
            loader = WebBaseLoader(url)
            docs = loader.load()
            documentos.extend(docs)
            print(f"    ✓ {url}")
        except Exception as e:
            print(f"    ✗ {url} — error: {e}")
    return documentos


def ingerir(cliente_id: str):
    carpeta_cliente = CONOCIMIENTO_DIR / cliente_id
    if not carpeta_cliente.exists():
        print(f"No existe la carpeta app/conocimiento/{cliente_id}/. Créala primero.")
        sys.exit(1)

    print(f"Cargando fuentes para '{cliente_id}'...")
    documentos = cargar_documentos_markdown(carpeta_cliente) + cargar_documentos_web(carpeta_cliente)

    if not documentos:
        print("No se encontró ningún documento (.md) ni fuentes.json con URLs. Nada que indexar.")
        sys.exit(1)

    print(f"{len(documentos)} documento(s) cargados. Dividiendo en fragmentos...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    fragmentos = splitter.split_documents(documentos)

    destino = CHROMA_ROOT / cliente_id
    print(f"Calculando embeddings y guardando {len(fragmentos)} fragmento(s) en {destino}...")

    # Empezar limpio cada vez que se re-ingesta, para no acumular versiones viejas
    if destino.exists():
        import shutil
        shutil.rmtree(destino)

    # Insertamos en lotes pequeños con pausa entre cada uno para no exceder
    # el límite del tier gratuito de Gemini (100 peticiones de embeddings/minuto).
    # Con lotes de 10 y 3s de pausa, el ritmo queda muy por debajo del límite.
    TAMANO_LOTE = 10
    PAUSA_SEGUNDOS = 3

    vectorstore = Chroma(persist_directory=str(destino), embedding_function=_embeddings())

    total_lotes = (len(fragmentos) + TAMANO_LOTE - 1) // TAMANO_LOTE
    for i in range(0, len(fragmentos), TAMANO_LOTE):
        lote = fragmentos[i:i + TAMANO_LOTE]
        numero_lote = i // TAMANO_LOTE + 1
        intentos = 0
        while True:
            try:
                vectorstore.add_documents(lote)
                print(f"  Lote {numero_lote}/{total_lotes} indexado ✓")
                break
            except Exception as e:
                intentos += 1
                if intentos >= 4:
                    raise
                espera = 20 * intentos
                print(f"  Lote {numero_lote}/{total_lotes} falló ({e}). Reintentando en {espera}s...")
                time.sleep(espera)
        if i + TAMANO_LOTE < len(fragmentos):
            time.sleep(PAUSA_SEGUNDOS)

    print(f"✅ Listo. Base de conocimiento de '{cliente_id}' actualizada.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python ingest.py <cliente_id>")
        print("Ejemplo: python ingest.py jaime_duque")
        sys.exit(1)

    ingerir(sys.argv[1])
