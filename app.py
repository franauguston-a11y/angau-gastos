import json
import pandas as pd
import streamlit as st
from PIL import Image
from google import genai
import requests

# Configuración de la página
st.set_page_config(
    page_title="Angaú Cervecería - Control de Gastos",
    page_icon="🍻",
    layout="centered",
)

# 1. Configuración de Gemini 3.6 Flash
GEMINI_MODEL = "gemini-3.6-flash"

api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ No se encontró la API Key de Gemini en los Secrets.")
    st.stop()

client_ai = genai.Client(api_key=api_key)
APPS_SCRIPT_URL = st.secrets.get("APPS_SCRIPT_URL", "")

# 2. Funciones para leer y escribir en Google Sheets vía Apps Script
def obtener_historial():
    try:
        response = requests.get(APPS_SCRIPT_URL, allow_redirects=True, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return pd.DataFrame(data)
    except Exception:
        pass
    return pd.DataFrame()

def guardar_gasto(datos):
    try:
        response = requests.post(APPS_SCRIPT_URL, json=datos, allow_redirects=True, timeout=10)
        # Si la petición llega bien al Apps Script, damos por exitoso el guardado
        return response.status_code == 200
    except Exception as e:
        st.error(f"Error detallado de red: {e}")
        return False

# 3. Módulo de Autenticación (Login Seguro)
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🍻 Angaú Cervecería")
    st.subheader("Acceso Restringido - Control de Gastos")
    
    with st.form("login_form"):
        usuario = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submit_login = st.form_submit_button("Ingresar")
        
        if submit_login:
            user_valido = st.secrets.get("AUTH_USER", "admin")
            pass_valida = st.secrets.get("AUTH_PASSWORD", "angau2026")
            
            if usuario == user_valido and password == pass_valida:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
    st.stop()

# --- APLICACIÓN PRINCIPAL ---
st.title("🍻 Angaú Cervecería")
st.subheader("Control de Gastos y Comprobantes")

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

# Carga de comprobantes
st.markdown("### 📥 Subir Nuevo Comprobante")
imagen_subida = st.file_uploader(
    "Sacá una foto o subí el ticket/factura", type=["jpg", "jpeg", "png"]
)

if imagen_subida is not None:
    image = Image.open(imagen_subida)
    st.image(image, caption="Comprobante cargado", use_container_width=True)

    if st.button("Analizar Comprobante con IA", type="primary"):
        with st.spinner("Procesando ticket con Gemini 3.6 Flash..."):
            try:
                prompt = (
                    "Analiza este comprobante de gasto para un negocio gastronómico/cervecero. "
                    "Extrae la siguiente información en formato JSON estricto: "
                    '{"fecha": "YYYY-MM-DD o desconocido", "proveedor": "Nombre del comercio", '
                    '"categoria": "Insumos/Materia Prima, Logística, Servicios, Mantenimiento, u Otros", '
                    '"total": 0.00}'
                )

                response = client_ai.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=[image, prompt]
                )

                texto_respuesta = response.text.strip()
                if texto_respuesta.startswith("```json"):
                    texto_respuesta = texto_respuesta[7:]
                if texto_respuesta.endswith("```"):
                    texto_respuesta = texto_respuesta[:-3]

                resultado_json = json.loads(texto_respuesta.strip())

                # Enviar a Google Sheets mediante Apps Script
                exito = guardar_gasto(resultado_json)
                if exito:
                    st.success("¡Comprobante procesado y guardado en Google Sheets con éxito!")
                else:
                    st.warning("El ticket se procesó pero hubo un problema al escribir en la planilla.")

                st.json(resultado_json)

            except Exception as e:
                st.error(f"Ocurrió un error al procesar la imagen: {e}")

# Visualización del Historial desde Google Sheets
st.markdown("---")
st.markdown("### 📊 Historial de Gastos en la Nube")

df_historial = obtener_historial()
if not df_historial.empty:
    st.dataframe(df_historial, use_container_width=True)
else:
    st.info("La planilla está vacía o cargando datos...")
