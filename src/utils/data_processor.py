"""Data processing utilities for bank transaction analysis."""
import pandas as pd
from pathlib import Path

from utils.validators import validate_excel_file_path, validate_dataframe_columns
from utils.logger import setup_logger

# Setup logger for this module
logger = setup_logger(__name__)


class DataProcessingError(Exception):
    """Raised when data processing fails."""
    pass


class DataProcessor:
    """Process and analyze bank transaction data from Excel files."""

    @staticmethod
    def load_and_clean_data(file_path):
        """Load and clean bank transaction data from Excel file.

        Args:
            file_path: Path to the Excel file

        Returns:
            Cleaned pandas DataFrame with transaction data

        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file is not accessible
            FileValidationError: If file validation fails
            DataProcessingError: If data processing fails
        """
        logger.info(f"Loading file: {file_path}")

        # Critical Security Fix #1: Validate file path to prevent path traversal
        try:
            validated_path = validate_excel_file_path(file_path)
        except FileNotFoundError as e:
            logger.error(f"File not found: {file_path}")
            raise
        except PermissionError as e:
            logger.error(f"Permission denied: {file_path}")
            raise
        except Exception as e:
            logger.error(f"File validation failed: {e}")
            raise

        # Critical Security Fix #2: Specific exception handling instead of generic
        try:
            xls = pd.ExcelFile(validated_path)
        except pd.errors.ParserError as e:
            logger.error(f"Invalid Excel file format: {e}")
            raise DataProcessingError(f"Invalid Excel file format: {e}")
        except ValueError as e:
            logger.error(f"Error reading Excel file: {e}")
            raise DataProcessingError(f"Error reading Excel file: {e}")

        # Read specific sheet
        try:
            df = pd.read_excel(xls, sheet_name="Informe BBVA")
        except ValueError as e:
            logger.error(f"Sheet 'Informe BBVA' not found in file")
            raise DataProcessingError(
                "Excel file must contain a sheet named 'Informe BBVA'. "
                "Please ensure you're using a valid BBVA bank export."
            )

        # Clean the data - detect format and column count
        try:
            # Skip first 4 rows (header rows)
            df_cleaned = df.iloc[4:].reset_index(drop=True)

            # Detect number of columns
            num_cols = len(df_cleaned.columns)
            logger.info(f"Detected {num_cols} columns in data")

            # Check row 3 for headers to identify file type and language
            header_row = df.iloc[3] if len(df) > 3 else None
            is_credit_card = False
            is_english_format = False
            if header_row is not None:
                header_text = ' '.join([str(v).lower() for v in header_row.values])
                is_credit_card = 'card' in header_text and 'card payment' not in header_text
                # Detect English format by checking for English headers
                is_english_format = 'eff. date' in header_text or 'item' in header_text

            # Assign column names based on file type and column count
            if num_cols == 9 and is_english_format:
                # English format: Eff. Date, Date, Item, Transaction, Amount, Foreign currency, Available, Foreign currency, Comments
                logger.info("Detected: English format BBVA export (9 columns)")
                df_cleaned.columns = [
                    "F_Efectiva", "Fecha", "Concepto", "Movimiento",
                    "Importe", "Divisa", "Disponible", "Divisa_2", "Observaciones"
                ]
                # Keep only relevant columns
                df_cleaned = df_cleaned[[
                    "Fecha", "Concepto", "Movimiento", "Importe", "Divisa", "Observaciones"
                ]]

            elif num_cols == 10:
                # Bank account transactions (10 columns)
                logger.info("Detected: Bank account transactions (10 columns)")
                df_cleaned.columns = [
                    "ID", "F_Valor", "Fecha", "Concepto", "Movimiento",
                    "Importe", "Divisa", "Disponible", "Divisa_2", "Observaciones"
                ]
                # Keep only relevant columns
                df_cleaned = df_cleaned[[
                    "Fecha", "Concepto", "Movimiento", "Importe", "Divisa", "Observaciones"
                ]]

            elif num_cols == 6 and is_credit_card:
                # Credit card transactions (6 columns)
                logger.info("Detected: Credit card transactions (6 columns)")
                df_cleaned.columns = [
                    "ID", "Fecha", "Tarjeta", "Concepto", "Importe", "Divisa"
                ]
                # Add empty columns to match expected structure
                df_cleaned["Movimiento"] = "Card payment"  # Mark as card payment
                df_cleaned["Observaciones"] = df_cleaned["Tarjeta"]  # Store card number
                # Reorder to match expected structure
                df_cleaned = df_cleaned[[
                    "Fecha", "Concepto", "Movimiento", "Importe", "Divisa", "Observaciones"
                ]]

            elif num_cols == 6:
                # Bank account transactions (already filtered to 6 columns)
                logger.info("Detected: Bank account transactions (6 columns)")
                df_cleaned.columns = [
                    "Fecha", "Concepto", "Movimiento", "Importe", "Divisa", "Observaciones"
                ]

            else:
                # Unknown format
                raise DataProcessingError(
                    f"Unexpected file format with {num_cols} columns. "
                    f"Expected 10 (bank account) or 6 (credit card/simplified)."
                )

            # Drop rows with empty Concepto
            df_cleaned = df_cleaned.dropna(subset=["Concepto"])

            # Convert date column - try both DD/MM/YYYY and MM/DD/YYYY formats
            # Store original date values for retry
            fecha_original = df_cleaned["Fecha"].copy()

            # First try DD/MM/YYYY (Spanish format)
            df_cleaned["Fecha"] = pd.to_datetime(
                fecha_original,
                format="%d/%m/%Y",
                errors='coerce'
            )

            # If many dates failed, try MM/DD/YYYY (English format)
            failed_count = df_cleaned["Fecha"].isna().sum()
            if failed_count > len(df_cleaned) * 0.5:
                logger.info(f"DD/MM/YYYY failed for {failed_count} rows, trying MM/DD/YYYY format (English)")
                df_cleaned["Fecha"] = pd.to_datetime(
                    fecha_original,
                    format="%m/%d/%Y",
                    errors='coerce'
                )
            df_cleaned["Importe"] = pd.to_numeric(
                df_cleaned["Importe"],
                errors='coerce'
            )

            # Validate we have data after cleaning
            if df_cleaned.empty:
                raise DataProcessingError(
                    "No valid transaction data found in file. "
                    "Please check the file format."
                )

            # Drop rows with invalid dates or amounts
            initial_count = len(df_cleaned)
            df_cleaned = df_cleaned.dropna(subset=["Fecha", "Importe"])
            dropped = initial_count - len(df_cleaned)

            if dropped > 0:
                logger.warning(
                    f"Dropped {dropped} rows with invalid dates or amounts"
                )

            logger.info(
                f"Successfully loaded {len(df_cleaned)} transactions from {validated_path.name}"
            )

            return df_cleaned

        except KeyError as e:
            logger.error(f"Missing expected column in Excel file: {e}")
            raise DataProcessingError(
                f"Excel file structure is invalid. Missing column: {e}"
            )
        except Exception as e:
            logger.error(f"Unexpected error during data cleaning: {e}", exc_info=True)
            raise DataProcessingError(f"Failed to process data: {e}")

    @staticmethod
    def clasificar_transaccion(importe):
        """Classify transaction as income or expense based on amount.

        Args:
            importe: Transaction amount (positive for income, negative for expense)

        Returns:
            str: "Ingreso" for income, "Gasto" for expense
        """
        return "Ingreso" if importe > 0 else "Gasto"

    @staticmethod
    def categorizar_transaccion(concepto, movimiento, importe=None):
        """Categorize transaction based on concept and movement description.

        Args:
            concepto: Transaction concept/description
            movimiento: Transaction movement type
            importe: Transaction amount (to detect returns - positive amounts at stores)

        Returns:
            str: Category name
        """
        concepto = str(concepto).lower()
        movimiento = str(movimiento).lower() if pd.notna(movimiento) else ""

        # Combine both for matching
        text = f"{concepto} {movimiento}"

        # Check if this is a return (positive amount at a store)
        is_return = False
        if importe is not None and importe > 0:
            # Stores that typically have negative amounts (expenses)
            store_keywords = [
                "decathlon", "amazon", "mercadona", "carrefour", "ikea",
                "leroy merlin", "apple", "card payment", "pago con tarjeta"
            ]
            if any(keyword in text for keyword in store_keywords):
                is_return = True

        # CRITICAL: Order matters! Most specific rules first
        categorias = {
            # === CREDIT CARD PAYMENTS (Not expenses - just moving money) ===
            "transfer to card|traspaso a tarjeta|pago tarjeta|adeudo mensual de tarjeta": "💳 Pago Tarjeta Crédito",

            # === INCOME ===
            "transfer received|transferencia recibida|nómina|nomina|salary|payroll": "💰 Ingreso",

            # === DEBT PAYMENTS ===
            "amortizacion de prestamo|loan payment|adeudo bmw bank|adeudo cofidis|préstamo|prestamo": "📊 Pago Deuda",

            # === INTERNAL TRANSFERS (Not real expenses) ===
            "transfer - set up your account|traspaso programa tu cuenta|traspaso desde cuenta|traspaso a cuenta|trp redondeo": "🔄 Transferencia Interna",

            # === BIZUM & PERSON-TO-PERSON ===
            "bizum": "👥 Bizum",

            # === HOUSING ===
            "alquiler|rent|hipoteca|mortgage": "🏠 Vivienda",

            # === UTILITIES ===
            "luz|electricity|endesa|energia|energy": "⚡ Electricidad",
            "agua|water": "💧 Agua",
            "gas": "🔥 Gas",
            "adeudo o2 fibra|internet|wifi|fibra": "🌐 Internet",

            # === INSURANCE ===
            "adeudo de zurich|seguro|insurance": "🛡️ Seguros",

            # === FOOD & GROCERIES ===
            "supermercado|mercadona|carrefour|carref alameda|supermarket|grocery": "🛒 Supermercado",
            "glovo|uber eats|deliveroo|just eat": "🍔 Comida a Domicilio",

            # === RESTAURANTS & LEISURE ===
            "restaurante|restaurant|bar|cafetería|cafe|plaza mayor|casa juan|casa kiki|meson juan gomez|sushi bros|vinoteca pura cepa|catalonia reina victoria|balcon de los montes": "🍽️ Restaurantes y Ocio",

            # === SHOPPING ===
            "decathlon": "⚽ Deporte",
            "apple.com/bill|apple|cursor, ai powered ide|crv*openai|chatgpt|software|subscription": "💻 Software y Suscripciones",
            "amzn mktp es|amazon.es|amazon": "📦 Amazon",
            "ikea": "🛋️ Muebles",
            "leroy merlin|bricolaje|hardware": "🔧 Bricolaje",
            "samsonite|clothing|ropa|fashion": "👔 Ropa y Accesorios",

            # === TRANSPORT ===
            "gasolina|eess alameda|gasolorgiva|es alameda|plenoil|petroprix|us 270 pizarra|gas station|fuel": "⛽ Gasolina",
            "parking el congreso|parking|aparcamiento": "🅿️ Parking",
            "uber|taxi|cabify|bolt.eu|transport": "🚕 Taxi/Uber",
            "transporte|bus|metro|train|tren": "🚌 Transporte Público",

            # === HEALTH & WELLNESS ===
            "farmacia|pharmacy": "💊 Farmacia",
            "peluqueria de caballeros|peluqueria|hairdresser|barbershop": "💇 Peluquería",

            # === ONLINE PAYMENTS ===
            "paypal": "💳 PayPal",

            # === CARD PAYMENTS (Generic - catch-all for unclassified) ===
            "card payment|pago con tarjeta": "💳 Pago con Tarjeta",
        }

        # Find matching category
        matched_category = None
        for key, value in categorias.items():
            patterns = key.split("|")
            if any(pattern.strip() in text for pattern in patterns):
                matched_category = value
                break

        if matched_category is None:
            matched_category = "❓ Otros"

        # If it's a return, prefix with return indicator
        if is_return:
            return f"↩️ Devolución - {matched_category}"

        return matched_category

    @staticmethod
    def analyze_transactions(df, categorization_service=None):
        """Analyze transactions by adding type and category columns.

        Args:
            df: DataFrame with transaction data
            categorization_service: Optional CategorizationService instance for AI categorization

        Returns:
            DataFrame with added 'Tipo', 'Categoría', and AI metadata columns

        Raises:
            ValueError: If required columns are missing
        """
        # Validate required columns exist
        required_cols = ["Importe", "Concepto", "Movimiento"]
        validate_dataframe_columns(df, required_cols)

        logger.info(f"Analyzing {len(df)} transactions")

        # Add transaction type (income/expense)
        df["Tipo"] = df["Importe"].apply(DataProcessor.clasificar_transaccion)

        # Categorize using service if available, otherwise use legacy method
        if categorization_service:
            logger.info("Using AI-enhanced categorization service")

            # Apply categorization to each transaction
            results = []
            for _, row in df.iterrows():
                result = categorization_service.categorize_transaction(
                    row["Concepto"],
                    row["Movimiento"]
                )
                results.append(result)

            # Add results to dataframe
            df["Categoría"] = [r['category'] for r in results]
            df["AI_Confidence"] = [r['confidence'] for r in results]
            df["Categorization_Method"] = [r['method'] for r in results]

            # Log statistics
            methods = pd.Series([r['method'] for r in results]).value_counts()
            logger.info(f"Categorization methods: {methods.to_dict()}")

        else:
            logger.info("Using legacy keyword-based categorization")
            df["Categoría"] = df.apply(
                lambda x: DataProcessor.categorizar_transaccion(
                    x["Concepto"],
                    x["Movimiento"],
                    x["Importe"]  # Pass amount to detect returns
                ),
                axis=1
            )
            df["AI_Confidence"] = None
            df["Categorization_Method"] = 'keyword'

        logger.info("Transaction analysis complete")
        return df

    @staticmethod
    def get_monthly_summary(df):
        """Generate monthly summary of transactions.

        Args:
            df: DataFrame with transaction data

        Returns:
            DataFrame with monthly aggregated data

        Raises:
            ValueError: If required columns are missing
        """
        validate_dataframe_columns(df, ["Fecha", "Importe"])

        monthly_data = df.groupby(df["Fecha"].dt.strftime("%B %Y")).agg({
            "Importe": ["sum", "count"]
        }).reset_index()
        return monthly_data

    @staticmethod
    def get_category_summary(df):
        """Generate category summary of transactions.

        Args:
            df: DataFrame with transaction data

        Returns:
            DataFrame with category aggregated data

        Raises:
            ValueError: If required columns are missing
        """
        validate_dataframe_columns(df, ["Categoría", "Importe"])

        category_data = df.groupby("Categoría").agg({
            "Importe": ["sum", "count"]
        }).reset_index()
        return category_data
