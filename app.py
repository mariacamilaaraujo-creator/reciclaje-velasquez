import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import numpy as np

st.set_page_config(page_title="Reciclaje Velásquez", page_icon="♻️", layout="wide")

st.title("♻️ RECICLAJE VELÁSQUEZ")
st.markdown("### Sistema de Gestión de Inventario con Clasificación ABC **DUAL**")
st.markdown("📊 **Clasificación por VALOR** | ⚡ **Clasificación por VELOCIDAD de rotación**")

# ============================================
# CONEXIÓN A GOOGLE SHEETS
# ============================================

def conectar_google_sheets():
    """Conecta con Google Sheets usando las credenciales de Streamlit secrets"""
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet_url = st.secrets["google_sheets"]["spreadsheet_url"]
        sheet = client.open_by_url(sheet_url)
        return sheet
    except Exception as e:
        st.error(f"Error de conexión a Google Sheets: {e}")
        return None

def cargar_inventario():
    """Carga el inventario desde Google Sheets"""
    try:
        sheet = conectar_google_sheets()
        if sheet:
            worksheet = sheet.worksheet("inventario")
            datos = worksheet.get_all_records()
            if datos:
                return pd.DataFrame(datos)
            else:
                return pd.DataFrame(columns=["id", "tipo_residuo", "cantidad", "precio_compra", "precio_venta", "proveedor", "fecha_ingreso"])
        return pd.DataFrame(columns=["id", "tipo_residuo", "cantidad", "precio_compra", "precio_venta", "proveedor", "fecha_ingreso"])
    except Exception as e:
        st.warning(f"No se pudo cargar inventario: {e}")
        return pd.DataFrame(columns=["id", "tipo_residuo", "cantidad", "precio_compra", "precio_venta", "proveedor", "fecha_ingreso"])

def guardar_inventario(df):
    """Guarda el inventario en Google Sheets"""
    try:
        sheet = conectar_google_sheets()
        if sheet:
            worksheet = sheet.worksheet("inventario")
            worksheet.clear()
            if not df.empty:
                worksheet.update([df.columns.values.tolist()] + df.values.tolist())
            return True
    except Exception as e:
        st.error(f"Error al guardar inventario: {e}")
        return False

def cargar_historial():
    """Carga el historial desde Google Sheets"""
    try:
        sheet = conectar_google_sheets()
        if sheet:
            worksheet = sheet.worksheet("historial")
            datos = worksheet.get_all_records()
            if datos:
                return pd.DataFrame(datos)
            else:
                return pd.DataFrame(columns=["fecha", "tipo_movimiento", "id_residuo", "tipo_residuo", "cantidad", "precio_unitario", "valor_total", "proveedor_cliente"])
        return pd.DataFrame(columns=["fecha", "tipo_movimiento", "id_residuo", "tipo_residuo", "cantidad", "precio_unitario", "valor_total", "proveedor_cliente"])
    except Exception as e:
        st.warning(f"No se pudo cargar historial: {e}")
        return pd.DataFrame(columns=["fecha", "tipo_movimiento", "id_residuo", "tipo_residuo", "cantidad", "precio_unitario", "valor_total", "proveedor_cliente"])

def guardar_historial(df):
    """Guarda el historial en Google Sheets"""
    try:
        sheet = conectar_google_sheets()
        if sheet:
            worksheet = sheet.worksheet("historial")
            worksheet.clear()
            if not df.empty:
                worksheet.update([df.columns.values.tolist()] + df.values.tolist())
            return True
    except Exception as e:
        st.error(f"Error al guardar historial: {e}")
        return False

# ============================================
# FUNCIONES PRINCIPALES
# ============================================

