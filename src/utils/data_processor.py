import pandas as pd
from datetime import datetime

class DataProcessor:
    @staticmethod
    def load_and_clean_data(file_path):
        try:
            xls = pd.ExcelFile(file_path)
            df = pd.read_excel(xls, sheet_name="Informe BBVA")
            
            # Clean the data
            df_cleaned = df.iloc[4:].reset_index(drop=True)
            df_cleaned.columns = ["ID", "F. Valor", "Fecha", "Concepto", "Movimiento", "Importe", "Divisa", "Disponible", "Divisa_2", "Observaciones"]
            
            # Keep only relevant columns and drop NaN values
            df_cleaned = df_cleaned[["Fecha", "Concepto", "Movimiento", "Importe", "Divisa", "Observaciones"]].dropna(subset=["Concepto"])
            
            # Convert date and amount columns
            df_cleaned["Fecha"] = pd.to_datetime(df_cleaned["Fecha"], format="%d/%m/%Y", errors='coerce')
            df_cleaned["Importe"] = pd.to_numeric(df_cleaned["Importe"], errors='coerce')
            
            return df_cleaned
        except Exception as e:
            raise Exception(f"Error loading file: {str(e)}")

    @staticmethod
    def clasificar_transaccion(importe):
        return "Ingreso" if importe > 0 else "Gasto"

    @staticmethod
    def categorizar_transaccion(concepto, movimiento):
        concepto = str(concepto).lower()
        movimiento = str(movimiento).lower() if pd.notna(movimiento) else ""
        
        categorias = {
            "nómina|transferencia recibida": "Ingreso Salarial",
            "pago tarjeta|adeudo mensual de tarjeta|operación financiada con tarjeta|operación financiada": "Tarjeta de Crédito",
            "amortizacion de prestamo|adeudo bmw bank|adeudo cofidis": "Deuda",
            "luz|endesa|energia": "Servicios Públicos",
            "agua": "Servicios Públicos",
            "gas": "Servicios Públicos",
            "supermercado|mercadona|carrefour|carref alameda": "Alimentación",
            "alquiler|hipoteca": "Vivienda",
            "adeudo de zurich|seguro": "Seguros",
            "traspaso programa tu cuenta|traspaso desde cuenta|traspaso a cuenta|traspaso a tarjeta|bizum": "Transferencia",
            "restaurante|bar|cafetería|plaza mayor|casa juan|casa kiki|meson juan gomez|sushi bros|vinoteca pura cepa|catalonia reina victoria|balcon de los montes hote": "Ocio",
            "apple.com/bill|amzn mktp es|amazon.es|samsonite|cursor, ai powered ide|crv*openai *chatgpt": "Compras Online",
            "transporte|uber|taxi|bus|bolt.eu": "Transporte",
            "farmacia": "Farmacia",
            "cafe bar atalaya|bar los cantaores": "Ocio",
            "adeudo o2 fibra": "Internet",
            "decathlon": "Deporte",
            "parking el congreso": "Parking",
            "glovo": "Alimentación Online",
            "peluqueria de caballeros": "Belleza",
            "paypal": "Pago Online",
            "ikea": "Muebles",
            "eess alameda|gasolorgiva|es alameda|plenoil|petroprix|us 270 pizarra": "Gasolina",
            "leroy merlin": "Bricolaje",
        }
        
        for key, value in categorias.items():
            if any(word in concepto or word in movimiento for word in key.split("|")):
                return value
        return "Otros"

    @staticmethod
    def analyze_transactions(df):
        df["Tipo"] = df["Importe"].apply(DataProcessor.clasificar_transaccion)
        df["Categoría"] = df.apply(lambda x: DataProcessor.categorizar_transaccion(x["Concepto"], x["Movimiento"]), axis=1)
        return df

    @staticmethod
    def get_monthly_summary(df):
        monthly_data = df.groupby(df["Fecha"].dt.strftime("%B %Y")).agg({
            "Importe": ["sum", "count"]
        }).reset_index()
        return monthly_data

    @staticmethod
    def get_category_summary(df):
        category_data = df.groupby("Categoría").agg({
            "Importe": ["sum", "count"]
        }).reset_index()
        return category_data 