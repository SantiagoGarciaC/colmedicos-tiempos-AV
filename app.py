import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

#Para correr el programa ejecutar en la consola cmd la siguiente línea: streamlit run app.py
# Define los alcances (scopes)
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Convertir los secretos a JSON
json_key = json.loads(json.dumps(st.secrets["gcp_service_account"]))
creds = ServiceAccountCredentials.from_json_keyfile_dict(json_key, scope)

# Autenticación
client = gspread.authorize(creds)

# Abre el archivo (por nombre o por URL)
sheet = client.open("Informe_tiempos_Avianca(actualizado 31-03-2025)").sheet1  # También puedes usar .worksheet("nombre_hoja")

# Obtén los datos como lista de diccionarios
data = sheet.get_all_records()

# Configuración general
st.set_page_config(page_title="Tiempos de Atención Red Nacional - Avianca", layout="wide")
st.image("assets/logo.png", width=250, use_column_width=False)
#st.image("colmedicos.png", width=200)
st.title("Dashboard Tiempos de Atención Red Nacional - Avianca")
st.markdown("Análisis de tiempos de atención en exámenes médicos de ingreso, control y egreso para pacientes de **Avianca**.")

# Cargar datos
#df = pd.read_csv("tiemposAvianca_finalversion.csv")
df = pd.DataFrame(data)
df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True)
df['Hora inicio'] = pd.to_datetime(df['Hora inicio'])
df['Hora fin'] = pd.to_datetime(df['Hora fin'])

# Calcular tiempo de atención (en minutos y formato)
df['TiempoAtencionMin'] = (df['Hora fin'] - df['Hora inicio']).dt.total_seconds() / 60
df['TiempoAtencionFormato'] = df['TiempoAtencionMin'].apply(lambda x: f"{int(x//60)}h {int(x%60)}m")
df = df.rename(columns={'Anexo factura': 'Examen'})
df["CumpleTiempo"] = df["TiempoAtencionMin"] <= 120
# Calcular TiempoAtención en horas:
df["TiempoAtencionHoras"] = df["TiempoAtencionMin"] / 60

# Filtros
examen = st.multiselect("Selecciona examen(s):", df['Examen'].unique(), default=df['Examen'].unique())
ciudades = st.multiselect("Selecciona ciudad(es):", df['Ciudad'].unique(), default=df['Ciudad'].unique())
fechas = st.date_input("Selecciona rango de fechas:", [df['Fecha'].min(), df['Fecha'].max()])

df_filtros = df[
    (df['Examen'].isin(examen)) &
    (df['Ciudad'].isin(ciudades)) &
    (df['Fecha'] >= pd.to_datetime(fechas[0])) &
    (df['Fecha'] <= pd.to_datetime(fechas[1]))
]

# KPIs
tiempo_prom = df_filtros['TiempoAtencionMin'].mean()
cumplimiento = (df_filtros['CumpleTiempo']).mean() * 100
total_atenciones = len(df_filtros)
ciudad_top = df_filtros.groupby('Ciudad')['TiempoAtencionMin'].mean().idxmin()

col1, col2, col3, col4 = st.columns(4)
col1.metric("⏱️ Tiempo Promedio", f"{int(tiempo_prom//60)}h {int(tiempo_prom%60)}m")
col2.metric("📉 % Porcentaje de Cumplimiento (<2h)", f"{cumplimiento:.1f}%")
col3.metric("🏥 Total Pacientes", total_atenciones)
col4.metric("🏆 Ciudad Destacada", ciudad_top)

# Gráficos
# Gráfico 1
st.markdown("### 📊 Distribución Tiempo de Atención Pacientes Avianca")
# Escoger un tono de la paleta "Blues"
blue_tone = sns.color_palette("Blues")[5] # Índice de 0 (más claro) a 9 (más oscuro)
fig, ax = plt.subplots(figsize=(8, 2.5))
sns.histplot(df_filtros["TiempoAtencionHoras"], bins=20, kde=True, color=blue_tone, ax=ax, alpha = 0.3, shrink=0.8, edgecolor=None)

