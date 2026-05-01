import streamlit as st
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

st.set_page_config(page_title="Reciclaje Velásquez", page_icon="♻️", layout="wide")

st.title("♻️ RECICLAJE VELÁSQUEZ")
st.markdown("### Sistema de Gestión de Inventario con Clasificación ABC")

# ============================================
# CONEXIÓN A GOOGLE SHEETS
# ============================================

def conectar_google_sheets():
    """Conecta con Google Sheets usando las credenciales de Streamlit secrets"""
    try:
        # Obtener credenciales desde secrets
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # Definir alcance
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        
        # Crear credenciales
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        
        # Conectar a Google Sheets
        client = gspread.authorize(creds)
        
        # Obtener la hoja por URL
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
    
    # Generar nuevo ID
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
    
    # Registrar en historial
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
    
    return f"✅ Residuo '{tipo}' agregado (ID: {nuevo_id}) - Datos guardados permanentemente"

def vender_residuo(id_residuo, cantidad_vendida):
    df = cargar_inventario()
    
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
        mensaje = f"✅ Venta: {cantidad_vendida} {tipo} | Restante: {nueva_cantidad}"
    
    guardar_inventario(df.reset_index(drop=True))
    
    # Registrar en historial
    df_hist = cargar_historial()
    nuevo_hist = pd.DataFrame([{
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tipo_movimiento": "VENTA",
        "id_residuo": id_residuo,
        "tipo_residuo": tipo,
        "cantidad": cantidad_vendida,
        "precio_unitario": precio_venta,
        "valor_total": valor_venta,
        "proveedor_cliente": "Cliente"
    }])
    df_hist = pd.concat([df_hist, nuevo_hist], ignore_index=True)
    guardar_historial(df_hist)
    
    return mensaje

def clasificar_abc():
    df = cargar_inventario()
    if df.empty:
        return pd.DataFrame()
    
    df["valor_rotacion"] = df["cantidad"] * df["precio_venta"]
    df_ordenado = df.sort_values("valor_rotacion", ascending=False).reset_index(drop=True)
    total = df_ordenado["valor_rotacion"].sum()
    
    if total == 0:
        return pd.DataFrame()
    
    df_ordenado["porcentaje_individual"] = (df_ordenado["valor_rotacion"] / total * 100)
    df_ordenado["porcentaje_acumulado"] = df_ordenado["porcentaje_individual"].cumsum()
    
    def asignar_abc(porc):
        if porc <= 80:
            return "A - Alto valor (80%)"
        elif porc <= 95:
            return "B - Medio valor (15%)"
        else:
            return "C - Bajo valor (5%)"
    
    df_ordenado["clasificacion"] = df_ordenado["porcentaje_acumulado"].apply(asignar_abc)
    return df_ordenado

# ============================================
# INTERFAZ DE USUARIO
# ============================================

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/recycle-sign.png", width=80)
    st.markdown("## 📊 Método ABC")
    st.markdown("**Clasificación según valor de rotación:**")
    st.markdown("- **A (80%)**: Alto valor")
    st.markdown("- **B (15%)**: Medio valor")
    st.markdown("- **C (5%)**: Bajo valor")
    st.divider()
    st.caption("💾 **Datos Permanentes**")
    st.caption("Guardados en Google Sheets")
    st.caption("Disponible 24/7 desde cualquier lugar")

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📦 Gestión Inventario", "💰 Clasificación por Valor", "📊 Gráfico Pareto", "📜 Historial", "ℹ️ Ayuda"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("➕ Ingresar Residuo")
        with st.form("ingresar_form"):
            tipo = st.text_input("Tipo de residuo", placeholder="Ej: PET, Cartón, Aluminio")
            cantidad = st.number_input("Cantidad (kg/unidades)", min_value=0.0, step=1.0)
            precio_compra = st.number_input("Precio compra ($)", min_value=0.0, step=0.1)
            precio_venta = st.number_input("Precio venta ($)", min_value=0.0, step=0.1)
            proveedor = st.text_input("Proveedor", placeholder="Nombre del proveedor")
            
            if st.form_submit_button("Agregar al inventario", type="primary"):
                if tipo and cantidad > 0:
                    resultado = agregar_residuo(tipo, cantidad, precio_compra, precio_venta, proveedor)
                    st.success(resultado)
                    st.rerun()
                else:
                    st.error("Complete todos los campos")
    
    with col2:
        st.subheader("💸 Registrar Venta")
        with st.form("vender_form"):
            id_venta = st.number_input("ID del residuo a vender", min_value=0, step=1)
            cantidad_vender = st.number_input("Cantidad a vender", min_value=0.0, step=1.0)
            
            if st.form_submit_button("Registrar venta", type="primary"):
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
        st.info("📭 No hay residuos registrados. ¡Agregue su primer residuo!")

