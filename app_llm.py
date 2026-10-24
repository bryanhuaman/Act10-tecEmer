

"""# Ingest"""

import pymongo
# Conexión a MongoDB Atlas
client = pymongo.MongoClient(MONGODB_URI)
db = client.pdf_embeddings_db
collection = db.pdf_vectors
collection.insert_one({"a":"sample"})

# Instalar el nuevo SDK (en Colab):
# !pip install -q google-genai pymongo PyPDF2

import os
import pymongo
from google import genai
from google.genai import types
from PyPDF2 import PdfReader

# =======================
# CONFIGURACIÓN
# =======================
#GOOGLE_API_KEY = GOOGLE_API_KEY
#MONGODB_URI = MONGODB_URI

if not GOOGLE_API_KEY or not MONGODB_URI:
    raise ValueError("Faltan GOOGLE_API_KEY o MONGODB_URI en las variables de entorno.")

# Cliente del nuevo SDK
client_genai = genai.Client(api_key=GOOGLE_API_KEY)

# Cliente de MongoDB (lo dejo a nivel de módulo para que `procesar_pdf` lo use)
client_mongo = pymongo.MongoClient(MONGODB_URI)
db = client_mongo.pdf_embeddings_db
collection = db.pdf_vectors

# =======================
# LECTURA DEL PDF
# =======================
def leer_pdf(path_pdf):
    reader = PdfReader(path_pdf)
    texto = ""
    for page in reader.pages:
        page_text = page.extract_text() or ""
        texto += page_text + "\n"
    return texto.strip()

# =======================
# EMBEDDINGS (SDK nuevo)
# =======================
def crear_embedding(texto, task_type="RETRIEVAL_DOCUMENT"):
    response = client_genai.models.embed_content(
        model="gemini-embedding-001",
        contents=texto,
        config=types.EmbedContentConfig(
            task_type=task_type,
        ),
    )
    return response.embeddings[0].values

# =======================
# ÍNDICE VECTORIAL EN ATLAS
# =======================
def crear_indice_vectorial():
    from pymongo.operations import SearchIndexModel

    # Si el índice ya existe, esto fallará — puedes envolverlo en try/except
    search_index_model = SearchIndexModel(
        definition={
            "fields": [
                {
                    "type": "vector",
                    "path": "embedding",
                    "similarity": "dotProduct",
                    "numDimensions": 3072,   # debe coincidir con el modelo
                }
            ]
        },
        name="vector_index",
        type="vectorSearch",
    )
    try:
        collection.create_search_index(model=search_index_model)
        print("Índice vectorial creado.")
    except Exception as e:
        print(f"Aviso al crear índice (puede que ya exista): {e}")

# =======================
# PROCESO PRINCIPAL
# =======================
def procesar_pdf(ruta_pdf):
    texto = leer_pdf(ruta_pdf)
    if not texto:
        print("El PDF no contiene texto.")
        return

    # Chunking simple por caracteres
    trozos = [texto[i:i+1000] for i in range(0, len(texto), 1000)]

    documentos = []
    for i, chunk in enumerate(trozos):
        embedding = crear_embedding(chunk, task_type="RETRIEVAL_DOCUMENT")
        documentos.append({
            "id": i,
            "texto": chunk,
            "embedding": embedding,
        })

    collection.insert_many(documentos)
    print(f"Se insertaron {len(documentos)} fragmentos con embeddings.")

# =======================
# USO
# =======================
if __name__ == "__main__":
    crear_indice_vectorial()
    procesar_pdf("aws-cloud-adoption-framework_XL.pdf")
    print("✅ Embeddings generados y almacenados en MongoDB Atlas.")