def agregar_residuo(tipo, cantidad, precio_compra, precio_venta, proveedor):
    if not tipo or cantidad <= 0:
        return "❌ Complete todos los campos correctamente"
    
    df = cargar_inventario()
    nuevo_id = df["id"].max() + 1 if not df.empty else 1
    
    nueva_fila = pd.DataFrame([{
        "id": nuevo_id,
        "tipo_residuo": tipo,
        "cantidad": float(cantidad),
        "precio_compra": float(precio_compra),
        "precio_venta": float(precio_venta),
        "proveedor": proveedor,
        "fecha_ingreso": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }])
    
    df = pd.concat([df, nueva_fila], ignore_index=True)
    guardar_inventario(df)
    
    df_hist = cargar_historial()
    nuevo_hist = pd.DataFrame([{
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tipo_movimiento": "COMPRA",
        "id_residuo": nuevo_id,
        "tipo_residuo": tipo,
        "cantidad": float(cantidad),
        "precio_unitario": float(precio_compra),
        "valor_total": float(cantidad) * float(precio_compra),
        "proveedor_cliente": proveedor
    }])
    df_hist = pd.concat([df_hist, nuevo_hist], ignore_index=True)
    guardar_historial(df_hist)
    
    return f"✅ Residuo '{tipo}' agregado (ID: {nuevo_id})"

def vender_residuo(id_residuo, cantidad_vendida):
    df = cargar_inventario()
    
    if id_residuo not in df["id"].values:
        return f"❌ ID {id_residuo} no encontrado"
    
    idx = df[df["id"] == id_residuo].index[0]
    disponible = df.loc[idx, "cantidad"]
    precio_venta = df.loc[idx, "precio_venta"]
    tipo = df.loc[idx, "tipo_residuo"]
    fecha_ingreso = df.loc[idx, "fecha_ingreso"]
    
    if cantidad_vendida > disponible:
        return f"❌ Stock insuficiente. Disponible: {disponible}"
    
    nueva_cantidad = disponible - cantidad_vendida
    valor_venta = cantidad_vendida * precio_venta
    
    # Calcular días desde ingreso hasta venta (para velocidad)
    fecha_ingreso_dt = datetime.strptime(fecha_ingreso, "%Y-%m-%d %H:%M:%S")
    dias_rotacion = (datetime.now() - fecha_ingreso_dt).days
    dias_rotacion = max(dias_rotacion, 1)
    
    if nueva_cantidad == 0:
        df = df.drop(idx)
        mensaje = f"✅ Venta: {cantidad_vendida} {tipo} | Stock agotado | Días en inventario: {dias_rotacion}"
    else:
        df.loc[idx, "cantidad"] = nueva_cantidad
        mensaje = f"✅ Venta: {cantidad_vendida} {tipo} | Restante: {nueva_cantidad} | Días en inventario: {dias_rotacion}"
    
    guardar_inventario(df.reset_index(drop=True))
    
    df_hist = cargar_historial()
    nuevo_hist = pd.DataFrame([{
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tipo_movimiento": "VENTA",
        "id_residuo": id_residuo,
        "tipo_residuo": tipo,
        "cantidad": cantidad_vendida,
        "precio_unitario": precio_venta,
        "valor_total": valor_venta,
        "proveedor_cliente": "Cliente",
        "dias_rotacion": dias_rotacion
    }])
    df_hist = pd.concat([df_hist, nuevo_hist], ignore_index=True)
    guardar_historial(df_hist)
    
    return mensaje

# ============================================
# CLASIFICACIÓN 1: POR VALOR
# ============================================

def clasificar_abc_valor():
    """Clasificación ABC por VALOR de rotación (cantidad × precio)"""
    df = cargar_inventario()
    if df.empty:
        return pd.DataFrame()
    
    df["valor_rotacion"] = df["cantidad"] * df["precio_venta"]
    df_ordenado = df.sort_values("valor_rotacion", ascending=False).reset_index(drop=True)
    total = df_ordenado["valor_rotacion"].sum()
    
    if total == 0:
        return pd.DataFrame()
    
    df_ordenado["porcentaje_individual"] = (df_ordenado["valor_rotacion"] / total * 100)
    df_ordenado["porcentaje_acumulado"] = (df_ordenado["valor_rotacion"].cumsum() / total * 100)
    
    def asignar_abc_valor(porc):
        if porc <= 80:
            return "A - Alto valor (80%)"
        elif porc <= 95:
            return "B - Medio valor (15%)"
        else:
            return "C - Bajo valor (5%)"
    
    df_ordenado["clasificacion_valor"] = df_ordenado["porcentaje_acumulado"].apply(asignar_abc_valor)
    return df_ordenado