with tab2:
    st.subheader("💰 Clasificación ABC por Valor de Rotación")
    st.markdown("**Fórmula:** Valor de rotación = Cantidad disponible × Precio de venta")
    
    if st.button("🔄 Actualizar clasificación", key="btn_clasificar"):
        df_abc = clasificar_abc()
        if not df_abc.empty:
            df_abc_mostrar = df_abc.copy()
            df_abc_mostrar["precio_venta"] = df_abc_mostrar["precio_venta"].apply(lambda x: f"${x:,.2f}")
            df_abc_mostrar["valor_rotacion"] = df_abc_mostrar["valor_rotacion"].apply(lambda x: f"${x:,.2f}")
            df_abc_mostrar["porcentaje_acumulado"] = df_abc_mostrar["porcentaje_acumulado"].apply(lambda x: f"{x:.1f}%")
            st.dataframe(df_abc_mostrar[["id", "tipo_residuo", "cantidad", "precio_venta", "valor_rotacion", "porcentaje_acumulado", "clasificacion"]], use_container_width=True)
            
            # Resumen por categorías
            st.subheader("📊 Resumen por Categoría")
            resumen = df_abc.groupby("clasificacion").agg({
                "id": "count",
                "valor_rotacion": "sum"
            }).rename(columns={"id": "Cantidad Items", "valor_rotacion": "Valor Total"})
            resumen["Valor Total"] = resumen["Valor Total"].apply(lambda x: f"${x:,.2f}")
            st.dataframe(resumen)
        else:
            st.warning("⚠️ No hay datos suficientes para clasificar. Agregue residuos primero.")

with tab3:
    st.subheader("📊 Gráfico de Pareto")
    
    if st.button("📈 Generar Gráfico", key="btn_grafico"):
        df_abc = clasificar_abc()
        if not df_abc.empty:
            fig, ax = plt.subplots(figsize=(14, 6))
            
            # Colores por categoría
            colors = ['#ff4444' if 'A' in c else '#ffaa44' if 'B' in c else '#44ff44' for c in df_abc['clasificacion']]
            
            # Barras
            bars = ax.bar(range(len(df_abc)), df_abc['valor_rotacion'], color=colors, alpha=0.7)
            ax.set_xlabel('Residuos (ordenados por valor)', fontsize=12)
            ax.set_ylabel('Valor de rotación ($)', fontsize=12, color='blue')
            
            # Línea acumulada
            ax2 = ax.twinx()
            ax2.plot(range(len(df_abc)), df_abc['porcentaje_acumulado'], color='red', marker='o', linewidth=2, label='% Acumulado')
            ax2.set_ylabel('Porcentaje acumulado (%)', fontsize=12, color='red')
            
            # Líneas de referencia
            ax2.axhline(y=80, color='green', linestyle='--', alpha=0.5, label='80%')
            ax2.axhline(y=95, color='orange', linestyle='--', alpha=0.5, label='95%')
            
            # Etiquetas
            ax.set_title('📊 GRÁFICO DE PARETO - CLASIFICACIÓN ABC', fontsize=14, fontweight='bold')
            ax.set_xticks(range(len(df_abc)))
            ax.set_xticklabels([f"{row['id']}: {row['tipo_residuo'][:15]}" for _, row in df_abc.iterrows()], rotation=45, ha='right')
            
            st.pyplot(fig)
            st.caption("🔴 A: Alto valor (80%) | 🟡 B: Medio valor (15%) | 🟢 C: Bajo valor (5%)")
        else:
            st.warning("⚠️ No hay datos suficientes para generar el gráfico")

with tab4:
    st.subheader("📜 Historial Completo de Movimientos")
    historial = cargar_historial()
    if not historial.empty:
        historial_mostrar = historial.copy()
        historial_mostrar["precio_unitario"] = historial_mostrar["precio_unitario"].apply(lambda x: f"${x:,.2f}")
        historial_mostrar["valor_total"] = historial_mostrar["valor_total"].apply(lambda x: f"${x:,.2f}")
        st.dataframe(historial_mostrar.sort_values("fecha", ascending=False), use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            compras = len(historial[historial["tipo_movimiento"] == "COMPRA"])
            st.metric("Total Compras", compras)
        with col2:
            ventas = len(historial[historial["tipo_movimiento"] == "VENTA"])
            st.metric("Total Ventas", ventas)
    else:
        st.info("📭 No hay movimientos registrados")

with tab5:
    st.subheader("ℹ️ Información del Sistema")
    st.markdown("""
    ### 📌 Características del Sistema
    
    - ✅ **Datos Permanentes**: Guardados en Google Sheets
    - ✅ **Acceso 24/7**: Disponible desde cualquier dispositivo
    - ✅ **Clasificación ABC**: Método de Pareto (80/20)
    - ✅ **Gráfico de Pareto**: Visualización automática
    - ✅ **Historial completo**: Registro de todas las operaciones
    
    ### 📊 Método ABC
    
    El sistema clasifica los residuos según su **valor de rotación**:
    
    | Categoría | Porcentaje | Prioridad |
    |-----------|------------|-----------|
    | **A** | 80% del valor | 🔴 Estrategia: Control riguroso |
    | **B** | 15% del valor | 🟡 Estrategia: Control periódico |
    | **C** | 5% del valor | 🟢 Estrategia: Control simple |
    
    ### 💾 Datos en Google Sheets
    
    Todos los datos se guardan permanentemente en tu Google Drive:
    - Hoja `inventario`: Residuos actuales
    - Hoja `historial`: Todos los movimientos
    
    ### 🔗 Acceso
    
    Esta aplicación está disponible 24/7 desde cualquier dispositivo con internet.
    """)

# Footer
st.divider()
st.caption("♻️ **Reciclaje Velásquez** | Sistema de Gestión de Inventario con Clasificación ABC | Datos guardados permanentemente en Google Sheets")
