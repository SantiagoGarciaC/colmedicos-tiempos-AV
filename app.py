import streamlit as st
import pandas as pd
import seaborn as sns
from scipy.stats import gaussian_kde
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
import plotly.figure_factory as ff
from io import BytesIO
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

def load_data():
    # Define los alcances (scopes)
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    # Convertir los secretos a JSON
    json_key = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json_key, scope)

    # Autenticación
    client = gspread.authorize(creds)

    # Abre el archivo (por nombre o por URL)
    sheet = client.open("Informe_tiempos_Avianca(actualizado 31-03-2025)").sheet1  # También puedes usar .worksheet("nombre_hoja")

    # Obtén los datos como lista de diccionarios
    data = sheet.get_all_records()

    # Cargar datos
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

df= load_data()

azul_oscuro = "#150169"
azul_claro_1 = "#2356C6"
azul_claro_2 = "#00A2E4"
rojo_col = "#E63E62"
naranja_col = "#FF8C00"

# Configuración general de la página
st.set_page_config(page_title="Tiempos de Atención - Avianca", layout="wide")

col1, col2, col3 = st.columns([3, 6, 2])
with col2:
    st.image("assets/logo.png", width=350,  use_container_width=False)
st.title("Seguimiento tiempos de atención - Avianca")
st.markdown("Análisis de tiempos de atención en exámenes médicos de ingreso, control, egreso y medicina laboral para pacientes de **Avianca**.")


clase_ciudades = {
    "Sedes propias": ["Medellín", "Bogotá", "Cali"],
    "Rionegro": ["Rionegro"],
    "Red nacional": list(set(df['Ciudad'].unique()) - {"Medellín", "Bogotá", "Cali", "Rionegro"})
}
clase_sedes = {}
for i in range(len(df['Ciudad'].unique())):
    clase_sedes[df['Ciudad'].unique()[i]] = df[df['Ciudad']==df['Ciudad'].unique()[i]]['Sede'].unique().tolist()

# Filtros Sidebar
st.sidebar.title("Filtros seleccionados")
examen = st.sidebar.multiselect("Selecciona examen(es):", df['Examen'].unique(), default=df['Examen'].unique())
clase_seleccionada = st.sidebar.multiselect("Selecciona tipo sede(s):", options= df['Clase'].unique(), default=['Sedes propias'])

# Obtener ciudades correspondientes a las clases seleccionadas
ciudades_filtradas = []
for clase in clase_seleccionada:
    ciudades_filtradas.extend(clase_ciudades.get(clase, []))
# Quitar duplicados manteniendo orden
ciudades_filtradas = list(dict.fromkeys(ciudades_filtradas))
ciudades_seleccionadas = st.sidebar.multiselect(
    "Selecciona ciudad(es):",
    options=ciudades_filtradas,
    default=ciudades_filtradas
)


# Obtener sedes correspondientes a las ciudades seleccionadas
sedes_filtradas = []
for ciudad in ciudades_seleccionadas:
    sedes_filtradas.extend(clase_sedes.get(ciudad, []))
# Quitar duplicados manteniendo orden
sedes_filtradas = list(dict.fromkeys(sedes_filtradas))
sedes_seleccionadas = st.sidebar.multiselect(
    "Selecciona sede(s):",
    options=sedes_filtradas,
    default=sedes_filtradas
)

#ciudades = st.multiselect("Selecciona ciudad(es):", df['Ciudad'].unique(), default=df['Ciudad'].unique())
fechas = st.sidebar.date_input("Selecciona rango de fechas:", [df['Fecha'].min(), df['Fecha'].max()])

# Filtro de tiempo > 2 horas (checkbox)
filtro_2h = st.checkbox("Mostrar solo atenciones con tiempo mayor a **2 horas**")

df_filtros = df[
    (df['Examen'].isin(examen)) &
    (df['Clase'].isin(clase_seleccionada)) &
    (df['Ciudad'].isin(ciudades_seleccionadas)) &
    (df['Sede'].isin(sedes_seleccionadas)) &
    (df['Fecha'] >= pd.to_datetime(fechas[0])) &
    (df['Fecha'] <= pd.to_datetime(fechas[1]))
]

#Filtro de tiempo si está activado
if filtro_2h:
    df_filtros = df_filtros[df_filtros['TiempoAtencionHoras'] > 2.0]