# Commented out IPython magic to ensure Python compatibility.
# %%writefile app.py
# import streamlit as st
# import pymongo
# from google import genai
# from google.genai import types
# import numpy as np
# 
# # =======================
# # CONFIGURACIÓN
# # =======================
# 
# GOOGLE_API_KEY = st.secrets["app"]["GOOGLE_API_KEY"]
# MONGODB_URI = st.secrets["app"]["MONGODB_URI"]
# 
# if not GOOGLE_API_KEY or not MONGODB_URI:
#     st.error("❌ Faltan las variables de entorno GOOGLE_API_KEY o MONGODB_URI")
#     st.stop()
# 
# # =======================
# # CLIENTES (cacheados)
# # =======================
# 
# @st.cache_resource
# def get_genai_client():
#     return genai.Client(api_key=GOOGLE_API_KEY)
# 
# @st.cache_resource
# def get_mongo_collection():
#     client = pymongo.MongoClient(MONGODB_URI)
#     db = client["pdf_embeddings_db"]
#     return db["pdf_vectors"]
# 
# client_genai = get_genai_client()
# collection = get_mongo_collection()
# 
# # =======================
# # FUNCIONES
# # =======================
# 
# def crear_embedding(texto: str):
#     """
#     Genera embedding de la query con el mismo modelo y dimensión que se usó
#     al indexar (gemini-embedding-001, 768 dims, normalizado L2).
# 
#     IMPORTANTE: para queries de búsqueda usar task_type='RETRIEVAL_QUERY'
#     (al indexar se usó 'RETRIEVAL_DOCUMENT').
#     """
#     response = client_genai.models.embed_content(
#         model="gemini-embedding-001",
#         contents=texto,
#         config=types.EmbedContentConfig(
#             task_type="RETRIEVAL_QUERY",
#         ),
#     )
#     return response.embeddings[0].values
# 
# def buscar_similares(embedding, k=5):
#     """
#     Busca los documentos más similares en MongoDB Atlas Vector Search.
#     Requiere el índice 'vector_index' creado sobre el campo 'embedding'.
#     """
#     pipeline = [
#         {
#             "$vectorSearch": {
#                 "index": "vector_index",
#                 "path": "embedding",
#                 "queryVector": embedding,
#                 "numCandidates": 100,
#                 "limit": k,
#             }
#         },
#         {
#             "$project": {
#                 "_id": 0,
#                 "texto": 1,
#                 "score": {"$meta": "vectorSearchScore"},
#             }
#         },
#     ]
#     return list(collection.aggregate(pipeline))
# 
# def generar_respuesta(pregunta: str, contextos: list[dict]) -> str:
#     """Usa Gemini para responder con contexto recuperado (RAG)."""
#     contexto = "\n\n".join([c["texto"] for c in contextos])
#     prompt = f"""Eres un asistente experto. Usa EXCLUSIVAMENTE el siguiente contexto para responder la pregunta del usuario. Si la respuesta no está en el contexto, indícalo claramente.
# 
# Contexto:
# {contexto}
# 
# Pregunta: {pregunta}
# 
# Responde de forma concisa y clara en español."""
# 
#     response = client_genai.models.generate_content(
#         model="gemini-2.5-flash",
#         contents=prompt,
#     )
#     return response.text
# 
# # =======================
# # INTERFAZ STREAMLIT
# # =======================
# 
# st.set_page_config(page_title="Chat PDF con MongoDB + Gemini", page_icon="💬")
# st.title("💬 Chatbot de tu PDF (MongoDB + Gemini)")
# 
# if "historial" not in st.session_state:
#     st.session_state.historial = []
# 
# # Mostrar historial PRIMERO (antes de procesar la nueva pregunta)
# for msg in st.session_state.historial:
#     if msg["rol"] == "usuario":
#         st.chat_message("user").write(msg["texto"])
#     else:
#         st.chat_message("assistant").write(msg["texto"])
# 
# pregunta = st.chat_input("Escribe tu pregunta sobre el PDF...")
# 
# if pregunta:
#     # Mostrar inmediatamente la pregunta del usuario
#     st.chat_message("user").write(pregunta)
#     st.session_state.historial.append({"rol": "usuario", "texto": pregunta})
# 
#     with st.chat_message("assistant"):
#         with st.spinner("Buscando respuesta..."):
#             try:
#                 emb = crear_embedding(pregunta)
#                 similares = buscar_similares(emb, k=5)
# 
#                 if not similares:
#                     respuesta = "No encontré información relevante en el documento."
#                 else:
#                     respuesta = generar_respuesta(pregunta, similares)
#             except Exception as e:
#                 respuesta = f"⚠️ Ocurrió un error: {e}"
# 
#         st.write(respuesta)
# 
#         # Opcional: mostrar fuentes recuperadas
#         if 'similares' in locals() and similares:
#             with st.expander("🔍 Fragmentos recuperados"):
#                 for i, c in enumerate(similares, 1):
#                     st.markdown(f"**Fragmento {i}** — score: `{c['score']:.4f}`")
#                     st.write(c["texto"][:500] + ("…" if len(c["texto"]) > 500 else ""))
#                     st.divider()
# 
#     st.session_state.historial.append({"rol": "bot", "texto": respuesta})

from google import genai

def get_genai_client():
    return genai.Client(api_key=GOOGLE_API_KEY)

# Inicializa el cliente unificado de GenAI
client = get_genai_client()

print("Modelos compatibles con generate_content:\n")
# Recorre la lista de modelos disponibles
for model in client.models.list():
    if "generateContent" in model.supported_actions:
        print(f"- {model.name}")

"""# Deploy con Forward"""

# Ejecuta Streamlit con la aplicación indicada
# CORS (Cross-Origin Resource Sharing): controla solicitudes desde otros dominios
# Se desactiva CORS para permitir acceso desde orígenes distintos
# XSRF (Cross-Site Request Forgery): ataque que fuerza acciones no autorizadas
# Se desactiva XSRF para evitar bloqueos al acceder a la app desde entornos como Colab
# Redirige la salida y errores al archivo logs.txt
# & Ejecuta el proceso en segundo plano
!streamlit run /content/app.py --server.enableCORS false --server.enableXsrfProtection false &>/content/logs.txt &

!wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
!chmod +x cloudflared-linux-amd64

!./cloudflared-linux-amd64 tunnel --url http://localhost:8501
