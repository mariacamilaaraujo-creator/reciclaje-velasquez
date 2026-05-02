import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import io
import base64
from fpdf import FPDF

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
    
    # Explicación del método ABC por VALOR
    st.markdown("### 1️⃣ Clasificación por **VALOR**")
    st.markdown("**Fórmula:** `Valor de rotación = Cantidad disponible × Precio de venta`")
    st.markdown("**Interpretación:** Mide la importancia económica de cada residuo.")
    st.markdown("""
    - **Categoría A (80%)** → Generan la mayor parte del valor. Prioridad alta.
    - **Categoría B (15%)** → Valor medio. Control periódico.
    - **Categoría C (5%)** → Bajo valor. Control simple.
    """)
    st.markdown("---")
    
    # Explicación del método ABC por VELOCIDAD
    st.markdown("### 2️⃣ Clasificación por **VELOCIDAD**")
    st.markdown("**Fórmula:** `Velocidad de rotación = Cantidad vendida / Días en inventario`")
    st.markdown("**Interpretación:** Qué tan rápido se vende un residuo desde que entra al almacén.")
    st.markdown("""
    - **Categoría A (80%)** → Rápida rotación (sale rápido). Mantener stock continuo.
    - **Categoría B (15%)** → Rotación media.
    - **Categoría C (5%)** → Lenta rotación (demora en salir). Minimizar stock.
    """)
    st.markdown("---")
    
    # Explicación del análisis de tiempo de salida
    st.markdown("### ⏱️ Tiempo de Salida")
    st.markdown("**Clasificación por días promedio para venderse:**")
    st.markdown("""
    - 🚀 **Muy rápido** (≤ 7 días)
    - 📦 **Rápido** (8-30 días)
    - ⏳ **Normal** (31-90 días)
    - 🐢 **Lento** (> 90 días)
    """)
    st.markdown("---")
    st.caption("💾 Datos guardados permanentemente en Google Sheets")
    st.caption("♻️ Reciclaje Velásquez")

# ============================================
# CONEXIÓN A GOOGLE SHEETS (igual)
# ============================================
def conectar_google_sheets():
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

def cargar_inventario():
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
        st.warning(f"⚠️ No se pudo cargar inventario: {e}")
        return pd.DataFrame(columns=["id", "tipo_residuo", "cantidad", "precio_compra", "precio_venta", "proveedor", "fecha_ingreso"])

def guardar_inventario(df):
    try:
        sheet = conectar_google_sheets()
        if sheet:
            worksheet = sheet.worksheet("inventario")
            worksheet.clear()
            if not df.empty:
                worksheet.update([df.columns.values.tolist()] + df.values.tolist())
            return True
    except Exception as e:
        st.error(f"❌ Error al guardar: {e}")
        return False

def cargar_historial():
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
        st.warning(f"⚠️ No se pudo cargar historial: {e}")
        return pd.DataFrame(columns=["fecha", "tipo_movimiento", "id_residuo", "tipo_residuo", "cantidad", "precio_unitario", "valor_total", "proveedor_cliente", "dias_rotacion"])

def guardar_historial(df):
    try:
        sheet = conectar_google_sheets()
        if sheet:
            worksheet = sheet.worksheet("historial")
            worksheet.clear()
            if not df.empty:
                worksheet.update([df.columns.values.tolist()] + df.values.tolist())
            return True
    except Exception as e:
        st.error(f"❌ Error al guardar historial: {e}")
        return False

# ============================================
# FUNCIONES PRINCIPALES (acumulación por tipo)
# ============================================
def agregar_residuo(tipo, cantidad, precio_compra, precio_venta, proveedor):
    if not tipo or cantidad <= 0:
        st.toast("⚠️ Complete todos los campos correctamente", icon="⚠️")
        return "❌ Complete todos los campos"
    
    df = cargar_inventario()
    
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
        
        df_hist = cargar_historial()
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
        
        df_hist = cargar_historial()
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
        return mensaje

