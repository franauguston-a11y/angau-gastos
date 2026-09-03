import os
import json
import pandas as pd
import streamlit as st
from PIL import Image

# Importación segura para Streamlit Cloud
try:
    from google import genai
    from google.genai import types
except ImportError:
    st.error("⚠️ La librería 'google-genai' no está instalada en el entorno. Verificá el archivo requirements.txt.")
    st.stop()

# Configuración de la página
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

client = genai.Client(api_key=api_key)

# Inicializar base de datos temporal en sesión si no existe
if "gastos" not in st.session_state:
    st.session_state.gastos = []

# Sección de carga de comprobantes
st.markdown("### 📥 Subir Nuevo Comprobante")
imagen_subida = st.file_uploader(
    "Sacá una foto o subí el ticket/factura", type=["jpg", "jpeg", "png"]
)

if imagen_subida is not None:
    image = Image.open(imagen_subida)
    st.image(image, caption="Comprobante cargado", use_column_width=True)

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

                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[image, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    ),
                )

                resultado_json = json.loads(response.text)

                # Guardar en la sesión
                st.session_state.gastos.append(resultado_json)
                st.success("¡Comprobante procesado y registrado con éxito!")
                st.json(resultado_json)

            except Exception as e:
                st.error(f"Ocurrió un error al procesar la imagen: {e}")

# Visualización de gastos registrados
if st.session_state.gastos:
    st.markdown("---")
    st.markdown("### 📊 Historial de Gastos Registrados")
    df = pd.DataFrame(st.session_state.gastos)
    st.dataframe(df, use_container_width=True)

    # Botón para exportar a Excel
    @st.cache_data
    def convertir_a_excel(df_gastos):
        import io
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_gastos.to_excel(writer, index=False, sheet_name="Gastos")
        return output.getvalue()

    excel_data = convertir_a_excel(df)
    st.download_button(
        label="📥 Descargar planilla en Excel",
        data=excel_data,
        file_name="angau_gastos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
