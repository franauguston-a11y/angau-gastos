import json
import pandas as pd
import streamlit as st
from PIL import Image
from google import genai
import requests

# Configuración de la página
st.set_page_config(
    page_title="Angaú Cervecería - Control de Gastos Detallado",
    page_icon="🍻",
    layout="centered",
)

# 1. Configuración de Gemini 3.6 Flash
GEMINI_MODEL = "gemini-2.5-flash"

api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ No se encontró la API Key de Gemini en los Secrets.")
    st.stop()

client_ai = genai.Client(api_key=api_key)
APPS_SCRIPT_URL = st.secrets.get("APPS_SCRIPT_URL", "")

# 2. Funciones de red
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
        response = requests.post(APPS_SCRIPT_URL, json=datos, allow_redirects=True, timeout=15)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Error detallado de red: {e}")
        return False

# 3. Autenticación
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
st.subheader("Control Avanzado de Comprobantes e Insumos")

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

# Carga de comprobantes
st.markdown("### 📥 Subir Nuevo Comprobante")
imagen_subida = st.file_uploader(
    "Sacá una foto o subí el ticket/factura detallada", type=["jpg", "jpeg", "png"]
)

if imagen_subida is not None:
    image = Image.open(imagen_subida)
    st.image(image, caption="Comprobante cargado", use_container_width=True)

    if st.button("Analizar Detalle con IA", type="primary"):
        with st.spinner("Gemini analizando productos, cantidades y precios..."):
            try:
                prompt = (
                    "Analiza este comprobante de gasto de manera avanzada para un negocio gastronómico. "
                    "Extrae la cabecera y el detalle de cada producto en un JSON estricto con esta estructura exacta: "
                    '{"fecha": "YYYY-MM-DD", "proveedor": "Nombre del comercio", '
                    '"categoria": "Insumos/Materia Prima, Logística, Servicios, Mantenimiento, u Otros", '
                    '"items": ['
                    '  {"descripcion": "Nombre del producto", "cantidad": 1.0, "precio_unitario": 0.00, "subtotal": 0.00}'
                    ']}'
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

                # Enviar a Google Sheets
                exito = guardar_gasto(resultado_json)
                if exito:
                    st.success("¡Ticket analizado por completo y guardado detalladamente en Google Sheets!")
                else:
                    st.warning("El ticket se procesó pero hubo un problema al escribir en la planilla.")

                st.json(resultado_json)

            except Exception as e:
                st.error(f"Ocurrió un error al procesar la imagen: {e}")

# Visualización del Historial Detallado
st.markdown("---")
st.markdown("### 📊 Historial Detallado de Gastos e Insumos")

df_historial = obtener_historial()
if not df_historial.empty:
    st.dataframe(df_historial, use_container_width=True)
else:
    st.info("La planilla está vacía o cargando datos...")