# ============================================
# CLASIFICACIÓN 2: POR VELOCIDAD (días que tarda en salir)
# ============================================

def calcular_velocidad_rotacion():
    """
    Calcula la velocidad de rotación basada en días que tarda en venderse.
    Mide qué tan RÁPIDO o LENTO se vende un residuo.
    
    Fórmula: Velocidad = Cantidad vendida / Días en inventario
    Menor velocidad = más lento (demora en salir)
    Mayor velocidad = más rápido (sale rápidamente)
    """
    df_hist = cargar_historial()
    if df_hist.empty:
        return pd.DataFrame()
    
    # Filtrar solo ventas que tienen días de rotación
    ventas = df_hist[df_hist["tipo_movimiento"] == "VENTA"].copy()
    if ventas.empty:
        return pd.DataFrame()
    
    # Si no existe la columna dias_rotacion, calcularla
    if "dias_rotacion" not in ventas.columns:
        ventas["dias_rotacion"] = 1
    
    # Agrupar por residuo
    velocidad = ventas.groupby(["id_residuo", "tipo_residuo"]).agg({
        "cantidad": "sum",
        "dias_rotacion": "mean",  # Promedio de días que tarda en salir
        "fecha": "count"  # Número de ventas
    }).reset_index()
    
    velocidad.columns = ["id", "tipo_residuo", "cantidad_total_vendida", "dias_promedio_rotacion", "num_ventas"]
    
    # Calcular velocidad = cantidad / días (a mayor velocidad, más rápido)
    velocidad["velocidad_rotacion"] = velocidad["cantidad_total_vendida"] / velocidad["dias_promedio_rotacion"]
    
    # Clasificación: los de MAYOR velocidad son los MÁS RÁPIDOS (A)
    # los de MENOR velocidad son los MÁS LENTOS (C)
    velocidad_ordenado = velocidad.sort_values("velocidad_rotacion", ascending=False).reset_index(drop=True)
    
    total_velocidad = velocidad_ordenado["velocidad_rotacion"].sum()
    if total_velocidad == 0:
        return pd.DataFrame()
    
    velocidad_ordenado["porcentaje_velocidad"] = (velocidad_ordenado["velocidad_rotacion"] / total_velocidad * 100)
    velocidad_ordenado["porcentaje_acumulado_velocidad"] = velocidad_ordenado["porcentaje_velocidad"].cumsum()
    
    def asignar_abc_velocidad(porc):
        if porc <= 80:
            return "A - Rápida (sale rápido +80%)"
        elif porc <= 95:
            return "B - Media (rotación media 15%)"
        else:
            return "C - Lenta (demora en salir 5%)"
    
    velocidad_ordenado["clasificacion_velocidad"] = velocidad_ordenado["porcentaje_acumulado_velocidad"].apply(asignar_abc_velocidad)
    
    return velocidad_ordenado

def analisis_tiempo_salida():
    """Analiza el tiempo promedio que tarda cada residuo en salir del almacén"""
    df_hist = cargar_historial()
    if df_hist.empty:
        return pd.DataFrame()
    
    ventas = df_hist[df_hist["tipo_movimiento"] == "VENTA"].copy()
    if ventas.empty:
        return pd.DataFrame()
    
    if "dias_rotacion" not in ventas.columns:
        ventas["dias_rotacion"] = 1
    
    # Agrupar por residuo
    tiempo = ventas.groupby(["id_residuo", "tipo_residuo"]).agg({
        "dias_rotacion": "mean",
        "cantidad": "sum"
    }).reset_index()
    
    tiempo.columns = ["id", "tipo_residuo", "dias_promedio", "cantidad_vendida"]
    tiempo = tiempo.sort_values("dias_promedio", ascending=False)
    
    # Clasificación por tiempo de salida
    def clasificar_tiempo(dias):
        if dias <= 7:
            return "🚀 Muy rápido (≤ 7 días)"
        elif dias <= 30:
            return "📦 Rápido (8-30 días)"
        elif dias <= 90:
            return "⏳ Normal (31-90 días)"
        else:
            return "🐢 Lento (> 90 días)"
    
    tiempo["clasificacion_tiempo"] = tiempo["dias_promedio"].apply(clasificar_tiempo)
    return tiempo

