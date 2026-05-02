import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import io
import base64
from fpdf import FPDF
import time

st.set_page_config(page_title="Reciclaje Velásquez", page_icon="♻️", layout="wide")

st.title("♻️ RECICLAJE VELÁSQUEZ")
st.markdown("### Sistema de Gestión de Inventario con Clasificación ABC DUAL")
st.info("📦 **Modo de acumulación activado:** Los residuos del mismo tipo se suman automáticamente")

# ============================================
# INICIALIZACIÓN DE VARIABLES DE SESIÓN
# ============================================
if 'umbral_stock' not in st.session_state:
    st.session_state.umbral_stock = 50.0  # umbral por defecto (kg)
if 'filtro_busqueda' not in st.session_state:
    st.session_state.filtro_busqueda = ""

# ============================================
# BARRA LATERAL CON INFORMACIÓN DEL MÉTODO ABC
# ============================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/recycle-sign.png", width=80)
    st.markdown("## 📊 Método ABC **DUAL**")
    st.markdown("---")
    
    # Explicación del método ABC por VALOR (actual)
    st.markdown("### 1️⃣ Clasificación por **VALOR (Stock Actual)**")
    st.markdown("**Fórmula:** `Valor = Cantidad disponible × Precio de venta`")
    st.markdown("**Interpretación:** Importancia económica actual.")
    st.markdown("---")
    
    # Explicación del nuevo método ABC por VALOR HISTÓRICO
    st.markdown("### 1️⃣ Clasificación por **VALOR HISTÓRICO (Ventas)**")
    st.markdown("**Fórmula:** `Valor histórico = Suma de todas las ventas (cantidad × precio venta)`")
    st.markdown("**Interpretación:** Mide qué productos han generado más ingresos totales.")
    st.markdown("---")
    
    # Explicación del método ABC por VELOCIDAD
    st.markdown("### 2️⃣ Clasificación por **VELOCIDAD**")
    st.markdown("**Fórmula:** `Velocidad = Cantidad vendida / Días en inventario`")
    st.markdown("---")
    
    # Explicación del análisis de tiempo de salida
    st.markdown("### ⏱️ Tiempo de Salida")
    st.markdown("**Clasificación por días promedio para venderse:** (≤7 días: rápido, >90: lento)")
    st.markdown("---")
    st.caption("💾 Datos guardados permanentemente en Google Sheets")
    st.caption("♻️ Reciclaje Velásquez")

# ============================================
# CONEXIÓN A GOOGLE SHEETS CON CACHÉ Y REINTENTOS
# ============================================

def conectar_google_sheets():
    """Conecta con Google Sheets usando credenciales de secrets."""
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet_url = st.secrets["google_sheets"]["spreadsheet_url"]
        sheet = client.open_by_url(sheet_url)
        return sheet
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        return None

# Aplicamos caché a las funciones de carga para reducir llamadas a la API
@st.cache_data(ttl=30, show_spinner=False)
def cargar_inventario_cache():
    """Carga inventario con caché de 30 segundos."""
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
        # Si es error de cuota (429), esperamos y reintentamos una vez
        if "429" in str(e):
            time.sleep(5)
            try:
                sheet = conectar_google_sheets()
                if sheet:
                    worksheet = sheet.worksheet("inventario")
                    datos = worksheet.get_all_records()
                    if datos:
                        return pd.DataFrame(datos)
                    else:
                        return pd.DataFrame(columns=["id", "tipo_residuo", "cantidad", "precio_compra", "precio_venta", "proveedor", "fecha_ingreso"])
            except:
                st.warning("⚠️ Límite de cuota excedido. Inténtalo de nuevo en unos segundos.")
                return pd.DataFrame(columns=["id", "tipo_residuo", "cantidad", "precio_compra", "precio_venta", "proveedor", "fecha_ingreso"])
        else:
            st.warning(f"⚠️ No se pudo cargar inventario: {e}")
            return pd.DataFrame(columns=["id", "tipo_residuo", "cantidad", "precio_compra", "precio_venta", "proveedor", "fecha_ingreso"])

