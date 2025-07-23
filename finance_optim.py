import streamlit as st
import pandas as pd
import numpy_financial as npf

# --- Funciones de Cálculo (las mismas que en Colab, sin cambios) ---

def generar_cuadro_marcha(monto_prestamo, n_cuotas, tna, gastos_admin_fijos, iva_porcentaje):
    """
    Genera un cuadro de marcha detallado para un préstamo con sistema francés.
    """
    tasa_mensual = tna / 12
    iva = iva_porcentaje

    if tasa_mensual > 0:
        cuota_pura = npf.pmt(tasa_mensual, n_cuotas, -monto_prestamo)
    else:
        cuota_pura = monto_prestamo / n_cuotas if n_cuotas > 0 else 0

    saldo_pendiente = monto_prestamo
    cuadro_data = []
    flujo_caja_cft = [-monto_prestamo]

    for periodo in range(1, n_cuotas + 1):
        interes_mes = saldo_pendiente * tasa_mensual
        amortizacion_capital = cuota_pura - interes_mes
        if periodo == n_cuotas:
            amortizacion_capital = saldo_pendiente
        saldo_final = saldo_pendiente - amortizacion_capital

        iva_sobre_intereses = interes_mes * iva
        iva_sobre_gastos = gastos_admin_fijos * iva
        total_gastos_impuestos = gastos_admin_fijos + iva_sobre_intereses + iva_sobre_gastos
        cuota_total_a_pagar = cuota_pura + total_gastos_impuestos

        cuadro_data.append({
            "N° Cuota": periodo,
            "Saldo Inicial": saldo_pendiente,
            "Cuota Pura": cuota_pura,
            "Interés": interes_mes,
            "Amortización": amortizacion_capital,
            "Gastos Admin.": gastos_admin_fijos,
            "IVA": iva_sobre_intereses + iva_sobre_gastos,
            "Cuota Total": cuota_total_a_pagar,
            "Saldo Final": saldo_final
        })
        flujo_caja_cft.append(cuota_total_a_pagar)
        saldo_pendiente = saldo_final

    cuadro_df = pd.DataFrame(cuadro_data)
    total_intereses = cuadro_df['Interés'].sum()
    total_pagado = cuadro_df['Cuota Total'].sum()
    
    try:
        cft_mensual = npf.irr(flujo_caja_cft)
        cft_anual = ((1 + cft_mensual) ** 12) - 1 if cft_mensual is not None and cft_mensual > -1 else 0
    except ValueError:
        cft_anual = 0

    metricas = {
        "n_cuotas": n_cuotas,
        "cuota_total_promedio": cuadro_df['Cuota Total'].mean(),
        "costo_financiero_total_%": cft_anual * 100
    }
    return cuadro_df, metricas

def optimizar_prestamo(monto_prestamo, tna, gastos_admin_fijos, iva_porcentaje, cuota_maxima_pagar, rango_cuotas):
    """
    Encuentra el número óptimo de cuotas que minimiza el CFT.
    """
    mejor_opcion = {"cft_%": float('inf')}
    resultados_validos = []

    for n in range(rango_cuotas[0], rango_cuotas[1] + 1):
        _, metricas = generar_cuadro_marcha(monto_prestamo, n, tna, gastos_admin_fijos, iva_porcentaje)
        if metricas["cuota_total_promedio"] <= cuota_maxima_pagar:
            opcion_actual = {
                "n_cuotas": n,
                "cft_%": metricas["costo_financiero_total_%"],
                "cuota_total": metricas["cuota_total_promedio"]
            }
            resultados_validos.append(opcion_actual)
            if opcion_actual["cft_%"] < mejor_opcion["cft_%"]:
                mejor_opcion = opcion_actual

    if not resultados_validos:
        return None, None
    
    return mejor_opcion, pd.DataFrame(resultados_validos)

# --- Interfaz de Usuario con Streamlit ---

st.set_page_config(page_title="Optimizador de Préstamos", layout="wide")

st.title("📊 Optimizador de Préstamos con Sistema Francés")
st.markdown("""
Esta aplicación te ayuda a encontrar el plan de pagos óptimo para un préstamo.
El objetivo es **minimizar el Costo Financiero Total (CFT)**, sujeto a una **cuota máxima** que puedas pagar.
La variable de ajuste es la **cantidad de cuotas**.
""")

