import streamlit as st
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from streamlit_gsheets import GSheetsConnection

# Configuración de la página
st.set_page_config(page_title="Reciclaje Velásquez", page_icon="♻️", layout="wide")

st.title("♻️ RECICLAJE VELÁSQUEZ")
st.markdown("### Sistema de Gestión de Inventario con Clasificación ABC Dual")

# Conexión a Google Sheets
@st.cache_resource
def init_connection():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

@st.cache_data(ttl=30)
def load_inventario():
    conn = init_connection()
    if conn:
        try:
            df = conn.read(worksheet="inventario", ttl=30)
            if df.empty:
                df = pd.DataFrame(columns=["id", "tipo_residuo", "cantidad", "precio_compra", "precio_venta", "proveedor", "fecha_ingreso"])
            return df
        except:
            return pd.DataFrame(columns=["id", "tipo_residuo", "cantidad", "precio_compra", "precio_venta", "proveedor", "fecha_ingreso"])
    return pd.DataFrame()

@st.cache_data(ttl=30)
def load_historial():
    conn = init_connection()
    if conn:
        try:
            df = conn.read(worksheet="historial", ttl=30)
            if df.empty:
                df = pd.DataFrame(columns=["fecha", "tipo_movimiento", "id_residuo", "tipo_residuo", "cantidad", "precio_unitario", "valor_total", "proveedor_cliente"])
            return df
        except:
            return pd.DataFrame(columns=["fecha", "tipo_movimiento", "id_residuo", "tipo_residuo", "cantidad", "precio_unitario", "valor_total", "proveedor_cliente"])
    return pd.DataFrame()

def save_inventario(df):
    conn = init_connection()
    if conn:
        conn.update(worksheet="inventario", data=df)
        st.cache_data.clear()

def save_historial(df):
    conn = init_connection()
    if conn:
        conn.update(worksheet="historial", data=df)
        st.cache_data.clear()

# Funciones principales
def agregar_residuo(tipo, cantidad, precio_compra, precio_venta, proveedor):
    if not tipo or cantidad <= 0:
        return "❌ Complete todos los campos correctamente"
    
    df = load_inventario()
    nuevo_id = df["id"].max() + 1 if not df.empty else 1
    
    nueva_fila = pd.DataFrame([{
        "id": nuevo_id, "tipo_residuo": tipo, "cantidad": float(cantidad),
        "precio_compra": float(precio_compra), "precio_venta": float(precio_venta),
        "proveedor": proveedor, "fecha_ingreso": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }])
    
    df = pd.concat([df, nueva_fila], ignore_index=True)
    save_inventario(df)
    
    df_hist = load_historial()
    nuevo_hist = pd.DataFrame([{
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "tipo_movimiento": "COMPRA",
        "id_residuo": nuevo_id, "tipo_residuo": tipo, "cantidad": float(cantidad),
        "precio_unitario": float(precio_compra), "valor_total": float(cantidad) * float(precio_compra),
        "proveedor_cliente": proveedor
    }])
    df_hist = pd.concat([df_hist, nuevo_hist], ignore_index=True)
    save_historial(df_hist)
    
    return f"✅ Residuo '{tipo}' agregado (ID: {nuevo_id})"

def vender_residuo(id_residuo, cantidad_vendida):
    df = load_inventario()
    if id_residuo not in df["id"].values:
        return f"❌ ID {id_residuo} no encontrado"
    
    idx = df[df["id"] == id_residuo].index[0]
    disponible = df.loc[idx, "cantidad"]
    precio_venta = df.loc[idx, "precio_venta"]
    tipo = df.loc[idx, "tipo_residuo"]
    
    if cantidad_vendida > disponible:
        return f"❌ Stock insuficiente. Disponible: {disponible}"
    
    nueva_cantidad = disponible - cantidad_vendida
    valor_venta = cantidad_vendida * precio_venta
    
    if nueva_cantidad == 0:
        df = df.drop(idx)
        mensaje = f"✅ Venta: {cantidad_vendida} {tipo} | Stock agotado"
    else:
        df.loc[idx, "cantidad"] = nueva_cantidad
        mensaje = f"✅ Venta registrada: {cantidad_vendida} {tipo} | Restante: {nueva_cantidad}"
    
    save_inventario(df.reset_index(drop=True))
    
    df_hist = load_historial()
    nuevo_hist = pd.DataFrame([{
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "tipo_movimiento": "VENTA",
        "id_residuo": id_residuo, "tipo_residuo": tipo, "cantidad": cantidad_vendida,
        "precio_unitario": precio_venta, "valor_total": valor_venta, "proveedor_cliente": "Cliente"
    }])
    df_hist = pd.concat([df_hist, nuevo_hist], ignore_index=True)
    save_historial(df_hist)
    
    return mensaje