# Línea de referencia a las 2 horas
ax.axvline(2, color="red", linestyle="dashed", label="Promesa Atención (2h)")

# Etiquetas y título
#ax.set_title("Distribución del Tiempo de Atención Pacientes Avianca")
ax.set_xlabel("Tiempo de Atención (hr)")
ax.set_ylabel("Atenciones")
ax.legend()

# Mostrar en Streamlit
st.pyplot(fig)

st.markdown("---")
col1, col2 = st.columns(2)
#Gráfico 2
with col1:
    st.markdown("### 📊 Tiempo Promedio por Ciudad")
    ciudad_data = df_filtros.groupby("Ciudad")["TiempoAtencionMin"].mean().sort_values()
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    sns.barplot(x=ciudad_data.index, y=ciudad_data.values, ax=ax2, palette="Blues")

    # Etiquetas sobre las barras
    for i, val in enumerate(ciudad_data.values):
        ax2.text(i, val + 2, f"{int(val//60)}h {int(val%60)}m", ha='center', va='bottom', fontweight='bold')

    # Línea de referencia
    ax2.axhline(120, color="red", linestyle="--", label="Promesa Atención (2h)")

    # Eje Y con etiquetas personalizadas
    max_val = int(ciudad_data.max()) + 60
    ticks = range(0, max_val, 30)
    labels = [f"{t // 60}h" if t % 60 == 0 else f"{t // 60}h {t % 60}m" for t in ticks]
    ax2.set_yticks(ticks)
    ax2.set_yticklabels(labels)

    ax2.set_ylabel("Tiempo Promedio")
    ax2.set_xlabel("")
    ax2.set_xticklabels(ax2.get_xticklabels())
    ax2.legend(loc='upper left')
    st.pyplot(fig2)


#Gráfico 3
# 📊 Tiempo de Atención por Examen
with col2:
    st.markdown("### 📊 Tiempo Promedio por Examen")

# Agrupamiento y promedio
    examen_data = df_filtros.groupby("Examen")["TiempoAtencionMin"].mean().sort_values()

# Crear figura y ejes
    fig3, ax3 = plt.subplots(figsize=(10, 5))
    sns.barplot(x=examen_data.index, y=examen_data.values, palette="Blues", ax=ax3)

# Línea de referencia (2h = 120 min)
    ax3.axhline(120, color="red", linestyle="dashed", label="Promesa Atención (2h)")

# Etiquetas personalizadas "Xh Ym" encima de las barras
    for i, value in enumerate(examen_data.values):
        horas = int(value) // 60
        minutos = int(value) % 60
        etiqueta = f"{horas}h {minutos}m"
        ax3.text(i, value + 2, etiqueta, ha='center', va='bottom', fontsize=10, fontweight='bold')

# Estética
    ax3.set_xlabel("")  # Quitar etiqueta del eje X
    ax3.set_ylabel("Tiempo Promedio")
#ax.set_title("Tiempo Promedio de Atención por Examen Pacientes Avianca")
    ax3.set_xticklabels(examen_data.index)

# Cambiar eje Y a formato de horas y minutos (opcional)
    ticks = range(0, int(max(examen_data.values)) + 60, 30)  # Cada 30 min
    labels = [f"{t // 60}h" if t % 60 == 0 else f"{t // 60}h {t % 60}m" for t in ticks]
    ax3.set_yticks(ticks)
    ax3.set_yticklabels(labels)

# Leyenda y layout
    ax3.legend(loc='upper left')
    plt.tight_layout()

# Mostrar en Streamlit
    st.pyplot(fig3)

# Descargar tabla
st.markdown("### 📥 Descargar datos filtrados")
def convertir_csv(df):
    output = BytesIO()
    df.to_csv(output, index=False)
    return output.getvalue()

st.download_button("Descargar CSV", data=convertir_csv(df_filtros), file_name="tiempos_filtrados.csv", mime="text/csv")