# ============================================
# INTERFAZ DE USUARIO
# ============================================

with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/recycle-sign.png", width=80)
    st.markdown("## 📊 Método ABC **DUAL**")
    st.markdown("---")
    st.markdown("### 1️⃣ Por VALOR")
    st.markdown("💰 Cantidad × Precio venta")
    st.markdown("**A**: Alto valor (80%)")
    st.markdown("**B**: Medio valor (15%)")
    st.markdown("**C**: Bajo valor (5%)")
    st.markdown("---")
    st.markdown("### 2️⃣ Por VELOCIDAD ⚡")
    st.markdown("📦 Qué tan RÁPIDO se vende")
    st.markdown("**A**: Rápida rotación (sale rápido)")
    st.markdown("**B**: Rotación media")
    st.markdown("**C**: Lenta rotación (demora en salir)")
    st.markdown("---")
    st.caption("💾 Datos permanentes en Google Sheets")

# Tabs principales
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📦 Gestión", 
    "💰 Clasificación por VALOR", 
    "⚡ Clasificación por VELOCIDAD",
    "📊 Tiempo de Salida",
    "📈 Gráficos", 
    "📜 Historial"
])

# ========== TAB 1: GESTIÓN ==========
with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("➕ Ingresar Residuo")
        with st.form("ingresar_form"):
            tipo = st.text_input("Tipo de residuo", placeholder="Ej: PET, Cartón, Aluminio")
            cantidad = st.number_input("Cantidad (kg/unidades)", min_value=0.0, step=1.0)
            precio_compra = st.number_input("Precio compra ($)", min_value=0.0, step=0.1)
            precio_venta = st.number_input("Precio venta ($)", min_value=0.0, step=0.1)
            proveedor = st.text_input("Proveedor")
            if st.form_submit_button("Agregar", type="primary"):
                if tipo and cantidad > 0:
                    resultado = agregar_residuo(tipo, cantidad, precio_compra, precio_venta, proveedor)
                    st.success(resultado)
                    st.rerun()
                else:
                    st.error("Complete todos los campos")
    
    with col2:
        st.subheader("💸 Registrar Venta")
        with st.form("vender_form"):
            id_venta = st.number_input("ID del residuo", min_value=0, step=1)
            cantidad_vender = st.number_input("Cantidad a vender", min_value=0.0, step=1.0)
            if st.form_submit_button("Vender", type="primary"):
                if id_venta > 0 and cantidad_vender > 0:
                    resultado = vender_residuo(id_venta, cantidad_vender)
                    st.success(resultado)
                    st.rerun()
                else:
                    st.error("Complete todos los campos")
    
    st.subheader("📋 Inventario Actual")
    inventario = cargar_inventario()
    if not inventario.empty:
        inventario_mostrar = inventario.copy()
        inventario_mostrar["precio_compra"] = inventario_mostrar["precio_compra"].apply(lambda x: f"${x:,.2f}")
        inventario_mostrar["precio_venta"] = inventario_mostrar["precio_venta"].apply(lambda x: f"${x:,.2f}")
        st.dataframe(inventario_mostrar, use_container_width=True)
        st.caption(f"📊 Total de items en inventario: **{len(inventario)}**")
    else:
        st.info("📭 No hay residuos registrados")