def vender_residuo_por_tipo(tipo, cantidad_vendida):
    df = cargar_inventario()
    
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
# CLASIFICACIONES Y ANÁLISIS (sin cambios)
# ============================================
def clasificar_abc_valor():
    df = cargar_inventario()
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

def calcular_velocidad_rotacion():
    df_hist = cargar_historial()
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

def analisis_tiempo_salida():
    df_hist = cargar_historial()
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
    ax.set_title("Gráfico de Pareto - Valor de Rotación")
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
        # Inventario
        df_inv = cargar_inventario()
        df_inv.to_excel(writer, sheet_name='Inventario', index=False)
        # Historial
        df_hist = cargar_historial()
        df_hist.to_excel(writer, sheet_name='Historial', index=False)
        # Clasificación valor
        df_val = clasificar_abc_valor()
        if not df_val.empty:
            df_val.to_excel(writer, sheet_name='Clasificacion_Valor', index=False)
        # Clasificación velocidad
        df_vel = calcular_velocidad_rotacion()
        if not df_vel.empty:
            df_vel.to_excel(writer, sheet_name='Clasificacion_Velocidad', index=False)
        # Tiempo salida
        df_tiempo = analisis_tiempo_salida()
        if not df_tiempo.empty:
            df_tiempo.to_excel(writer, sheet_name='Tiempo_Salida', index=False)
    output.seek(0)
    return output