@st.cache_data(ttl=30, show_spinner=False)
def cargar_historial_cache():
    """Carga historial con caché de 30 segundos."""
    try:
        sheet = conectar_google_sheets()
        if sheet:
            worksheet = sheet.worksheet("historial")
            datos = worksheet.get_all_records()
            if datos:
                return pd.DataFrame(datos)
            else:
                return pd.DataFrame(columns=["fecha", "tipo_movimiento", "id_residuo", "tipo_residuo", "cantidad", "precio_unitario", "valor_total", "proveedor_cliente", "dias_rotacion"])
        return pd.DataFrame(columns=["fecha", "tipo_movimiento", "id_residuo", "tipo_residuo", "cantidad", "precio_unitario", "valor_total", "proveedor_cliente", "dias_rotacion"])
    except Exception as e:
        if "429" in str(e):
            time.sleep(5)
            try:
                sheet = conectar_google_sheets()
                if sheet:
                    worksheet = sheet.worksheet("historial")
                    datos = worksheet.get_all_records()
                    if datos:
                        return pd.DataFrame(datos)
                    else:
                        return pd.DataFrame(columns=["fecha", "tipo_movimiento", "id_residuo", "tipo_residuo", "cantidad", "precio_unitario", "valor_total", "proveedor_cliente", "dias_rotacion"])
            except:
                st.warning("⚠️ Límite de cuota excedido. Inténtalo de nuevo en unos segundos.")
                return pd.DataFrame(columns=["fecha", "tipo_movimiento", "id_residuo", "tipo_residuo", "cantidad", "precio_unitario", "valor_total", "proveedor_cliente", "dias_rotacion"])
        else:
            st.warning(f"⚠️ No se pudo cargar historial: {e}")
            return pd.DataFrame(columns=["fecha", "tipo_movimiento", "id_residuo", "tipo_residuo", "cantidad", "precio_unitario", "valor_total", "proveedor_cliente", "dias_rotacion"])

# Funciones sin caché para escritura (guardar) – no se cachean
def guardar_inventario(df):
    try:
        sheet = conectar_google_sheets()
        if sheet:
            worksheet = sheet.worksheet("inventario")
            worksheet.clear()
            if not df.empty:
                worksheet.update([df.columns.values.tolist()] + df.values.tolist())
            st.cache_data.clear()  # Limpiar caché después de guardar
            return True
    except Exception as e:
        st.error(f"❌ Error al guardar inventario: {e}")
        return False

def guardar_historial(df):
    try:
        sheet = conectar_google_sheets()
        if sheet:
            worksheet = sheet.worksheet("historial")
            worksheet.clear()
            if not df.empty:
                worksheet.update([df.columns.values.tolist()] + df.values.tolist())
            st.cache_data.clear()
            return True
    except Exception as e:
        st.error(f"❌ Error al guardar historial: {e}")
        return False

# Función auxiliar para limpiar caché manualmente (usar después de operaciones de escritura)
def limpiar_cache():
    st.cache_data.clear()

