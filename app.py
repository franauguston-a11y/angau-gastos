import json
import pandas as pd
import streamlit as st
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials
from google import genai

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

# 2. Conexión a Google Sheets mediante gspread y Secrets
@st.cache_resource
def conectar_google_sheets():
    try:
        # Lee las credenciales de la cuenta de servicio desde los Secrets de Streamlit
        gcp_secrets = dict(st.secrets["gcp_service_account"])
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials = Credentials.from_service_account_info(gcp_secrets, scopes=scopes)
        gc = gspread.authorize(credentials)
        
        # Abre tu planilla 'angau_gastos'
        sheet = gc.open("angau_gastos").sheet1
        return sheet
    except Exception as e:
        return None

sheet = conectar_google_sheets()

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

                # Guardar directamente en Google Sheets
                if sheet:
                    sheet.append_row([
                        str(resultado_json.get("fecha", "")),
                        str(resultado_json.get("proveedor", "")),
                        str(resultado_json.get("categoria", "")),
                        str(resultado_json.get("total", 0.0))
                    ])
                    st.success("¡Comprobante procesado y guardado en Google Sheets con éxito!")
                else:
                    st.warning("El ticket se procesó pero no se pudo conectar con la planilla.")

                st.json(resultado_json)

            except Exception as e:
                st.error(f"Ocurrió un error al procesar la imagen: {e}")

# Visualización del Historial desde Google Sheets
st.markdown("---")
st.markdown("### 📊 Historial de Gastos en la Nube")

if sheet:
    try:
        data = sheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("La planilla está vacía. Sube tu primer ticket arriba.")
    except Exception as e:
        st.error(f"No se pudo cargar el historial desde Google Sheets: {e}")
