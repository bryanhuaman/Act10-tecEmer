
 
 =======================
 INTERFAZ STREAMLIT
 # =======================
 
 st.set_page_config(page_title="Chat PDF con MongoDB + Gemini", page_icon="💬")
 st.title("💬 Chatbot de tu PDF (MongoDB + Gemini)")
 
 if "historial" not in st.session_state:
     st.session_state.historial = []
 
# Mostrar historial PRIMERO (antes de procesar la nueva pregunta)
 for msg in st.session_state.historial:
     if msg["rol"] == "usuario":
         st.chat_message("user").write(msg["texto"])
     else:
         st.chat_message("assistant").write(msg["texto"])
 
 pregunta = st.chat_input("Escribe tu pregunta sobre el PDF...")
 
 if pregunta:
     # Mostrar inmediatamente la pregunta del usuario
     st.chat_message("user").write(pregunta)
     st.session_state.historial.append({"rol": "usuario", "texto": pregunta})
 
    with st.chat_message("assistant"):
         with st.spinner("Buscando respuesta..."):
             try:
                 emb = crear_embedding(pregunta)
                 similares = buscar_similares(emb, k=5)
 
                 if not similares:
                     respuesta = "No encontré información relevante en el documento."
                 else:
                     respuesta = generar_respuesta(pregunta, similares)
             except Exception as e:
                 respuesta = f"⚠️ Ocurrió un error: {e}"
 
         st.write(respuesta)
 
         # Opcional: mostrar fuentes recuperadas
         if 'similares' in locals() and similares:
             with st.expander("🔍 Fragmentos recuperados"):
                 for i, c in enumerate(similares, 1):
                     st.markdown(f"**Fragmento {i}** — score: `{c['score']:.4f}`")
                     st.write(c["texto"][:500] + ("…" if len(c["texto"]) > 500 else ""))
                     st.divider()
 
     st.session_state.historial.append({"rol": "bot", "texto": respuesta})
from google import genai
def get_genai_client():
   return genai.Client(api_key=GOOGLE_API_KEY)
# Inicializa el cliente unificado de GenAI
lient = get_genai_client()
print("Modelos compatibles con generate_content:\n")
 Recorre la lista de modelos disponibles
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