def calcular_clasificacion_valor():
    df = load_inventario()
    if df.empty:
        return pd.DataFrame()
    df["valor_rotacion"] = df["cantidad"] * df["precio_venta"]
    df_ordenado = df.sort_values("valor_rotacion", ascending=False).reset_index(drop=True)
    total = df_ordenado["valor_rotacion"].sum()
    if total == 0:
        return pd.DataFrame()
    df_ordenado["porcentaje_acumulado"] = (df_ordenado["valor_rotacion"].cumsum() / total * 100)
    
    def asignar_abc(porc):
        if porc <= 80:
            return "A - Alto valor"
        elif porc <= 95:
            return "B - Medio valor"
        else:
            return "C - Bajo valor"
    
    df_ordenado["clasificacion"] = df_ordenado["porcentaje_acumulado"].apply(asignar_abc)
    return df_ordenado[["id", "tipo_residuo", "cantidad", "precio_venta", "valor_rotacion", "porcentaje_acumulado", "clasificacion"]]

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/recycle-sign.png", width=80)
    st.markdown("## 📊 Método ABC Dual")
    st.caption("💾 Datos guardados en Google Sheets")
    st.caption("🔒 Acceso persistente 24/7")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📦 Gestión Inventario", "💰 Clasificación por Valor", "⚡ Clasificación por Velocidad", "📜 Historial"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("➕ Ingresar Residuo")
        with st.form("ingresar_form"):
            tipo = st.text_input("Tipo de residuo")
            cantidad = st.number_input("Cantidad (kg/unidades)", min_value=0.0, step=1.0)
            precio_compra = st.number_input("Precio compra ($)", min_value=0.0, step=0.1)
            precio_venta = st.number_input("Precio venta ($)", min_value=0.0, step=0.1)
            proveedor = st.text_input("Proveedor")
            if st.form_submit_button("Agregar", type="primary"):
                resultado = agregar_residuo(tipo, cantidad, precio_compra, precio_venta, proveedor)
                st.success(resultado)
                st.rerun()
    
    with col2:
        st.subheader("💸 Registrar Venta")
        with st.form("vender_form"):
            id_venta = st.number_input("ID del residuo", min_value=0, step=1)
            cantidad_vender = st.number_input("Cantidad a vender", min_value=0.0, step=1.0)
            if st.form_submit_button("Vender", type="primary"):
                resultado = vender_residuo(id_venta, cantidad_vender)
                st.success(resultado)
                st.rerun()
    
    st.subheader("📋 Inventario Actual")
    inventario = load_inventario()
    if not inventario.empty:
        st.dataframe(inventario, use_container_width=True)
    else:
        st.info("No hay residuos registrados")

with tab2:
    st.subheader("💰 Clasificación ABC por VALOR")
    if st.button("Actualizar análisis por Valor"):
        df_valor = calcular_clasificacion_valor()
        if not df_valor.empty:
            st.dataframe(df_valor, use_container_width=True)
            
            fig, ax = plt.subplots(figsize=(12, 5))
            colors = ['#ff4444' if 'A' in c else '#ffaa44' if 'B' in c else '#44ff44' for c in df_valor['clasificacion']]
            ax.bar(range(len(df_valor)), df_valor['valor_rotacion'], color=colors, alpha=0.7)
            ax.set_xlabel('Residuos')
            ax.set_ylabel('Valor de rotación ($)')
            ax.set_title('Gráfico de Pareto - Valor de Rotación')
            ax.set_xticks(range(len(df_valor)))
            ax.set_xticklabels(df_valor['tipo_residuo'], rotation=45, ha='right')
            st.pyplot(fig)
        else:
            st.warning("No hay datos suficientes")

with tab3:
    st.subheader("⚡ Clasificación por VELOCIDAD")
    st.info("Esta clasificación se activará después de registrar ventas. La velocidad mide qué tan rápido se vende cada residuo (kg por día).")
    df_hist = load_historial()
    if not df_hist.empty:
        ventas = df_hist[df_hist["tipo_movimiento"] == "VENTA"]
        if not ventas.empty:
            st.dataframe(ventas, use_container_width=True)
        else:
            st.warning("Aún no hay ventas registradas")
    else:
        st.warning("Aún no hay movimientos registrados")

with tab4:
    st.subheader("📜 Historial Completo")
    historial = load_historial()
    if not historial.empty:
        st.dataframe(historial.sort_values("fecha", ascending=False), use_container_width=True)
    else:
        st.info("No hay movimientos registrados")

st.divider()
st.caption("♻️ Sistema de Gestión de Inventario - Reciclaje Velásquez | Clasificación ABC Dual")