# --- Panel de Entradas en la Barra Lateral ---
st.sidebar.header("Parámetros de Entrada")

monto_prestamo = st.sidebar.number_input(
    "Monto a Solicitar ($)", 
    min_value=1000, 
    max_value=500000000, 
    value=5000000, 
    step=10000,
    format="%d"
)

tna_pct = st.sidebar.slider(
    "Tasa Nominal Anual (TNA %)",
    min_value=0.0, 
    max_value=200.0, 
    value=85.0, 
    step=0.1
)
tna = tna_pct / 100.0

gastos_admin_fijos = st.sidebar.number_input(
    "Gastos Administrativos Fijos por Cuota ($)", 
    min_value=0, 
    value=15000000, 
    step=100
)

iva_pct = st.sidebar.slider(
    "IVA sobre Intereses y Gastos (%)", 
    min_value=0.0, 
    max_value=50.0, 
    value=21.0, 
    step=0.5
)
iva_porcentaje = iva_pct / 100.0

st.sidebar.markdown("---")
st.sidebar.header("Objetivo y Restricciones")

cuota_maxima_pagar = st.sidebar.number_input(
    "Cuota Máxima que Puedo Pagar ($)", 
    min_value=1000, 
    value=500000, 
    step=1000,
    format="%d"
)

rango_cuotas = st.sidebar.slider(
    "Rango de Cuotas a Evaluar", 
    min_value=1, 
    max_value=120, 
    value=(12, 48)
)

# --- Botón para ejecutar el cálculo ---
if st.button("🚀 Calcular y Optimizar Plan"):
    with st.spinner("Buscando la mejor opción... Por favor, espera."):
        mejor_plan, df_validos = optimizar_prestamo(
            monto_prestamo, tna, gastos_admin_fijos, iva_porcentaje, cuota_maxima_pagar, rango_cuotas
        )

    st.success("¡Análisis completado!")

    if mejor_plan:
        st.header("🏆 Resultado Óptimo Encontrado")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Número de Cuotas", f"{mejor_plan['n_cuotas']} meses")
        col2.metric("Cuota Mensual Total", f"${mejor_plan['cuota_total']:,.2f}")
        col3.metric("Costo Financiero Total (CFT)", f"{mejor_plan['cft_%']:.2f}%")
        
        st.markdown("---")
        
        # Generar y mostrar el cuadro de marcha para la opción óptima
        st.subheader(f"Cuadro de Marcha para el Plan de {mejor_plan['n_cuotas']} Cuotas")
        cuadro_optimo, _ = generar_cuadro_marcha(
            monto_prestamo, mejor_plan['n_cuotas'], tna, gastos_admin_fijos, iva_porcentaje
        )
        st.dataframe(cuadro_optimo.style.format({
            "Saldo Inicial": "${:,.2f}",
            "Cuota Pura": "${:,.2f}",
            "Interés": "${:,.2f}",
            "Amortización": "${:,.2f}",
            "Gastos Admin.": "${:,.2f}",
            "IVA": "${:,.2f}",
            "Cuota Total": "${:,.2f}",
            "Saldo Final": "${:,.2f}",
        }))
        
        st.markdown("---")

        # Mostrar gráfico y tabla de opciones válidas
        st.subheader("Análisis de Opciones Válidas")
        st.write("Las siguientes opciones cumplen con tu cuota máxima. El punto óptimo (menor CFT) está resaltado.")
        
        # Gráfico comparativo
        st.line_chart(df_validos.rename(columns={'n_cuotas':'index'}).set_index('index'))

        st.dataframe(df_validos.style.format({
            "cft_%": "{:.2f}%",
            "cuota_total": "${:,.2f}"
        }).highlight_min(subset=['cft_%'], color='lightgreen'))

    else:
        st.error(
            f"**No se encontró ninguna solución.**\n\n"
            f"Bajo las condiciones dadas, no es posible obtener un préstamo de ${monto_prestamo:,.2f} "
            f"con una cuota mensual menor a ${cuota_maxima_pagar:,.2f} en el rango de {rango_cuotas[0]} a {rango_cuotas[1]} cuotas. "
            f"Prueba a aumentar la cuota máxima que puedes pagar o el monto del préstamo."
        )
