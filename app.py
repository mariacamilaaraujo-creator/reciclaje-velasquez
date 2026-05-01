import streamlit as st
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt

st.set_page_config(page_title="Reciclaje Velásquez", page_icon="♻️", layout="wide")

st.title("♻️ RECICLAJE VELÁSQUEZ")
st.markdown("### Sistema de Gestión de Inventario")

# Inicializar datos en session_state (para guardar temporalmente)
if 'inventario' not in st.session_state:
    st.session_state.inventario = pd.DataFrame(columns=[
        "id", "tipo_residuo", "cantidad", "precio_compra", "precio_venta", "proveedor", "fecha_ingreso"
    ])

if 'historial' not in st.session_state:
    st.session_state.historial = pd.DataFrame(columns=[
        "fecha", "tipo_movimiento", "id_residuo", "tipo_residuo", "cantidad", "precio_unitario", "valor_total"
    ])

# Funciones
def agregar_residuo(tipo, cantidad, precio_compra, precio_venta, proveedor):
    if not tipo or cantidad <= 0:
        return "❌ Complete todos los campos"
    
    nuevo_id = len(st.session_state.inventario) + 1
    
    nueva_fila = pd.DataFrame([{
        "id": nuevo_id, "tipo_residuo": tipo, "cantidad": float(cantidad),
        "precio_compra": float(precio_compra), "precio_venta": float(precio_venta),
        "proveedor": proveedor, "fecha_ingreso": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }])
    
    st.session_state.inventario = pd.concat([st.session_state.inventario, nueva_fila], ignore_index=True)
    
    nuevo_hist = pd.DataFrame([{
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "tipo_movimiento": "COMPRA",
        "id_residuo": nuevo_id, "tipo_residuo": tipo, "cantidad": float(cantidad),
        "precio_unitario": float(precio_compra), "valor_total": float(cantidad) * float(precio_compra)
    }])
    st.session_state.historial = pd.concat([st.session_state.historial, nuevo_hist], ignore_index=True)
    
    return f"✅ Residuo '{tipo}' agregado (ID: {nuevo_id})"

def vender_residuo(id_residuo, cantidad_vendida):
    df = st.session_state.inventario
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
        st.session_state.inventario = df.drop(idx).reset_index(drop=True)
        mensaje = f"✅ Venta: {cantidad_vendida} {tipo} | Stock agotado"
    else:
        df.loc[idx, "cantidad"] = nueva_cantidad
        st.session_state.inventario = df
        mensaje = f"✅ Venta: {cantidad_vendida} {tipo} | Restante: {nueva_cantidad}"
    
    nuevo_hist = pd.DataFrame([{
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "tipo_movimiento": "VENTA",
        "id_residuo": id_residuo, "tipo_residuo": tipo, "cantidad": cantidad_vendida,
        "precio_unitario": precio_venta, "valor_total": valor_venta
    }])
    st.session_state.historial = pd.concat([st.session_state.historial, nuevo_hist], ignore_index=True)
    
    return mensaje

def clasificar_abc():
    df = st.session_state.inventario
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
    return df_ordenado

# Sidebar
with st.sidebar:
    st.markdown("## 📊 Método ABC")
    st.caption("Clasificación por valor de rotación")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📦 Inventario", "💰 Clasificación ABC", "📊 Gráfico", "📜 Historial"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("➕ Ingresar Residuo")
        with st.form("ingresar"):
            tipo = st.text_input("Tipo de residuo")
            cantidad = st.number_input("Cantidad", min_value=0.0, step=1.0)
            precio_compra = st.number_input("Precio compra ($)", min_value=0.0, step=0.1)
            precio_venta = st.number_input("Precio venta ($)", min_value=0.0, step=0.1)
            proveedor = st.text_input("Proveedor")
            if st.form_submit_button("Agregar"):
                resultado = agregar_residuo(tipo, cantidad, precio_compra, precio_venta, proveedor)
                st.success(resultado)
                st.rerun()
    
    with col2:
        st.subheader("💸 Vender")
        with st.form("vender"):
            id_venta = st.number_input("ID del residuo", min_value=0, step=1)
            cantidad_vender = st.number_input("Cantidad a vender", min_value=0.0, step=1.0)
            if st.form_submit_button("Vender"):
                resultado = vender_residuo(id_venta, cantidad_vender)
                st.success(resultado)
                st.rerun()
    
    st.subheader("📋 Inventario Actual")
    if not st.session_state.inventario.empty:
        st.dataframe(st.session_state.inventario, use_container_width=True)
    else:
        st.info("No hay residuos registrados")

with tab2:
    st.subheader("💰 Clasificación ABC")
    if st.button("Actualizar"):
        df_abc = clasificar_abc()
        if not df_abc.empty:
            st.dataframe(df_abc[["id", "tipo_residuo", "cantidad", "precio_venta", "valor_rotacion", "porcentaje_acumulado", "clasificacion"]], use_container_width=True)
        else:
            st.warning("Agregue residuos primero")

with tab3:
    st.subheader("📊 Gráfico de Pareto")
    if st.button("Generar Gráfico"):
        df_abc = clasificar_abc()
        if not df_abc.empty:
            fig, ax = plt.subplots(figsize=(12, 5))
            colors = ['#ff4444' if 'A' in c else '#ffaa44' if 'B' in c else '#44ff44' for c in df_abc['clasificacion']]
            ax.bar(range(len(df_abc)), df_abc['valor_rotacion'], color=colors)
            ax.set_xlabel('Residuos')
            ax.set_ylabel('Valor de rotación ($)')
            ax.set_title('Gráfico de Pareto')
            ax.set_xticks(range(len(df_abc)))
            ax.set_xticklabels(df_abc['tipo_residuo'], rotation=45, ha='right')
            st.pyplot(fig)
        else:
            st.warning("No hay datos")

with tab4:
    st.subheader("📜 Historial")
    if not st.session_state.historial.empty:
        st.dataframe(st.session_state.historial.sort_values("fecha", ascending=False), use_container_width=True)
    else:
        st.info("No hay movimientos")

st.divider()
st.caption("⚠️ NOTA: Los datos se pierden al cerrar la aplicación. Versión DEMO.")