if len(df_filtros)!=0:
    # KPIs
    tiempo_prom = df_filtros['TiempoAtencionMin'].mean()
    cumplimiento = (df_filtros['CumpleTiempo']).mean() * 100
    total_atenciones = len(df_filtros)
    ciudad_top = df_filtros.groupby('Ciudad')['TiempoAtencionMin'].mean().idxmin()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("⏱️ Tiempo promedio", f"{int(tiempo_prom//60)}h {int(tiempo_prom%60)}m")
    col2.metric("📉 % Cumplimiento tiempo (<2h)", f"{cumplimiento:.1f}%")
    col3.metric("🧑‍✈️ Total pacientes", total_atenciones)
    col4.metric("🏆 Ciudad destacada", ciudad_top)

    # Gráficos
    # Gráfico 1
    st.markdown("### 📈 Distribución tiempo de atención pacientes Avianca")
    # Escoger un tono de la paleta "Blues"
    blue_tone = sns.color_palette("Blues")[5] # Índice de 0 (más claro) a 9 (más oscuro)
    # Datos del histograma
    data = df_filtros["TiempoAtencionHoras"]
    data = data.dropna() 
    hist_y, hist_x = np.histogram(data, bins=20)
    
    if len(data)>1:
        # KDE (densidad)
        kde = gaussian_kde(data)
        x_kde = np.linspace(data.min(), data.max(), 200)
        y_kde = kde(x_kde)
        # Ajustar altura para que esté en la misma escala que el histograma
        scale = max(hist_y) / max(y_kde)
        y_kde_scaled = y_kde * scale

        hist_x_bins = (hist_x[:-1] + hist_x[1:]) / 2
        hist_x_bins_min = hist_x_bins*60
        etiquetas_atenciones = [f"{int(val// 60)}h {int(val % 60)}m" for val in (hist_x_bins_min)]


        # Crear figura
        fig = go.Figure()

        # Histograma
        fig.add_trace(go.Bar(
            x=hist_x_bins,  # centro de los bins
            y=hist_y,
            width=(hist_x[1] - hist_x[0]) * 0.8,  # ajustar ancho de barras
            name="Atenciones",
            text = etiquetas_atenciones,
            textposition='outside'
        ))

        #Distribución
        fig.add_trace(go.Scatter(
            x=x_kde,
            y=y_kde_scaled,
            mode='lines',
            line=dict(color=azul_claro_2, width=2),
            name='Distribución'
        ))

        # Línea de referencia (2 horas)
        fig.add_trace(go.Scatter(
            x=[2, 2],
            y=[0, max(hist_y)*1.1],
            mode="lines",
            line=dict(color=naranja_col, dash="dash"),
            name="Promesa Atención (2h)"
        ))

        fig.update_traces(marker_color=azul_oscuro, marker_line_color=azul_oscuro,
                        marker_line_width=1.5)

        # Layout
        fig.update_layout(
            height=250,
            margin=dict(t=40, l=50, r=30, b=50),
            xaxis_title="Tiempo de atención (hr)",
            yaxis_title="Atenciones",
            bargap=0.1,
            showlegend=True,
            template="simple_white"
        )

        # Mostrar en Streamlit
        st.plotly_chart(fig, use_container_width=True)
    else:
        hist_x_bins = (hist_x[:-1] + hist_x[1:]) / 2
        hist_x_bins_min = hist_x_bins*60
        etiquetas_atenciones = [f"{int(val// 60)}h {int(val % 60)}m" for val in (hist_x_bins_min)]


        # Crear figura
        fig = go.Figure()

        # Histograma
        fig.add_trace(go.Bar(
            x=hist_x_bins,  # centro de los bins
            y=hist_y,
            width=(hist_x[1] - hist_x[0]) * 0.8,  # ajustar ancho de barras
            name="Atenciones",
            text = etiquetas_atenciones,
            textposition='outside'
        ))

        # Línea de referencia (2 horas)
        fig.add_trace(go.Scatter(
            x=[2, 2],
            y=[0, max(hist_y)*1.1],
            mode="lines",
            line=dict(color=naranja_col, dash="dash"),
            name="Promesa Atención (2h)"
        ))

        fig.update_traces(marker_color=azul_oscuro, marker_line_color=azul_oscuro,
                        marker_line_width=1.5)

        # Layout
        fig.update_layout(
            height=250,
            margin=dict(t=40, l=50, r=30, b=50),
            xaxis_title="Tiempo de atención (hr)",
            yaxis_title="Atenciones",
            bargap=0.1,
            showlegend=True,
            template="simple_white"
        )

        # Mostrar en Streamlit
        st.plotly_chart(fig, use_container_width=True)


    st.markdown("---")
    col1, col2 = st.columns(2)
    #Gráfico 2
    with col1:
        st.markdown("### 📊 Tiempo promedio por ciudad")
        # Agrupar y ordenar los datos
        ciudad_data = df_filtros.groupby("Ciudad")["TiempoAtencionMin"].mean().sort_values()
        ciudades = ciudad_data.index.tolist()
        tiempos = ciudad_data.values

        # Crear etiquetas para cada barra (ej. "1h 15m")
        etiquetas = [f"{int(val // 60)}h {int(val % 60)}m" for val in tiempos]

        # Crear figura
        fig2 = go.Figure()

        fig2.add_trace(go.Bar(
            x=ciudades,
            y=tiempos,
            text=etiquetas,
            textposition='outside',
            name="Tiempo Promedio"
        ))

        fig2.update_traces(marker_color=azul_oscuro, marker_line_color=azul_oscuro,
                        marker_line_width=1.5)

        # Línea de referencia a las 2h (120 minutos)
        fig2.add_hline(y=120, line_dash="dash", line_color=naranja_col,
                    annotation_text="Promesa Atención (2h)",
                    annotation_position="top left")

        # Personalizar eje Y con formato h/m
        max_val = int(ciudad_data.max()) + 60
        ticks = list(range(0, max_val, 30))
        tick_labels = [f"{t // 60}h" if t % 60 == 0 else f"{t // 60}h {t % 60}m" for t in ticks]

        fig2.update_layout(
            yaxis=dict(
                tickmode='array',
                tickvals=ticks,
                ticktext=tick_labels,
                title="Tiempo de atención promedio"
            ),
            xaxis=dict(
                title="Ciudad"
            ),
            showlegend=False,
            height=500,
            margin=dict(t=50, l=50, r=50, b=100)
        )

        st.plotly_chart(fig2, use_container_width=True)


    #Gráfico 3
    # 📊 Tiempo de Atención por Examen
    with col2:
        st.markdown("### 📊 Tiempo promedio por examen")

        # Agrupar y ordenar los datos
        examen_data = df_filtros.groupby("Examen")["TiempoAtencionMin"].mean().sort_values()
        examenes = examen_data.index.tolist()
        tiempos_examen = examen_data.values

        # Etiquetas de tiempo sobre las barras
        etiquetas_examen = [f"{int(val // 60)}h {int(val % 60)}m" for val in tiempos_examen]

        # Crear figura
        fig3 = go.Figure()

        fig3.add_trace(go.Bar(
            x=examenes,
            y=tiempos_examen,
            text=etiquetas_examen,
            textposition='outside',
            name="Tiempo Promedio"
        ))

        # Estilo de barras
        fig3.update_traces(marker_color=azul_oscuro, marker_line_color=azul_oscuro,
                        marker_line_width=1.5)

        # Línea de referencia a 2 horas
        fig3.add_hline(
            y=120,
            line_dash="dash",
            line_color=naranja_col,
            annotation_text="Promesa Atención (2h)",
            annotation_position="top left"
        )

        # Personalizar eje Y
        max_val_examen = int(examen_data.max()) + 60
        ticks_examen = list(range(0, max_val_examen, 30))
        tick_labels_examen = [f"{t // 60}h" if t % 60 == 0 else f"{t // 60}h {t % 60}m" for t in ticks_examen]

        fig3.update_layout(
            yaxis=dict(
                tickmode='array',
                tickvals=ticks_examen,
                ticktext=tick_labels_examen,
                title="Tiempo de atención promedio"
            ),
            xaxis=dict(
                title="Examen"
            ),
            showlegend=False,
            height=500,
            margin=dict(t=50, l=50, r=50, b=100)  # Ajuste por nombres largos
        )

        st.plotly_chart(fig3, use_container_width=True)

    # Descargar tabla
    st.markdown("### 📥 Descargar datos filtrados")
    def convertir_csv(df):
        output = BytesIO()
        df.to_csv(output, index=False)
        return output.getvalue()

    st.download_button("Descargar CSV", data=convertir_csv(df_filtros), file_name="tiempos_filtrados.csv", mime="text/csv")

else:
    st.write("No hay atenciones disponibles para los filtros seleccionados.")