# ========== TAB 2: CLASIFICACIÓN POR VALOR ==========
with tab2:
    st.subheader("💰 Clasificación ABC por VALOR de Rotación")
    st.markdown("**Fórmula:** Valor de rotación = Cantidad disponible × Precio de venta")
    
    if st.button("🔄 Actualizar clasificación por VALOR", key="btn_valor"):
        df_valor = clasificar_abc_valor()
        if not df_valor.empty:
            df_mostrar = df_valor.copy()
            df_mostrar["precio_venta"] = df_mostrar["precio_venta"].apply(lambda x: f"${x:,.2f}")
            df_mostrar["valor_rotacion"] = df_mostrar["valor_rotacion"].apply(lambda x: f"${x:,.2f}")
            df_mostrar["porcentaje_acumulado"] = df_mostrar["porcentaje_acumulado"].apply(lambda x: f"{x:.1f}%")
            st.dataframe(df_mostrar[["id", "tipo_residuo", "cantidad", "precio_venta", "valor_rotacion", "porcentaje_acumulado", "clasificacion_valor"]], use_container_width=True)
            
            # Gráfico de barras por categoría
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Distribución por Categoría")
                resumen = df_valor.groupby("clasificacion_valor").agg({"id": "count", "valor_rotacion": "sum"})
                resumen.columns = ["Cantidad Items", "Valor Total"]
                resumen["Valor Total"] = resumen["Valor Total"].apply(lambda x: f"${x:,.2f}")
                st.dataframe(resumen)
        else:
            st.warning("⚠️ No hay datos suficientes")

# ========== TAB 3: CLASIFICACIÓN POR VELOCIDAD (NUEVA) ==========
with tab3:
    st.subheader("⚡ Clasificación ABC por VELOCIDAD de Rotación")
    st.markdown("""
    **¿Qué mide?** Qué tan RÁPIDO o LENTO se vende un residuo.
    - **Fórmula:** Velocidad = Cantidad vendida ÷ Días en inventario
    - **Mayor velocidad** = Sale rápido (Categoría A)
    - **Menor velocidad** = Demora en salir (Categoría C)
    """)
    
    if st.button("🔄 Actualizar clasificación por VELOCIDAD", key="btn_velocidad"):
        df_velocidad = calcular_velocidad_rotacion()
        if not df_velocidad.empty:
            df_mostrar = df_velocidad.copy()
            df_mostrar["velocidad_rotacion"] = df_mostrar["velocidad_rotacion"].apply(lambda x: f"{x:.2f} kg/día")
            df_mostrar["dias_promedio_rotacion"] = df_mostrar["dias_promedio_rotacion"].apply(lambda x: f"{x:.1f} días")
            st.dataframe(df_mostrar[["id", "tipo_residuo", "cantidad_total_vendida", "dias_promedio_rotacion", "velocidad_rotacion", "clasificacion_velocidad"]], use_container_width=True)
            
            # Resumen por categoría
            st.subheader("📊 Resumen por Categoría de Velocidad")
            resumen = df_velocidad.groupby("clasificacion_velocidad").agg({
                "id": "count",
                "velocidad_rotacion": "mean",
                "dias_promedio_rotacion": "mean"
            })
            resumen.columns = ["Cantidad Items", "Velocidad Promedio (kg/día)", "Días Promedio"]
            resumen["Velocidad Promedio (kg/día)"] = resumen["Velocidad Promedio (kg/día)"].apply(lambda x: f"{x:.2f}")
            resumen["Días Promedio"] = resumen["Días Promedio"].apply(lambda x: f"{x:.1f}")
            st.dataframe(resumen)
        else:
            st.warning("⚠️ No hay suficientes ventas registradas para calcular velocidad")

# ========== TAB 4: TIEMPO DE SALIDA ==========
with tab4:
    st.subheader("📊 Análisis de Tiempo de Salida del Almacén")
    st.markdown("**¿Qué mide?** Cuántos días tarda cada residuo en venderse desde que entra.")
    
    if st.button("🔄 Analizar tiempos de salida", key="btn_tiempo"):
        df_tiempo = analisis_tiempo_salida()
        if not df_tiempo.empty:
            df_mostrar = df_tiempo.copy()
            df_mostrar["dias_promedio"] = df_mostrar["dias_promedio"].apply(lambda x: f"{x:.1f} días")
            st.dataframe(df_mostrar, use_container_width=True)
            
            # Tabla resumen por tipo de velocidad
            st.subheader("📊 Resumen por Tipo de Rotación")
            resumen_tiempo = df_tiempo.groupby("clasificacion_tiempo").agg({
                "id": "count",
                "dias_promedio": "mean"
            })
            resumen_tiempo.columns = ["Cantidad Items", "Días Promedio"]
            resumen_tiempo["Días Promedio"] = resumen_tiempo["Días Promedio"].apply(lambda x: f"{x:.1f}")
            st.dataframe(resumen_tiempo)
            
            # Explicación
            st.info("""
            **Interpretación:**
            - 🚀 **Muy rápido (≤ 7 días)**: Rotación excelente, mantener stock
            - 📦 **Rápido (8-30 días)**: Buena rotación
            - ⏳ **Normal (31-90 días)**: Rotación aceptable
            - 🐢 **Lento (> 90 días)**: Revisar precio o demanda
            """)
        else:
            st.warning("⚠️ No hay suficientes ventas registradas para analizar tiempos")

