import os
import json
import pandas as pd
import streamlit as st
from PIL import Image
import google.generativeai as genai

# Configuración de la página y título personalizado
st.set_page_config(
    page_title="Angaú Cervecería - Control de Gastos",
    page_icon="🍻",
    layout="centered",
)

st.title("🍻 Angaú Cervecería")
st.subheader("Control de Gastos y Comprobantes")

# Configurar API Key de Gemini
api_key = None
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
elif "GEMINI_API_KEY" in os.environ:
    api_key = os.environ["GEMINI_API_KEY"]

if not api_key:
    st.error("⚠️ No se encontró la API Key de Gemini. Configura los Secrets en Streamlit Cloud.")
    st.stop()

genai.configure(api_key=api_key)

# Archivo persistente en la nube para guardar los gastos
EXCEL_FILE = "gastos_angau.xlsx"

# Cargar gastos existentes desde el archivo en la nube si existe
if "gastos" not in st.session_state:
    if os.path.exists(EXCEL_FILE):
        try:
            df_guardado = pd.read_excel(EXCEL_FILE)
            st.session_state.gastos = df_guardado.to_dict(orient="records")
        except Exception:
            st.session_state.gastos = []
    else:
        st.session_state.gastos = []

# Sección de carga de comprobantes
st.markdown("### 📥 Subir Nuevo Comprobante")
imagen_subida = st.file_uploader(
    "Sacá una foto o subí el ticket/factura", type=["jpg", "jpeg", "png"]
)

if imagen_subida is not None:
    image = Image.open(imagen_subida)
    st.image(image, caption="Comprobante cargado", use_container_width=True)

    if st.button("Analizar Comprobante con IA", type="primary"):
        with st.spinner("Procesando ticket con Gemini..."):
            try:
                prompt = (
                    "Analiza este comprobante de gasto para un negocio gastronómico/cervecero. "
                    "Extrae la siguiente información en formato JSON estricto: "
                    '{"fecha": "YYYY-MM-DD o desconocido", "proveedor": "Nombre del comercio", '
                    '"categoria": "Insumos/Materia Prima, Logística, Servicios, Mantenimiento, u Otros", '
                    '"total": 0.00}'
                )

                # Usando el modelo optimizado de alta precisión para imágenes
                model = genai.GenerativeModel("gemini-3.6-flash")
                response = model.generate_content([image, prompt])

                # Limpiar texto por si devuelve formato markdown
                texto_respuesta = response.text.strip()
                if texto_respuesta.startswith("```json"):
                    texto_respuesta = texto_respuesta[7:]
                if texto_respuesta.endswith("```"):
                    texto_respuesta = texto_respuesta[:-3]

                resultado_json = json.loads(texto_respuesta.strip())

                # Guardar en la sesión y actualizar el archivo Excel en la nube
                st.session_state.gastos.append(resultado_json)
                df_temp = pd.DataFrame(st.session_state.gastos)
                df_temp.to_excel(EXCEL_FILE, index=False)

                st.success("¡Comprobante procesado, registrado y guardado en la nube con éxito!")
                st.json(resultado_json)

            except Exception as e:
                st.error(f"Ocurrió un error al procesar la imagen: {e}")

# Visualización de gastos registrados
if st.session_state.gastos:
    st.markdown("---")
    st.markdown("### 📊 Historial de Gastos Registrados")
    df = pd.DataFrame(st.session_state.gastos)
    st.dataframe(df, use_container_width=True)

    # Botón para descargar el Excel actualizado desde la nube
    if os.path.exists(EXCEL_FILE):
        with open(EXCEL_FILE, "rb") as f:
            excel_bytes = f.read()

        st.download_button(
            label="📥 Descargar planilla completa actualizada",
            data=excel_bytes,
            file_name="angau_gastos_actualizado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