# ============================================
# FUNCIONES PRINCIPALES (acumulación por tipo)
# ============================================
def agregar_residuo(tipo, cantidad, precio_compra, precio_venta, proveedor):
    if not tipo or cantidad <= 0:
        st.toast("⚠️ Complete todos los campos correctamente", icon="⚠️")
        return "❌ Complete todos los campos"
    
    df = cargar_inventario_cache()
    
    if not df.empty and tipo in df["tipo_residuo"].values:
        idx = df[df["tipo_residuo"] == tipo].index[0]
        cantidad_anterior = df.loc[idx, "cantidad"]
        nueva_cantidad = cantidad_anterior + float(cantidad)
        df.loc[idx, "cantidad"] = nueva_cantidad
        df.loc[idx, "precio_compra"] = float(precio_compra)
        df.loc[idx, "precio_venta"] = float(precio_venta)
        df.loc[idx, "proveedor"] = proveedor
        df.loc[idx, "fecha_ingreso"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        guardar_inventario(df)
        
        df_hist = cargar_historial_cache()
        nuevo_hist = pd.DataFrame([{
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tipo_movimiento": "COMPRA",
            "id_residuo": df.loc[idx, "id"],
            "tipo_residuo": tipo,
            "cantidad": float(cantidad),
            "precio_unitario": float(precio_compra),
            "valor_total": float(cantidad) * float(precio_compra),
            "proveedor_cliente": proveedor,
            "dias_rotacion": ""
        }])
        df_hist = pd.concat([df_hist, nuevo_hist], ignore_index=True)
        guardar_historial(df_hist)
        
        mensaje = f"✅ Se añadieron {cantidad} kg a '{tipo}'. Stock anterior: {cantidad_anterior} kg → Nuevo stock: {nueva_cantidad} kg"
        st.toast(mensaje, icon="📦")
        limpiar_cache()  # Limpiar caché para forzar recarga de datos
        return mensaje
    else:
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
        
        df_hist = cargar_historial_cache()
        nuevo_hist = pd.DataFrame([{
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tipo_movimiento": "COMPRA",
            "id_residuo": nuevo_id,
            "tipo_residuo": tipo,
            "cantidad": float(cantidad),
            "precio_unitario": float(precio_compra),
            "valor_total": float(cantidad) * float(precio_compra),
            "proveedor_cliente": proveedor,
            "dias_rotacion": ""
        }])
        df_hist = pd.concat([df_hist, nuevo_hist], ignore_index=True)
        guardar_historial(df_hist)
        
        mensaje = f"✅ Nuevo residuo '{tipo}' creado con {cantidad} kg. ID: {nuevo_id}"
        st.toast(mensaje, icon="🆕")
        limpiar_cache()
        return mensaje

def vender_residuo_por_tipo(tipo, cantidad_vendida):
    df = cargar_inventario_cache()
    
    if df.empty or tipo not in df["tipo_residuo"].values:
        st.toast(f"❌ Residuo '{tipo}' no encontrado", icon="❌")
        return f"❌ Residuo '{tipo}' no encontrado"
    
    idx = df[df["tipo_residuo"] == tipo].index[0]
    disponible = df.loc[idx, "cantidad"]
    precio_venta = df.loc[idx, "precio_venta"]
    id_residuo = df.loc[idx, "id"]
    fecha_ingreso = df.loc[idx, "fecha_ingreso"]
    
    if cantidad_vendida > disponible:
        st.toast(f"❌ Stock insuficiente. Solo hay {disponible} kg de '{tipo}'", icon="⚠️")
        return f"❌ Stock insuficiente. Disponible: {disponible} kg"
    
    nueva_cantidad = disponible - cantidad_vendida
    valor_venta = cantidad_vendida * precio_venta
    
    fecha_ingreso_dt = datetime.strptime(fecha_ingreso, "%Y-%m-%d %H:%M:%S")
    dias_rotacion = max((datetime.now() - fecha_ingreso_dt).days, 1)
    
    if nueva_cantidad == 0:
        df = df.drop(idx)
        mensaje = f"✅ Venta exitosa: {cantidad_vendida} kg de '{tipo}' por ${valor_venta:,.2f}. Stock AGOTADO. Días en almacén: {dias_rotacion}"
        st.toast(mensaje, icon="💰")
    else:
        df.loc[idx, "cantidad"] = nueva_cantidad
        mensaje = f"✅ Venta exitosa: {cantidad_vendida} kg de '{tipo}' por ${valor_venta:,.2f}. Stock restante: {nueva_cantidad} kg. Días en almacén: {dias_rotacion}"
        st.toast(mensaje, icon="💲")
    
    guardar_inventario(df.reset_index(drop=True))
    
    df_hist = cargar_historial_cache()
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
    
    limpiar_cache()
    return mensaje

# ============================================
# CLASIFICACIONES Y ANÁLISIS (con caché)
# ============================================

@st.cache_data(ttl=60, show_spinner=False)
def clasificar_abc_valor():
    """Clasificación ABC por valor de stock actual."""
    df = cargar_inventario_cache()
    if df.empty:
        return pd.DataFrame()
    df["valor_rotacion"] = df["cantidad"] * df["precio_venta"]
    df_ordenado = df.sort_values("valor_rotacion", ascending=False).reset_index(drop=True)
    total = df_ordenado["valor_rotacion"].sum()
    if total == 0:
        return pd.DataFrame()
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

@st.cache_data(ttl=60, show_spinner=False)
def clasificar_abc_valor_historico():
    """
    NUEVA CLASIFICACIÓN: ABC por valor histórico total de VENTAS.
    Agrupa por tipo_residuo y suma el valor_total de las ventas.
    """
    df_hist = cargar_historial_cache()
    if df_hist.empty:
        return pd.DataFrame()
    ventas = df_hist[df_hist["tipo_movimiento"] == "VENTA"].copy()
    if ventas.empty:
        return pd.DataFrame()
    # Agrupar por tipo_residuo (y también id_residuo, pero para mostrar usamos tipo)
    ventas_agrupadas = ventas.groupby("tipo_residuo").agg(
        valor_total_ventas=("valor_total", "sum"),
        cantidad_total_vendida=("cantidad", "sum"),
        numero_ventas=("fecha", "count")
    ).reset_index()
    # Ordenar por mayor valor histórico
    ventas_agrupadas = ventas_agrupadas.sort_values("valor_total_ventas", ascending=False).reset_index(drop=True)
    total_ventas = ventas_agrupadas["valor_total_ventas"].sum()
    if total_ventas == 0:
        return pd.DataFrame()
    ventas_agrupadas["porcentaje_acumulado"] = (ventas_agrupadas["valor_total_ventas"].cumsum() / total_ventas * 100)
    def asignar_abc_hist(porc):
        if porc <= 80:
            return "A - Alto valor histórico (80%)"
        elif porc <= 95:
            return "B - Medio valor histórico (15%)"
        else:
            return "C - Bajo valor histórico (5%)"
    ventas_agrupadas["clasificacion_historica"] = ventas_agrupadas["porcentaje_acumulado"].apply(asignar_abc_hist)
    return ventas_agrupadas

@st.cache_data(ttl=60, show_spinner=False)
def calcular_velocidad_rotacion():
    df_hist = cargar_historial_cache()
    if df_hist.empty:
        return pd.DataFrame()
    ventas = df_hist[df_hist["tipo_movimiento"] == "VENTA"].copy()
    if ventas.empty:
        return pd.DataFrame()
    if "dias_rotacion" not in ventas.columns:
        ventas["dias_rotacion"] = 1
    velocidad = ventas.groupby(["id_residuo", "tipo_residuo"]).agg({
        "cantidad": "sum",
        "dias_rotacion": "mean"
    }).reset_index()
    velocidad.columns = ["id", "tipo_residuo", "cantidad_total_vendida", "dias_promedio_rotacion"]
    velocidad["velocidad_rotacion"] = velocidad["cantidad_total_vendida"] / velocidad["dias_promedio_rotacion"]
    velocidad_ordenado = velocidad.sort_values("velocidad_rotacion", ascending=False).reset_index(drop=True)
    total_vel = velocidad_ordenado["velocidad_rotacion"].sum()
    if total_vel == 0:
        return pd.DataFrame()
    velocidad_ordenado["porcentaje_acumulado"] = (velocidad_ordenado["velocidad_rotacion"].cumsum() / total_vel * 100)
    def asignar_abc_vel(porc):
        if porc <= 80:
            return "A - Rápida rotación"
        elif porc <= 95:
            return "B - Rotación media"
        else:
            return "C - Lenta rotación"
    velocidad_ordenado["clasificacion_velocidad"] = velocidad_ordenado["porcentaje_acumulado"].apply(asignar_abc_vel)
    return velocidad_ordenado

@st.cache_data(ttl=60, show_spinner=False)
def analisis_tiempo_salida():
    df_hist = cargar_historial_cache()
    if df_hist.empty:
        return pd.DataFrame()
    ventas = df_hist[df_hist["tipo_movimiento"] == "VENTA"].copy()
    if ventas.empty:
        return pd.DataFrame()
    if "dias_rotacion" not in ventas.columns:
        ventas["dias_rotacion"] = 1
    tiempo = ventas.groupby(["id_residuo", "tipo_residuo"]).agg({
        "dias_rotacion": "mean",
        "cantidad": "sum"
    }).reset_index()
    tiempo.columns = ["id", "tipo_residuo", "dias_promedio", "cantidad_vendida"]
    tiempo = tiempo.sort_values("dias_promedio", ascending=False)
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
# FUNCIONES PARA GRÁFICOS DE PARETO (AMBOS)
# ============================================
def grafico_pareto_valor():
    df_valor = clasificar_abc_valor()
    if df_valor.empty:
        return None
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ['#ff4444' if 'A' in c else '#ffaa44' if 'B' in c else '#44ff44' for c in df_valor['clasificacion_valor']]
    ax.bar(range(len(df_valor)), df_valor['valor_rotacion'], color=colors, alpha=0.7)
    ax.set_xticks(range(len(df_valor)))
    ax.set_xticklabels(df_valor['tipo_residuo'], rotation=45, ha='right')
    ax.set_ylabel("Valor de rotación ($)")
    ax.set_title("Gráfico de Pareto - Valor de Rotación (Stock Actual)")
    st.pyplot(fig)

def grafico_pareto_valor_historico():
    """Nuevo gráfico de Pareto para valor histórico de ventas"""
    df_hist_val = clasificar_abc_valor_historico()
    if df_hist_val.empty:
        return None
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ['#4444ff' if 'A' in c else '#88aaff' if 'B' in c else '#aaccff' for c in df_hist_val['clasificacion_historica']]
    ax.bar(range(len(df_hist_val)), df_hist_val['valor_total_ventas'], color=colors, alpha=0.7)
    ax.set_xticks(range(len(df_hist_val)))
    ax.set_xticklabels(df_hist_val['tipo_residuo'], rotation=45, ha='right')
    ax.set_ylabel("Valor total de ventas ($)")
    ax.set_title("Gráfico de Pareto - Valor Histórico de Ventas")
    st.pyplot(fig)

def grafico_pareto_velocidad():
    df_vel = calcular_velocidad_rotacion()
    if df_vel.empty:
        return None
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ['#ff4444' if 'Rápida' in c else '#ffaa44' if 'media' in c else '#44ff44' for c in df_vel['clasificacion_velocidad']]
    ax.bar(range(len(df_vel)), df_vel['velocidad_rotacion'], color=colors, alpha=0.7)
    ax.set_xticks(range(len(df_vel)))
    ax.set_xticklabels(df_vel['tipo_residuo'], rotation=45, ha='right')
    ax.set_ylabel("Velocidad de rotación (kg/día)")
    ax.set_title("Gráfico de Pareto - Velocidad de Rotación")
    st.pyplot(fig)

# ============================================
# NUEVAS FUNCIONES: EXPORTACIÓN, TENDENCIAS, ALERTAS
# ============================================

def exportar_excel():
    """Genera un archivo Excel con inventario, historial, clasificaciones y resúmenes"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_inv = cargar_inventario_cache()
        df_inv.to_excel(writer, sheet_name='Inventario', index=False)
        df_hist = cargar_historial_cache()
        df_hist.to_excel(writer, sheet_name='Historial', index=False)
        df_val = clasificar_abc_valor()
        if not df_val.empty:
            df_val.to_excel(writer, sheet_name='Clasificacion_Valor_Stock', index=False)
        df_val_hist = clasificar_abc_valor_historico()
        if not df_val_hist.empty:
            df_val_hist.to_excel(writer, sheet_name='Clasificacion_Valor_Historico', index=False)
        df_vel = calcular_velocidad_rotacion()
        if not df_vel.empty:
            df_vel.to_excel(writer, sheet_name='Clasificacion_Velocidad', index=False)
        df_tiempo = analisis_tiempo_salida()
        if not df_tiempo.empty:
            df_tiempo.to_excel(writer, sheet_name='Tiempo_Salida', index=False)
    output.seek(0)
    return output

def exportar_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Reporte Reciclaje Velásquez", ln=1, align='C')
    pdf.cell(200, 10, txt=f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=1, align='C')
    df_inv = cargar_inventario_cache()
    total_valor = (df_inv['cantidad'] * df_inv['precio_venta']).sum() if not df_inv.empty else 0
    pdf.cell(200, 10, txt=f"Valor total inventario actual: ${total_valor:,.2f}", ln=1)
    pdf.cell(200, 10, txt=f"Items en stock: {len(df_inv)}", ln=1)
    # Añadir resumen de valor histórico
    df_val_hist = clasificar_abc_valor_historico()
    if not df_val_hist.empty:
        total_ventas_hist = df_val_hist['valor_total_ventas'].sum()
        pdf.cell(200, 10, txt=f"Valor total histórico de ventas: ${total_ventas_hist:,.2f}", ln=1)
    pdf.cell(200, 10, txt="-----------------------------------", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt="Top 10 residuos por cantidad actual:", ln=1)
    if not df_inv.empty:
        top = df_inv.nlargest(10, 'cantidad')[['tipo_residuo', 'cantidad']]
        for _, row in top.iterrows():
            pdf.cell(200, 8, txt=f"{row['tipo_residuo']}: {row['cantidad']} kg", ln=1)
    else:
        pdf.cell(200, 8, txt="No hay datos", ln=1)
    pdf_output = pdf.output(dest='S').encode('latin-1')
    return io.BytesIO(pdf_output)

def grafico_tendencias_mensuales():
    df_hist = cargar_historial_cache()
    if df_hist.empty:
        st.info("No hay suficientes datos para tendencias.")
        return
    df_hist['fecha'] = pd.to_datetime(df_hist['fecha'])
    df_hist['mes'] = df_hist['fecha'].dt.to_period('M').astype(str)
    compras = df_hist[df_hist['tipo_movimiento'] == 'COMPRA'].groupby('mes')['valor_total'].sum()
    ventas = df_hist[df_hist['tipo_movimiento'] == 'VENTA'].groupby('mes')['valor_total'].sum()
    fig, ax = plt.subplots(figsize=(10, 5))
    if not compras.empty:
        ax.plot(compras.index, compras.values, marker='o', label='Compras')
    if not ventas.empty:
        ax.plot(ventas.index, ventas.values, marker='s', label='Ventas')
    ax.set_xlabel('Mes')
    ax.set_ylabel('Valor total ($)')
    ax.set_title('Tendencia mensual de compras y ventas')
    ax.legend()
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)

def low_stock_alerts():
    df_inv = cargar_inventario_cache()
    if df_inv.empty:
        return
    umbral = st.session_state.umbral_stock
    low_stock = df_inv[df_inv['cantidad'] < umbral]
    if not low_stock.empty:
        st.warning(f"⚠️ **Alerta de stock mínimo** (umbral: {umbral} kg)")
        for _, row in low_stock.iterrows():
            st.write(f"- {row['tipo_residuo']}: {row['cantidad']} kg (por debajo de {umbral} kg)")
    else:
        st.success("✅ Todos los residuos están por encima del umbral de stock.")

# ============================================
# DASHBOARD EJECUTIVO (sin cambios relevantes)
# ============================================
def dashboard_ejecutivo():
    st.subheader("📊 Dashboard Ejecutivo")
    df_inv = cargar_inventario_cache()
    total_valor = (df_inv['cantidad'] * df_inv['precio_venta']).sum() if not df_inv.empty else 0
    total_items = len(df_inv)
    df_hist = cargar_historial_cache()
    ventas = df_hist[df_hist['tipo_movimiento'] == 'VENTA'] if not df_hist.empty else pd.DataFrame()
    total_ventas = ventas['valor_total'].sum() if not ventas.empty else 0
    df_vel = calcular_velocidad_rotacion()
    velocidad_prom = df_vel['velocidad_rotacion'].mean() if not df_vel.empty else 0
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Valor inventario actual", f"${total_valor:,.2f}")
    col2.metric("Items en stock", total_items)
    col3.metric("Ventas totales históricas", f"${total_ventas:,.2f}")
    col4.metric("Velocidad promedio", f"{velocidad_prom:.2f} kg/día")
    
    nuevo_umbral = st.number_input("Definir umbral de stock mínimo (kg)", min_value=0.0, value=st.session_state.umbral_stock, step=5.0)
    if nuevo_umbral != st.session_state.umbral_stock:
        st.session_state.umbral_stock = nuevo_umbral
        st.rerun()
    low_stock_alerts()
    st.subheader("📈 Tendencia mensual de compras/ventas")
    grafico_tendencias_mensuales()
    st.subheader("📑 Exportar reportes")
    col_ex1, col_ex2 = st.columns(2)
    with col_ex1:
        if st.button("📊 Exportar a Excel"):
            excel_data = exportar_excel()
            b64 = base64.b64encode(excel_data.read()).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="reporte_reciclaje.xlsx">Descargar Excel</a>'
            st.markdown(href, unsafe_allow_html=True)
            st.toast("✅ Reporte Excel generado", icon="📊")
    with col_ex2:
        if st.button("📄 Exportar a PDF"):
            pdf_data = exportar_pdf()
            b64 = base64.b64encode(pdf_data.read()).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="reporte_reciclaje.pdf">Descargar PDF</a>'
            st.markdown(href, unsafe_allow_html=True)
            st.toast("✅ Reporte PDF generado", icon="📄")

# ============================================
# INTERFAZ DE USUARIO (con NUEVA PESTAÑA para valor histórico)
# ============================================
if 'bienvenido' not in st.session_state:
    st.toast("♻️ ¡Bienvenido al Sistema de Reciclaje Velásquez! Sistema listo para operar.", icon="🎉")
    st.session_state.bienvenido = True

# Ahora tenemos 8 pestañas (añadimos la nueva de valor histórico)
tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Dashboard",
    "📦 Gestión",
    "💰 Clasif. Valor (Stock)",
    "💰 Clasif. Valor (Histórico)",
    "⚡ Clasif. Velocidad",
    "⏱️ Tiempo de Salida",
    "📊 Gráficos",
    "📜 Historial"
])

# ---------- Pestaña 0: Dashboard ----------
with tab0:
    dashboard_ejecutivo()

# ---------- Pestaña 1: Gestión (con filtro) ----------
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("➕ Ingresar Residuo")
        with st.form("ingresar"):
            tipo = st.text_input("Tipo de residuo", placeholder="PET, Cartón, Aluminio...")
            cantidad = st.number_input("Cantidad (kg)", min_value=0.0, step=10.0)
            precio_compra = st.number_input("Precio compra ($/kg)", min_value=0.0, step=0.1)
            precio_venta = st.number_input("Precio venta ($/kg)", min_value=0.0, step=0.1)
            proveedor = st.text_input("Proveedor")
            submitted = st.form_submit_button("Agregar")
            if submitted:
                if tipo and cantidad > 0:
                    resultado = agregar_residuo(tipo, cantidad, precio_compra, precio_venta, proveedor)
                    st.success(resultado)
                    st.rerun()
                else:
                    st.warning("⚠️ Complete todos los campos obligatorios (tipo y cantidad)")
    with col2:
        st.subheader("💸 Vender por Tipo")
        with st.form("vender"):
            tipo_vender = st.text_input("Tipo de residuo a vender", placeholder="PET, Cartón...")
            cantidad_vender = st.number_input("Cantidad a vender (kg)", min_value=0.0, step=10.0)
            submitted_venta = st.form_submit_button("Vender")
            if submitted_venta:
                if tipo_vender and cantidad_vender > 0:
                    resultado = vender_residuo_por_tipo(tipo_vender, cantidad_vender)
                    st.success(resultado)
                    st.rerun()
                else:
                    st.warning("⚠️ Complete todos los campos obligatorios (tipo y cantidad)")
    
    st.subheader("📋 Inventario Actual")
    search_term = st.text_input("🔍 Buscar residuo (nombre o proveedor)", value=st.session_state.filtro_busqueda, key="search_input")
    st.session_state.filtro_busqueda = search_term
    inventario = cargar_inventario_cache()
    if not inventario.empty:
        if search_term:
            mask = inventario['tipo_residuo'].str.contains(search_term, case=False, na=False) | inventario['proveedor'].str.contains(search_term, case=False, na=False)
            inventario = inventario[mask]
        inv_show = inventario.copy()
        inv_show["precio_compra"] = inv_show["precio_compra"].apply(lambda x: f"${x:.2f}")
        inv_show["precio_venta"] = inv_show["precio_venta"].apply(lambda x: f"${x:.2f}")
        st.dataframe(inv_show, use_container_width=True)
        st.caption(f"📌 Total de tipos de residuos mostrados: {len(inventario)}")
    else:
        st.info("📭 No hay residuos registrados. Agrega tu primer residuo.")

# ---------- Pestaña 2: Clasificación por Valor (Stock Actual) ----------
with tab2:
    st.subheader("💰 Clasificación ABC por VALOR de Rotación (Stock Actual)")
    if st.button("🔄 Actualizar clasificación por VALOR (Stock)", key="btn_valor_stock"):
        df_valor = clasificar_abc_valor()
        if not df_valor.empty:
            df_show = df_valor.copy()
            df_show["precio_venta"] = df_show["precio_venta"].apply(lambda x: f"${x:.2f}")
            df_show["valor_rotacion"] = df_show["valor_rotacion"].apply(lambda x: f"${x:.2f}")
            st.dataframe(df_show[["tipo_residuo", "cantidad", "precio_venta", "valor_rotacion", "clasificacion_valor"]], use_container_width=True)
            st.markdown("### 📊 Resumen del análisis")
            resumen_valor = df_valor.groupby("clasificacion_valor").agg(
                cantidad_items=("id", "count"),
                valor_total=("valor_rotacion", "sum")
            ).reset_index()
            resumen_valor["porcentaje_del_total"] = (resumen_valor["valor_total"] / resumen_valor["valor_total"].sum() * 100).round(1)
            resumen_valor["valor_total"] = resumen_valor["valor_total"].apply(lambda x: f"${x:,.2f}")
            st.dataframe(resumen_valor, use_container_width=True)
            st.markdown("#### 🔍 Interpretación")
            alta = resumen_valor[resumen_valor["clasificacion_valor"].str.contains("A")]["cantidad_items"].values
            media = resumen_valor[resumen_valor["clasificacion_valor"].str.contains("B")]["cantidad_items"].values
            baja = resumen_valor[resumen_valor["clasificacion_valor"].str.contains("C")]["cantidad_items"].values
            st.write(f"- **Categoría A**: {alta[0] if len(alta)>0 else 0} residuos generan el 80% del valor. Enfoque de control riguroso.")
            st.write(f"- **Categoría B**: {media[0] if len(media)>0 else 0} residuos generan el 15% del valor. Control periódico.")
            st.write(f"- **Categoría C**: {baja[0] if len(baja)>0 else 0} residuos generan el 5% del valor. Control simple.")
            st.toast("✅ Clasificación por valor (stock) actualizada", icon="📊")
        else:
            st.warning("⚠️ No hay datos suficientes para clasificar por valor.")

# ---------- Pestaña 3: Clasificación por Valor Histórico (NUEVA) ----------
with tab3:
    st.subheader("💰 Clasificación ABC por VALOR HISTÓRICO (Ventas Acumuladas)")
    st.markdown("**Fórmula:** `Valor histórico = Suma de todas las ventas (cantidad × precio venta)`")
    if st.button("🔄 Actualizar clasificación por VALOR HISTÓRICO", key="btn_valor_historico"):
        df_hist_val = clasificar_abc_valor_historico()
        if not df_hist_val.empty:
            df_show = df_hist_val.copy()
            df_show["valor_total_ventas"] = df_show["valor_total_ventas"].apply(lambda x: f"${x:,.2f}")
            st.dataframe(df_show[["tipo_residuo", "valor_total_ventas", "cantidad_total_vendida", "numero_ventas", "clasificacion_historica"]], use_container_width=True)
            st.markdown("### 📊 Resumen del análisis histórico")
            resumen_hist = df_hist_val.groupby("clasificacion_historica").agg(
                cantidad_items=("tipo_residuo", "count"),
                valor_total=("valor_total_ventas", "sum")
            ).reset_index()
            resumen_hist["porcentaje_del_total"] = (resumen_hist["valor_total"] / resumen_hist["valor_total"].sum() * 100).round(1)
            resumen_hist["valor_total"] = resumen_hist["valor_total"].apply(lambda x: f"${x:,.2f}")
            st.dataframe(resumen_hist, use_container_width=True)
            st.markdown("#### 🔍 Interpretación")
            st.write("Los productos que más ingresos han generado históricamente (categoría A) merecen atención especial, aunque su stock actual sea bajo.")
            st.toast("✅ Clasificación por valor histórico actualizada", icon="📈")
        else:
            st.warning("⚠️ No hay suficientes ventas registradas para calcular el valor histórico.")

# ---------- Pestaña 4: Clasificación por Velocidad ----------
with tab4:
    st.subheader("⚡ Clasificación ABC por VELOCIDAD de Rotación")
    if st.button("🔄 Actualizar clasificación por VELOCIDAD", key="btn_velocidad"):
        df_vel = calcular_velocidad_rotacion()
        if not df_vel.empty:
            df_show = df_vel.copy()
            df_show["velocidad_rotacion"] = df_show["velocidad_rotacion"].apply(lambda x: f"{x:.2f} kg/día")
            st.dataframe(df_show[["tipo_residuo", "cantidad_total_vendida", "dias_promedio_rotacion", "velocidad_rotacion", "clasificacion_velocidad"]], use_container_width=True)
            resumen_vel = df_vel.groupby("clasificacion_velocidad").agg(
                cantidad_items=("id", "count"),
                velocidad_promedio=("velocidad_rotacion", "mean"),
                dias_promedio=("dias_promedio_rotacion", "mean")
            ).reset_index()
            resumen_vel["velocidad_promedio"] = resumen_vel["velocidad_promedio"].apply(lambda x: f"{x:.2f} kg/día")
            resumen_vel["dias_promedio"] = resumen_vel["dias_promedio"].apply(lambda x: f"{x:.1f} días")
            st.dataframe(resumen_vel, use_container_width=True)
            st.toast("✅ Clasificación por velocidad actualizada", icon="⚡")
        else:
            st.warning("⚠️ Se necesitan ventas registradas para calcular velocidad.")

# ---------- Pestaña 5: Tiempo de Salida ----------
with tab5:
    st.subheader("⏱️ Análisis de Tiempo de Salida del Almacén")
    if st.button("🔄 Analizar tiempos de salida", key="btn_tiempo"):
        df_tiempo = analisis_tiempo_salida()
        if not df_tiempo.empty:
            df_show = df_tiempo.copy()
            df_show["dias_promedio"] = df_show["dias_promedio"].apply(lambda x: f"{x:.1f} días")
            st.dataframe(df_show[["tipo_residuo", "dias_promedio", "cantidad_vendida", "clasificacion_tiempo"]], use_container_width=True)
            st.markdown("### 📊 Distribución por tiempo de salida")
            resumen_tiempo = df_tiempo.groupby("clasificacion_tiempo").agg(
                cantidad_items=("id", "count"),
                dias_promedio=("dias_promedio", "mean")
            ).reset_index()
            resumen_tiempo["dias_promedio"] = resumen_tiempo["dias_promedio"].apply(lambda x: f"{x:.1f} días")
            st.dataframe(resumen_tiempo, use_container_width=True)
            st.toast("✅ Análisis de tiempos completado", icon="⏱️")
        else:
            st.warning("⚠️ No hay suficientes ventas para analizar tiempos.")

# ---------- Pestaña 6: Gráficos (se añade el gráfico de valor histórico) ----------
with tab6:
    st.subheader("📊 Gráficos de Pareto")
    col_graf1, col_graf2 = st.columns(2)
    with col_graf1:
        st.markdown("### 📈 Por VALOR (Stock Actual)")
        if st.button("Generar gráfico Valor (Stock)", key="btn_pareto_valor"):
            df_valor = clasificar_abc_valor()
            if not df_valor.empty:
                grafico_pareto_valor()
                st.caption("🔴 A: Alto valor | 🟡 B: Medio | 🟢 C: Bajo")
            else:
                st.warning("No hay datos")
    with col_graf2:
        st.markdown("### 📈 Por VALOR HISTÓRICO (Ventas)")
        if st.button("Generar gráfico Valor Histórico", key="btn_pareto_historico"):
            df_hist_val = clasificar_abc_valor_historico()
            if not df_hist_val.empty:
                grafico_pareto_valor_historico()
                st.caption("🔵 A: Alto valor histórico | 🔷 B: Medio | 🔹 C: Bajo")
            else:
                st.warning("No hay suficientes ventas")
    
    st.markdown("---")
    col_graf3, _ = st.columns(2)
    with col_graf3:
        st.markdown("### ⚡ Por VELOCIDAD")
        if st.button("Generar gráfico Velocidad", key="btn_pareto_vel"):
            df_vel = calcular_velocidad_rotacion()
            if not df_vel.empty:
                grafico_pareto_velocidad()
                st.caption("🔴 A: Rápida | 🟡 B: Media | 🟢 C: Lenta")
            else:
                st.warning("No hay suficientes ventas")

# ---------- Pestaña 7: Historial ----------
with tab7:
    st.subheader("📜 Historial Completo")
    historial = cargar_historial_cache()
    if not historial.empty:
        cols_mostrar = ["fecha", "tipo_movimiento", "tipo_residuo", "cantidad", "precio_unitario", "valor_total", "proveedor_cliente", "dias_rotacion"]
        df_hist_show = historial[cols_mostrar].copy()
        df_hist_show["precio_unitario"] = df_hist_show["precio_unitario"].apply(lambda x: f"${x:.2f}")
        df_hist_show["valor_total"] = df_hist_show["valor_total"].apply(lambda x: f"${x:.2f}")
        st.dataframe(df_hist_show.sort_values("fecha", ascending=False), use_container_width=True)
        st.caption(f"📌 Total de movimientos registrados: {len(historial)}")
    else:
        st.info("📭 No hay movimientos registrados aún.")

st.divider()
st.caption("♻️ **Reciclaje Velásquez** | ABC Dual mejorado con Valor Histórico | Datos persistentes + caché para evitar cuotas")