def exportar_pdf():
    """Genera un PDF sencillo con un resumen ejecutivo"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Reporte Reciclaje Velásquez", ln=1, align='C')
    pdf.cell(200, 10, txt=f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=1, align='C')
    
    # KPIs
    df_inv = cargar_inventario()
    total_valor = (df_inv['cantidad'] * df_inv['precio_venta']).sum() if not df_inv.empty else 0
    pdf.cell(200, 10, txt=f"Valor total inventario: ${total_valor:,.2f}", ln=1)
    pdf.cell(200, 10, txt=f"Items en stock: {len(df_inv)}", ln=1)
    pdf.cell(200, 10, txt=f"-----------------------------------", ln=1)
    
    # Inventario resumido (primeros 10)
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt="Top 10 residuos por cantidad:", ln=1)
    if not df_inv.empty:
        top = df_inv.nlargest(10, 'cantidad')[['tipo_residuo', 'cantidad']]
        for i, row in top.iterrows():
            pdf.cell(200, 8, txt=f"{row['tipo_residuo']}: {row['cantidad']} kg", ln=1)
    else:
        pdf.cell(200, 8, txt="No hay datos", ln=1)
    
    pdf_output = pdf.output(dest='S').encode('latin-1')
    return io.BytesIO(pdf_output)

def grafico_tendencias_mensuales():
    """Gráfico de ventas y compras mensuales"""
    df_hist = cargar_historial()
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
    """Muestra alertas de stock por debajo del umbral definido"""
    df_inv = cargar_inventario()
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
# DASHBOARD EJECUTIVO (NUEVA PESTAÑA)
# ============================================
def dashboard_ejecutivo():
    st.subheader("📊 Dashboard Ejecutivo")
    
    # KPIs
    df_inv = cargar_inventario()
    total_valor = (df_inv['cantidad'] * df_inv['precio_venta']).sum() if not df_inv.empty else 0
    total_items = len(df_inv)
    
    df_hist = cargar_historial()
    ventas = df_hist[df_hist['tipo_movimiento'] == 'VENTA'] if not df_hist.empty else pd.DataFrame()
    total_ventas = ventas['valor_total'].sum() if not ventas.empty else 0
    
    # Velocidad promedio
    df_vel = calcular_velocidad_rotacion()
    velocidad_prom = df_vel['velocidad_rotacion'].mean() if not df_vel.empty else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Valor inventario", f"${total_valor:,.2f}")
    col2.metric("Items en stock", total_items)
    col3.metric("Ventas totales (histórico)", f"${total_ventas:,.2f}")
    col4.metric("Velocidad promedio", f"{velocidad_prom:.2f} kg/día")
    
    # Umbral de stock
    nuevo_umbral = st.number_input("Definir umbral de stock mínimo (kg)", min_value=0.0, value=st.session_state.umbral_stock, step=5.0)
    if nuevo_umbral != st.session_state.umbral_stock:
        st.session_state.umbral_stock = nuevo_umbral
        st.rerun()
    
    # Alertas
    low_stock_alerts()
    
    # Gráfico de tendencias
    st.subheader("📈 Tendencia mensual de compras/ventas")
    grafico_tendencias_mensuales()
    
    # Exportar
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
# INTERFAZ DE USUARIO (con nueva pestaña Dashboard)
# ============================================
if 'bienvenido' not in st.session_state:
    st.toast("♻️ ¡Bienvenido al Sistema de Reciclaje Velásquez! Sistema listo para operar.", icon="🎉")
    st.session_state.bienvenido = True

# Añadimos la pestaña Dashboard al principio
tab0, tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Dashboard",
    "📦 Gestión", 
    "💰 Clasificación Valor", 
    "⚡ Clasificación Velocidad",
    "⏱️ Tiempo de Salida",
    "📊 Gráficos", 
    "📜 Historial"
])

# ---------- Pestaña 0: Dashboard Ejecutivo ----------
with tab0:
    dashboard_ejecutivo()

# ---------- Pestaña 1: Gestión (con filtro de búsqueda añadido) ----------
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
    # Filtro de búsqueda
    search_term = st.text_input("🔍 Buscar residuo (nombre o proveedor)", value=st.session_state.filtro_busqueda, key="search_input")
    st.session_state.filtro_busqueda = search_term
    
    inventario = cargar_inventario()
    if not inventario.empty:
        # Aplicar filtro
        if search_term:
            mask = inventario['tipo_residuo'].str.contains(search_term, case=False, na=False) | inventario['proveedor'].str.contains(search_term, case=False, na=False)
            inventario = inventario[mask]
        
        inv_show = inventario.copy()
        inv_show["precio_compra"] = inv_show["precio_compra"].apply(lambda x: f"${x:.2f}")
        inv_show["precio_venta"] = inv_show["precio_venta"].apply(lambda x: f"${x:.2f}")
        st.dataframe(inv_show, use_container_width=True)
        st.caption(f"📌 Total de tipos de residuos mostrados: {len(inventario)}")
    else:
        st.info("📭 No hay residuos registrados. Agrega tu primer residuo usando el formulario.")

# ---------- Resto de pestañas (tab2 a tab6) exactamente igual que antes ----------
# (Copia el código de las pestañas originales desde tab2 hasta tab6)

# Nota: Por brevedad, aquí solo incluyo el contenido de tab2 a tab6 tal cual estaban.
# Asegúrate de mantener la indentación correcta.

# ---------- Pestaña 2: Clasificación por Valor ----------
with tab2:
    st.subheader("💰 Clasificación ABC por VALOR de Rotación")
    if st.button("🔄 Actualizar clasificación por VALOR", key="btn_valor_update"):
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
            st.toast("✅ Clasificación por valor actualizada correctamente", icon="📊")
        else:
            st.warning("⚠️ No hay datos suficientes para clasificar por valor.")

# ---------- Pestaña 3: Clasificación por Velocidad ----------
with tab3:
    st.subheader("⚡ Clasificación ABC por VELOCIDAD de Rotación")
    if st.button("🔄 Actualizar clasificación por VELOCIDAD", key="btn_vel_update"):
        df_vel = calcular_velocidad_rotacion()
        if not df_vel.empty:
            df_show = df_vel.copy()
            df_show["velocidad_rotacion"] = df_show["velocidad_rotacion"].apply(lambda x: f"{x:.2f} kg/día")
            st.dataframe(df_show[["tipo_residuo", "cantidad_total_vendida", "dias_promedio_rotacion", "velocidad_rotacion", "clasificacion_velocidad"]], use_container_width=True)
            
            st.markdown("### 📊 Resumen del análisis de velocidad")
            resumen_vel = df_vel.groupby("clasificacion_velocidad").agg(
                cantidad_items=("id", "count"),
                velocidad_promedio=("velocidad_rotacion", "mean"),
                dias_promedio=("dias_promedio_rotacion", "mean")
            ).reset_index()
            resumen_vel["velocidad_promedio"] = resumen_vel["velocidad_promedio"].apply(lambda x: f"{x:.2f} kg/día")
            resumen_vel["dias_promedio"] = resumen_vel["dias_promedio"].apply(lambda x: f"{x:.1f} días")
            st.dataframe(resumen_vel, use_container_width=True)
            
            st.markdown("#### 🔍 Interpretación")
            st.write("- **Categoría A (Rápida rotación):** Productos que se venden rápido. Mantener stock suficiente y reorden frecuente.")
            st.write("- **Categoría B (Rotación media):** Balance entre rotación y stock.")
            st.write("- **Categoría C (Lenta rotación):** Minimizar inventario, evaluar si es rentable mantenerlos.")
            st.toast("✅ Clasificación por velocidad actualizada correctamente", icon="⚡")
        else:
            st.warning("⚠️ Se necesitan ventas registradas para calcular velocidad.")

# ---------- Pestaña 4: Análisis de Tiempo de Salida ----------
with tab4:
    st.subheader("⏱️ Análisis de Tiempo de Salida del Almacén")
    st.markdown("**Mide cuántos días tarda cada residuo en venderse desde que ingresa.**")
    if st.button("🔄 Analizar tiempos de salida", key="btn_tiempo_update"):
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
            
            st.markdown("#### 🔍 Interpretación")
            st.write("- **🚀 Muy rápido (≤ 7 días):** Excelente rotación. Asegurar stock continuo.")
            st.write("- **📦 Rápido (8-30 días):** Buena rotación. Revisar periódicamente.")
            st.write("- **⏳ Normal (31-90 días):** Rotación aceptable. Puede optimizarse.")
            st.write("- **🐢 Lento (> 90 días):** Problema de demanda o precio. Considerar reducir stock o campañas de venta.")
            st.toast("✅ Análisis de tiempos de salida completado", icon="⏱️")
        else:
            st.warning("⚠️ No hay suficientes ventas registradas para analizar tiempos de salida.")

# ---------- Pestaña 5: Gráficos (ya tiene dos gráficos) ----------
with tab5:
    st.subheader("📊 Gráficos de Pareto")
    
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        st.markdown("### 📈 Por VALOR")
        if st.button("Generar gráfico de Pareto (Valor)", key="btn_pareto_valor_new"):
            df_valor = clasificar_abc_valor()
            if not df_valor.empty:
                grafico_pareto_valor()
                st.caption("🔴 A: Alto valor | 🟡 B: Medio valor | 🟢 C: Bajo valor")
            else:
                st.warning("No hay datos suficientes para generar el gráfico de valor.")
    
    with col_graf2:
        st.markdown("### ⚡ Por VELOCIDAD")
        if st.button("Generar gráfico de Pareto (Velocidad)", key="btn_pareto_vel_new"):
            df_vel = calcular_velocidad_rotacion()
            if not df_vel.empty:
                grafico_pareto_velocidad()
                st.caption("🔴 A: Rápida rotación | 🟡 B: Rotación media | 🟢 C: Lenta rotación")
            else:
                st.warning("No hay suficientes ventas para generar el gráfico de velocidad.")

# ---------- Pestaña 6: Historial ----------
with tab6:
    st.subheader("📜 Historial Completo")
    historial = cargar_historial()
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
st.caption("♻️ **Reciclaje Velásquez** | Mensajes en tiempo real | Modo acumulación por tipo de residuo | Análisis de tiempo de salida incluido")