# ========== TAB 5: GRÁFICOS ==========
with tab5:
    st.subheader("📊 Gráficos Comparativos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Pareto - Clasificación por VALOR")
        if st.button("Generar gráfico de VALOR", key="btn_graf_valor"):
            df_valor = clasificar_abc_valor()
            if not df_valor.empty:
                fig, ax = plt.subplots(figsize=(10, 5))
                colors = ['#ff4444' if 'A' in c else '#ffaa44' if 'B' in c else '#44ff44' for c in df_valor['clasificacion_valor']]
                ax.bar(range(len(df_valor)), df_valor['valor_rotacion'], color=colors, alpha=0.7)
                ax.set_xlabel('Residuos')
                ax.set_ylabel('Valor de rotación ($)')
                ax.set_title('Pareto - Valor de Rotación')
                ax.set_xticks(range(len(df_valor)))
                ax.set_xticklabels(df_valor['tipo_residuo'], rotation=45, ha='right')
                st.pyplot(fig)
            else:
                st.warning("No hay datos")
    
    with col2:
        st.markdown("### ⚡ Pareto - Clasificación por VELOCIDAD")
        if st.button("Generar gráfico de VELOCIDAD", key="btn_graf_vel"):
            df_vel = calcular_velocidad_rotacion()
            if not df_vel.empty:
                fig, ax = plt.subplots(figsize=(10, 5))
                colors = ['#ff4444' if 'Rápida' in c else '#ffaa44' if 'Media' in c else '#44ff44' for c in df_vel['clasificacion_velocidad']]
                ax.bar(range(len(df_vel)), df_vel['velocidad_rotacion'], color=colors, alpha=0.7)
                ax.set_xlabel('Residuos')
                ax.set_ylabel('Velocidad (kg/día)')
                ax.set_title('Pareto - Velocidad de Rotación')
                ax.set_xticks(range(len(df_vel)))
                ax.set_xticklabels(df_vel['tipo_residuo'], rotation=45, ha='right')
                st.pyplot(fig)
                st.caption("Mayor velocidad = Sale más rápido | Menor velocidad = Demora en salir")
            else:
                st.warning("No hay suficientes ventas")

# ========== TAB 6: HISTORIAL ==========
with tab6:
    st.subheader("📜 Historial Completo")
    historial = cargar_historial()
    if not historial.empty:
        historial_mostrar = historial.copy()
        historial_mostrar["precio_unitario"] = historial_mostrar["precio_unitario"].apply(lambda x: f"${x:,.2f}")
        historial_mostrar["valor_total"] = historial_mostrar["valor_total"].apply(lambda x: f"${x:,.2f}")
        st.dataframe(historial_mostrar.sort_values("fecha", ascending=False), use_container_width=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            compras = len(historial[historial["tipo_movimiento"] == "COMPRA"])
            st.metric("Total Compras", compras)
        with col2:
            ventas = len(historial[historial["tipo_movimiento"] == "VENTA"])
            st.metric("Total Ventas", ventas)
        with col3:
            # Velocidad promedio general
            ventas_df = historial[historial["tipo_movimiento"] == "VENTA"]
            if not ventas_df.empty and "dias_rotacion" in ventas_df.columns:
                dias_prom = ventas_df["dias_rotacion"].mean()
                st.metric("Días promedio para vender", f"{dias_prom:.1f}")
    else:
        st.info("No hay movimientos registrados")

# Footer
st.divider()
st.caption("♻️ **Reciclaje Velásquez** | Clasificación ABC **DUAL**: Por VALOR y por VELOCIDAD de rotación | Datos permanentes")
