import os
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, session
from werkzeug.utils import secure_filename
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime
import tempfile
import shutil
import re
import traceback

# Import data processor
from src.utils.data_processor import DataProcessor

# Create Flask app
app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
            static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'))
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['CHARTS_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'charts')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Ensure upload and charts directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['CHARTS_FOLDER'], exist_ok=True)

# Global variables
global_df = None
loaded_files = []

# Add custom filters
@app.template_filter('format_currency')
def format_currency(value):
    """Format a number as currency (€)"""
    if value is None:
        return "0,00 €"
    return f"{value:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

# Add context processor for current date
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.route('/')
def index():
    """Main page with file upload and analysis options"""
    return render_template('index.html', files=loaded_files)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload"""
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    files = request.files.getlist('file')
    
    if not files or files[0].filename == '':
        flash('No selected file')
        return redirect(request.url)
    
    for file in files:
        if file and file.filename.endswith(('.xlsx', '.xls')):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            if file_path not in loaded_files:
                loaded_files.append(file_path)
                flash(f'File {filename} uploaded successfully')
        else:
            flash(f'Invalid file format for {file.filename}. Only Excel files are allowed.')
    
    return redirect(url_for('index'))

@app.route('/remove/<filename>')
def remove_file(filename):
    """Remove a file from the loaded files list"""
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
    
    if file_path in loaded_files:
        loaded_files.remove(file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
        flash(f'File {filename} removed')
    
    return redirect(url_for('index'))

@app.route('/analyze')
def analyze():
    global global_df
    
    if not loaded_files:
        flash("Por favor, carga y procesa archivos primero.", "warning")
        return redirect(url_for('index'))
    
    if global_df is None:
        try:
            # List to store DataFrames from each file
            dfs = []
            
            for file in loaded_files:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file)
                print(f"Processing file: {file}")
                
                # Try different approaches to read the Excel file
                try:
                    # First attempt: Try to find the header row by looking for specific column names
                    found_header = False
                    
                    # For BBVA statements, the header is typically at row 8
                    try:
                        df = pd.read_excel(file_path, skiprows=8)
                        print(f"Reading with skiprows=8")
                        
                        # Check if this looks like a proper table with F.Valor, Fecha, Concepto, etc.
                        if any('fecha' in str(col).lower() for col in df.columns) or any('valor' in str(col).lower() for col in df.columns):
                            print(f"Found header at skiprows=8")
                            found_header = True
                        else:
                            # Try with a different skiprows value
                            for skip_rows in [9, 10, 11]:
                                try:
                                    df = pd.read_excel(file_path, skiprows=skip_rows)
                                    print(f"Trying with skiprows={skip_rows}")
                                    
                                    # Check if this looks like a proper table
                                    if any('fecha' in str(col).lower() for col in df.columns) or any('valor' in str(col).lower() for col in df.columns):
                                        print(f"Found header at skiprows={skip_rows}")
                                        found_header = True
                                        break
                                except Exception as e:
                                    print(f"Error with skiprows={skip_rows}: {e}")
                    except Exception as e:
                        print(f"Error with skiprows=8: {e}")
                    
                    if not found_header:
                        # Try to find the actual data by looking for rows with date patterns
                        for skip_rows in range(5, 15):
                            try:
                                temp_df = pd.read_excel(file_path, skiprows=skip_rows, nrows=5)
                                
                                # Check if any cell in the first few rows contains a date pattern
                                date_pattern = r'\d{2}/\d{2}/\d{4}'
                                date_found = False
                                
                                for col in temp_df.columns:
                                    sample = temp_df[col].astype(str).tolist()
                                    if any(re.match(date_pattern, str(val)) for val in sample):
                                        date_found = True
                                        break
                                
                                if date_found:
                                    print(f"Found data rows at skiprows={skip_rows}")
                                    df = pd.read_excel(file_path, skiprows=skip_rows)
                                    found_header = True
                                    break
                            except Exception as e:
                                print(f"Error checking row {skip_rows}: {e}")
                    
                    # Print column names for debugging
                    print(f"Columns in {file}: {df.columns.tolist()}")
                    
                except Exception as e:
                    print(f"Error with standard approaches: {e}")
                    # Fallback: Try to read with header=None and assign column names later
                    try:
                        df = pd.read_excel(file_path, header=None)
                        print(f"Reading with header=None. Columns: {df.columns.tolist()}")
                    except Exception as e2:
                        print(f"Failed to read file even with header=None: {e2}")
                        continue  # Skip this file
                
                # Map columns based on content patterns
                column_mapping = {}
                
                # For BBVA statements, we know the typical column structure
                # Try to identify columns based on their position and content
                if len(df.columns) >= 9:  # BBVA statements typically have at least 9 columns
                    # Check if this looks like a BBVA statement based on column content
                    bbva_format = False
                    
                    # Sample some rows to check for typical BBVA content
                    sample_rows = min(5, len(df))
                    for i in range(sample_rows):
                        row_values = df.iloc[i].astype(str).tolist()
                        # Check for typical BBVA transaction types
                        bbva_keywords = ['transferencia', 'bizum', 'traspaso', 'tarjeta', 'recibo', 'comisión']
                        if any(any(keyword in str(val).lower() for keyword in bbva_keywords) for val in row_values):
                            bbva_format = True
                            break
                    
                    if bbva_format:
                        print("Detected BBVA statement format")
                        # BBVA format typically has:
                        # F.Valor at index 0 or 1
                        # Fecha at index 1 or 2
                        # Concepto at index 2 or 3
                        # Importe at index 4 or 5
                        
                        # Try to map columns based on typical BBVA positions
                        if len(df.columns) > 1:
                            column_mapping[df.columns[1]] = 'F.Valor'
                        if len(df.columns) > 2:
                            column_mapping[df.columns[2]] = 'Fecha'
                        if len(df.columns) > 3:
                            column_mapping[df.columns[3]] = 'Concepto'
                        if len(df.columns) > 5:
                            column_mapping[df.columns[5]] = 'Importe'
                
                # If we didn't identify as BBVA format, try the general approach
                if not column_mapping:
                    # First, check if we have a row that looks like a header
                    if len(df) > 0:
                        first_row = df.iloc[0].astype(str).tolist()
                        header_keywords = {
                            'Fecha': ['fecha', 'date', 'f.valor'],
                            'Concepto': ['concepto', 'description', 'descripción', 'concept'],
                            'Importe': ['importe', 'amount', 'cantidad', 'valor'],
                            'Categoría': ['categoría', 'category', 'tipo']
                        }
                        
                        # Check if first row contains header-like values
                        header_found = False
                        for i, val in enumerate(first_row):
                            for col_name, keywords in header_keywords.items():
                                if any(keyword in str(val).lower() for keyword in keywords):
                                    column_mapping[df.columns[i]] = col_name
                                    header_found = True
                        
                        # If first row looks like a header, use it and skip that row
                        if header_found and len(column_mapping) >= 2:
                            print("First row appears to be a header, using it for column mapping")
                            df = df.rename(columns=column_mapping)
                            df = df.iloc[1:].reset_index(drop=True)
                            # Reset column_mapping since we've already applied it
                            column_mapping = {}
                
                # If we didn't find a header row, try to identify columns by content
                if not column_mapping or len(column_mapping) < 2:
                    # Try to identify columns by their content
                    for col in df.columns:
                        # Sample some values to determine column type
                        sample = df[col].dropna().astype(str).tolist()[:10]
                        
                        if not sample:
                            continue
                        
                        # Check for date patterns
                        date_pattern = r'\d{2}/\d{2}/\d{4}'
                        date_matches = [re.match(date_pattern, str(val)) for val in sample]
                        date_match_count = sum(1 for m in date_matches if m)
                        
                        if date_match_count >= 3:  # If at least 3 values match date pattern
                            if 'Fecha' not in column_mapping:
                                column_mapping[col] = 'Fecha'
                                print(f"Column {col} identified as Fecha based on content")
                            elif 'F.Valor' not in column_mapping:
                                column_mapping[col] = 'F.Valor'
                                print(f"Column {col} identified as F.Valor based on content")
                        
                        # Check for monetary values
                        money_pattern = r'^-?\d+(\.\d+)?$'
                        money_matches = [re.match(money_pattern, str(val).strip()) for val in sample]
                        money_match_count = sum(1 for m in money_matches if m)
                        
                        if money_match_count >= 3:  # If at least 3 values match money pattern
                            # Check if values are mostly negative (expenses) or mixed (likely amounts)
                            numeric_values = pd.to_numeric(df[col], errors='coerce')
                            if not numeric_values.isna().all():
                                neg_count = (numeric_values < 0).sum()
                                pos_count = (numeric_values > 0).sum()
                                
                                if (neg_count > 0 or pos_count > 0) and 'Importe' not in column_mapping:
                                    column_mapping[col] = 'Importe'
                                    print(f"Column {col} identified as Importe based on content")
                        
                        # Check for concept descriptions
                        if any(len(str(val)) > 10 for val in sample) and 'Concepto' not in column_mapping:
                            column_mapping[col] = 'Concepto'
                            print(f"Column {col} identified as Concepto based on content")
                
                # If we still couldn't identify columns by content, try by position
                if 'Fecha' not in column_mapping.values():
                    # Try to find date columns by position
                    date_positions = [1, 2]  # Common positions for date columns
                    for pos in date_positions:
                        if pos < len(df.columns):
                            column_mapping[df.columns[pos]] = 'Fecha'
                            print(f"Using column {df.columns[pos]} as Fecha based on position")
                            break
                
                if 'Importe' not in column_mapping.values():
                    # Try to find amount columns by position
                    amount_positions = [4, 5]  # Common positions for amount columns
                    for pos in amount_positions:
                        if pos < len(df.columns):
                            column_mapping[df.columns[pos]] = 'Importe'
                            print(f"Using column {df.columns[pos]} as Importe based on position")
                            break
                
                if 'Concepto' not in column_mapping.values():
                    # Try to find concept columns by position
                    concept_positions = [3, 2]  # Common positions for concept columns
                    for pos in concept_positions:
                        if pos < len(df.columns):
                            column_mapping[df.columns[pos]] = 'Concepto'
                            print(f"Using column {df.columns[pos]} as Concepto based on position")
                            break
                
                # Rename columns based on our mapping
                df = df.rename(columns=column_mapping)
                print(f"Columns after mapping: {df.columns.tolist()}")
                
                # Check for duplicate column names and make them unique
                if df.columns.duplicated().any():
                    print("Found duplicate column names, making them unique")
                    # Create a dictionary to track column name occurrences
                    col_counts = {}
                    new_columns = []
                    
                    for col in df.columns:
                        if col in col_counts:
                            col_counts[col] += 1
                            new_columns.append(f"{col}_{col_counts[col]}")
                        else:
                            col_counts[col] = 0
                            new_columns.append(col)
                    
                    df.columns = new_columns
                    print(f"Columns after making unique: {df.columns.tolist()}")
                
                # For any remaining columns we need but couldn't identify, create them
                if 'Categoría' not in df.columns:
                    if 'Concepto' in df.columns:
                        df['Categoría'] = df['Concepto'].astype(str)
                    else:
                        df['Categoría'] = "Sin categoría"
                
                print(f"Final columns after mapping: {df.columns.tolist()}")
                
                # Convert Importe to numeric if it exists
                if 'Importe' in df.columns:
                    df['Importe'] = pd.to_numeric(df['Importe'], errors='coerce')
                
                # Convert Fecha to datetime if it exists
                if 'Fecha' in df.columns:
                    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce', format='%d/%m/%Y')
                
                dfs.append(df)
            
            # Combine all DataFrames
            if dfs:
                global_df = pd.concat(dfs, ignore_index=True)
                
                # Final check and cleanup
                if 'Importe' not in global_df.columns:
                    # Try to find a numeric column that could be the amount
                    numeric_cols = global_df.select_dtypes(include=['number']).columns
                    if numeric_cols.any():
                        global_df['Importe'] = global_df[numeric_cols[0]]
                        print(f"Columna \"Importe\" no encontrada. Usando \"{numeric_cols[0]}\" como importe.")
                
                if 'Fecha' not in global_df.columns:
                    print("No se pudo identificar una columna para las fechas.")
                    # Try to create a date column from the filename or current date
                    global_df['Fecha'] = pd.Timestamp.now()
                
                # Sort by date
                if 'Fecha' in global_df.columns:
                    global_df = global_df.sort_values(by='Fecha', ascending=False)
                
                # Create charts
                create_charts(global_df)
                
                flash("Archivos procesados correctamente.", "success")
            else:
                flash("No se pudieron procesar los archivos.", "danger")
                return redirect(url_for('index'))
                
        except Exception as e:
            flash(f"Error al procesar los archivos: {str(e)}", "danger")
            print(f"Error processing files: {str(e)}")
            traceback.print_exc()
            return redirect(url_for('index'))
    
    # Create charts
    create_charts(global_df)
    
    # Calculate summary statistics
    income = 0
    expenses = 0
    balance = 0
    
    if 'Importe' in global_df.columns:
        # Use Concepto as Categoría if Categoría doesn't exist
        category_col = 'Categoría' if 'Categoría' in global_df.columns else 'Concepto'
        
        # Create a copy of the dataframe for calculations
        calc_df = global_df.copy()
        
        # Exclude transfers between accounts
        if category_col in calc_df.columns:
            excluded_categories = ['Traspaso a cuenta', 'Traspaso desde cuenta']
            calc_df = calc_df[~calc_df[category_col].isin(excluded_categories)]
        
        # Calculate income (positive amounts)
        income = calc_df[calc_df['Importe'] > 0]['Importe'].sum()
        
        # Calculate expenses (negative amounts)
        expenses = abs(calc_df[calc_df['Importe'] < 0]['Importe'].sum())
        
        # Calculate balance
        balance = income - expenses
    
    # Format for display
    summary = {
        'income': format_currency(income),
        'expenses': format_currency(expenses),
        'balance': format_currency(balance)
    }
    
    # Get category data for the pie chart
    category_data = get_category_data(global_df)
    
    # Get available months for filtering
    available_months = []
    if 'Fecha' in global_df.columns and not global_df['Fecha'].isna().all():
        months = global_df['Fecha'].dt.strftime('%Y-%m').unique()
        for month in sorted(months, reverse=True):
            year, month_num = month.split('-')
            month_name = {
                '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
                '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
                '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
            }.get(month_num, month_num)
            available_months.append({'value': month, 'name': f"{month_name} {year}"})
    
    # Get transactions (limit to 100 for performance)
    transactions = []
    if global_df is not None and not global_df.empty:
        # Select only relevant columns for display
        display_cols = ['Fecha', 'Concepto', 'Importe', 'Categoría']
        # Filter to only include columns that exist
        display_cols = [col for col in display_cols if col in global_df.columns]
        
        if display_cols:
            transactions_df = global_df[display_cols].head(100)
            transactions = transactions_df.to_dict('records')
            
            # Format dates for display
            for transaction in transactions:
                if 'Fecha' in transaction and pd.notna(transaction['Fecha']):
                    if isinstance(transaction['Fecha'], pd.Timestamp):
                        transaction['Fecha'] = transaction['Fecha'].strftime('%d/%m/%Y')
    
    return render_template('results.html', 
                          summary=summary, 
                          category_data=category_data,
                          transactions=transactions,
                          available_months=available_months)

@app.route('/filter_data', methods=['POST'])
def filter_data():
    global global_df
    
    if global_df is None:
        flash('Por favor, analiza primero un archivo.', 'warning')
        return redirect(url_for('index'))
    
    # Get filter parameters
    month = request.form.get('month', 'all')
    start_date = request.form.get('start_date', '')
    end_date = request.form.get('end_date', '')
    category = request.form.get('category', 'all')
    
    # Create a copy of the dataframe to avoid modifying the original
    filtered_df = global_df.copy()
    
    # Apply filters
    filtered = False
    
    # Month filter
    if month != 'all':
        filtered = True
        # Extract month from the date column
        filtered_df = filtered_df[filtered_df['Fecha'].dt.strftime('%Y-%m') == month]
    
    # Date range filter
    if start_date:
        filtered = True
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            filtered_df = filtered_df[filtered_df['Fecha'] >= start_date_obj]
        except ValueError:
            flash('Formato de fecha de inicio inválido.', 'danger')
    
    if end_date:
        filtered = True
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            filtered_df = filtered_df[filtered_df['Fecha'] <= end_date_obj]
        except ValueError:
            flash('Formato de fecha de fin inválido.', 'danger')
    
    # Category filter
    if category != 'all':
        filtered = True
        filtered_df = filtered_df[filtered_df['Concepto'] == category]
    
    # Check if filtered data is empty
    if filtered_df.empty:
        flash('No hay datos para los filtros seleccionados.', 'warning')
        return redirect(url_for('analyze'))
    
    # Use Concepto as Categoría if Categoría doesn't exist
    category_col = 'Categoría' if 'Categoría' in filtered_df.columns else 'Concepto'
    
    # Create a copy for summary calculations (excluding transfers)
    calc_df = filtered_df.copy()
    
    # Exclude transfers between accounts for summary calculations
    if category_col in calc_df.columns:
        excluded_categories = ['Traspaso a cuenta', 'Traspaso desde cuenta']
        calc_df = calc_df[~calc_df[category_col].isin(excluded_categories)]
    
    # Calculate summary statistics
    income = calc_df[calc_df['Importe'] > 0]['Importe'].sum()
    expenses = abs(calc_df[calc_df['Importe'] < 0]['Importe'].sum())
    balance = income - expenses
    
    # Get category data
    categories = get_category_data(filtered_df)
    
    # Get available months for the filter dropdown
    available_months = []
    if not global_df.empty and 'Fecha' in global_df.columns:
        # Extract unique year-month combinations
        unique_months = global_df['Fecha'].dt.strftime('%Y-%m').unique()
        
        # Create a list of (value, display_name) tuples
        for month_val in sorted(unique_months):
            year, month_num = month_val.split('-')
            month_name = {
                '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
                '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
                '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
            }.get(month_num, month_num)
            
            display_name = f"{month_name} {year}"
            available_months.append((month_val, display_name))
    
    # Create charts based on filtered data
    create_monthly_chart(filtered_df)
    create_category_distribution_chart(filtered_df)
    create_category_analysis_chart(filtered_df)
    
    # Get transactions for the transactions tab
    transactions = filtered_df.head(100).to_dict('records')  # Limit to 100 for performance
    
    # Create summary for the summary cards
    summary = {
        'income': format_currency(income),
        'expenses': format_currency(expenses),
        'balance': format_currency(balance)
    }
    
    return render_template('results.html', 
                          income=income, 
                          expenses=expenses, 
                          balance=balance, 
                          categories=categories,
                          available_months=available_months,
                          selected_month=month,
                          start_date=start_date,
                          end_date=end_date,
                          selected_category=category,
                          filtered=filtered,
                          transactions=transactions,
                          summary=summary)

@app.route('/category/<category>')
def category_details(category):
    """Show details for a specific category"""
    global global_df
    
    if global_df is None:
        flash('Please analyze files first')
        return redirect(url_for('index'))
    
    # Clean category name if needed
    clean_category = category.strip()
    if "dtype:" in clean_category:
        clean_category = clean_category.split("dtype:")[0].strip()
    
    # Convert DataFrame categories to string to ensure matching
    global_df["Categoría"] = global_df["Categoría"].astype(str)
    
    # Filter by category (using string contains for more flexible matching)
    category_df = global_df[global_df["Categoría"].str.contains(clean_category, na=False)]
    
    if category_df.empty:
        flash(f'No transactions found for category: {clean_category}')
        return redirect(url_for('analyze'))
    
    return render_template(
        'category.html',
        category=clean_category,
        transactions=category_df.to_dict('records')
    )

@app.route('/download')
def download_results():
    """Download the analyzed data as Excel file"""
    global global_df
    
    if global_df is None:
        flash('Please analyze files first')
        return redirect(url_for('index'))
    
    # Create a temporary file
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, f"bank_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    
    # Save to Excel
    global_df.to_excel(output_path, index=False)
    
    @app.after_request
    def cleanup(response):
        shutil.rmtree(temp_dir, ignore_errors=True)
        return response
    
    return send_file(output_path, as_attachment=True)

@app.route('/expense_alerts', methods=['GET', 'POST'])
def expense_alerts():
    """Route for managing expense alerts and thresholds"""
    if global_df is None:
        flash('Por favor, analiza un archivo primero.', 'warning')
        return redirect(url_for('index'))
    
    # Initialize alerts in session if not present
    if 'alerts' not in session:
        session['alerts'] = {}
    
    if request.method == 'POST':
        category = request.form.get('category')
        threshold = request.form.get('threshold')
        
        if category and threshold:
            try:
                threshold = float(threshold)
                session['alerts'][category] = threshold
                flash(f'Alerta configurada para {category} con umbral de {threshold:,.2f} €', 'success')
            except ValueError:
                flash('El umbral debe ser un número válido', 'danger')
    
    # Get all unique categories from the dataframe
    categories = []
    if global_df is not None:
        # Clean category names
        categories = global_df['Categoría'].astype(str).str.replace('dtype:object', '').unique().tolist()
        categories.sort()
    
    # Check for triggered alerts
    triggered_alerts = {}
    if global_df is not None and 'alerts' in session:
        for category, threshold in session['alerts'].items():
            # Clean category name for comparison
            clean_category = category.replace('dtype:object', '')
            
            # Filter dataframe for expenses in this category
            category_expenses = global_df[
                (global_df['Categoría'].astype(str).str.replace('dtype:object', '') == clean_category) & 
                (global_df['Importe'] < 0)
            ]
            
            if not category_expenses.empty:
                total_spent = abs(category_expenses['Importe'].sum())
                if total_spent > threshold:
                    triggered_alerts[category] = {
                        'threshold': threshold,
                        'current': total_spent,
                        'excess': total_spent - threshold
                    }
    
    return render_template(
        'alerts.html',
        categories=categories,
        alerts=session.get('alerts', {}),
        triggered_alerts=triggered_alerts
    )

@app.route('/delete_alert/<category>')
def delete_alert(category):
    """Delete an alert for a specific category"""
    if 'alerts' in session and category in session['alerts']:
        del session['alerts'][category]
        flash(f'Alerta para {category} eliminada', 'success')
    return redirect(url_for('expense_alerts'))

@app.route('/simulator')
def simulator():
    """Investment simulator page"""
    return render_template('simulator.html')

@app.route('/financial_report')
@app.route('/financial_report/<month>')
def financial_report(month=None):
    """Generate a personalized financial report, optionally filtered by month"""
    global global_df
    
    if global_df is None:
        flash('Por favor, analiza primero un archivo.', 'warning')
        return redirect(url_for('index'))
    
    # Create a copy of the dataframe to avoid modifying the original
    df = global_df.copy()
    
    # Filter by month if specified
    filtered = False
    report_title = "Informe Financiero Completo"
    
    if month and month != 'all':
        filtered = True
        # Extract month from the date column
        df = df[df['Fecha'].dt.strftime('%Y-%m') == month]
        
        # Get month name for the title
        try:
            year, month_num = month.split('-')
            month_name = {
                '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
                '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
                '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
            }.get(month_num, month_num)
            
            report_title = f"Informe Financiero - {month_name} {year}"
        except:
            report_title = "Informe Financiero Filtrado"
    
    # Check if filtered data is empty
    if df.empty:
        flash('No hay datos para el mes seleccionado.', 'warning')
        return redirect(url_for('analyze'))
    
    # Calculate financial metrics
    total_income = df[df['Importe'] > 0]['Importe'].sum()
    total_expenses = abs(df[df['Importe'] < 0]['Importe'].sum())
    savings_rate = (total_income - total_expenses) / total_income * 100 if total_income > 0 else 0
    
    # Get top expense categories
    expense_df = df[df['Importe'] < 0].copy()
    top_expenses = expense_df.groupby('Concepto')['Importe'].sum().abs().sort_values(ascending=False).head(5)
    top_expense_categories = [
        {'name': cat, 'amount': amount, 'percentage': (amount / total_expenses) * 100}
        for cat, amount in top_expenses.items()
    ]
    
    # Generate personalized recommendations
    recommendations = []
    
    # Recommendation based on savings rate
    if savings_rate < 10:
        recommendations.append({
            'title': 'Aumenta tu tasa de ahorro',
            'description': 'Tu tasa de ahorro actual está por debajo del 10%. Considera reducir gastos no esenciales para aumentar tus ahorros.',
            'source': 'Regla 50/30/20 de presupuesto personal'
        })
    elif savings_rate < 20:
        recommendations.append({
            'title': 'Buen trabajo con tus ahorros',
            'description': 'Tu tasa de ahorro está en buen camino. Considera aumentarla gradualmente hasta alcanzar el 20-30%.',
            'source': 'Principios de independencia financiera'
        })
    else:
        recommendations.append({
            'title': 'Excelente tasa de ahorro',
            'description': 'Estás ahorrando más del 20% de tus ingresos, lo cual es excelente para tu futuro financiero.',
            'source': 'Estrategias de libertad financiera'
        })
    
    # Recommendation based on top expense category
    if top_expense_categories:
        top_category = top_expense_categories[0]
        if top_category['percentage'] > 40:
            recommendations.append({
                'title': f'Revisa tus gastos en {top_category["name"]}',
                'description': f'Esta categoría representa más del 40% de tus gastos totales. Considera estrategias para reducir este gasto.',
                'source': 'Análisis de presupuesto balanceado'
            })
    
    # General recommendation for financial health
    recommendations.append({
        'title': 'Establece un fondo de emergencia',
        'description': 'Asegúrate de tener un fondo de emergencia que cubra 3-6 meses de gastos para imprevistos.',
        'source': 'Planificación financiera básica'
    })
    
    # Get available months for the filter dropdown
    available_months = []
    if not global_df.empty and 'Fecha' in global_df.columns:
        # Extract unique year-month combinations
        unique_months = global_df['Fecha'].dt.strftime('%Y-%m').unique()
        
        # Create a list of (value, display_name) tuples
        for month_val in sorted(unique_months):
            year, month_num = month_val.split('-')
            month_name = {
                '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
                '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
                '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
            }.get(month_num, month_num)
            
            display_name = f"{month_name} {year}"
            available_months.append((month_val, display_name))
    
    return render_template('financial_report.html',
                          report_title=report_title,
                          total_income=total_income,
                          total_expenses=total_expenses,
                          savings_rate=savings_rate,
                          top_expense_categories=top_expense_categories,
                          recommendations=recommendations,
                          available_months=available_months,
                          selected_month=month if month else 'all')

def create_charts(df):
    """Create charts for the analysis page"""
    # Create directory for charts if it doesn't exist
    os.makedirs(os.path.join(app.static_folder, 'charts'), exist_ok=True)
    
    # Create monthly chart
    create_monthly_chart(df)
    
    # Create category distribution chart
    create_category_distribution_chart(df)
    
    # Create category analysis chart
    create_category_analysis_chart(df)

def create_category_distribution_chart(df):
    """Create pie chart for expense distribution by category"""
    # Ensure required columns exist
    if 'Importe' not in df.columns:
        # Create an empty chart if Importe column doesn't exist
        fig = go.Figure()
        fig.update_layout(title="No hay datos de gastos disponibles")
        fig.write_json(os.path.join(app.static_folder, 'charts', 'category_distribution.json'))
        return
    
    # Use Concepto as Categoría if Categoría doesn't exist
    category_col = 'Categoría' if 'Categoría' in df.columns else 'Concepto'
    
    # Filter for expenses only (negative amounts)
    expenses_df = df[df['Importe'] < 0].copy()
    
    if expenses_df.empty:
        # Create an empty chart if there are no expenses
        fig = go.Figure()
        fig.update_layout(title="No hay datos de gastos disponibles")
        fig.write_json(os.path.join(app.static_folder, 'charts', 'category_distribution.json'))
        return
    
    # Clean category names
    expenses_df.loc[:, category_col] = expenses_df[category_col].astype(str).str.replace('dtype:object', '')
    
    # Exclude transfers between accounts
    excluded_categories = ['Traspaso a cuenta', 'Traspaso desde cuenta']
    expenses_df = expenses_df[~expenses_df[category_col].isin(excluded_categories)]
    
    if expenses_df.empty:
        # Create an empty chart if there are no expenses after filtering
        fig = go.Figure()
        fig.update_layout(title="No hay datos de gastos disponibles (excluyendo traspasos)")
        fig.write_json(os.path.join(app.static_folder, 'charts', 'category_distribution.json'))
        return
    
    # Group by category and sum amounts (use absolute values for expenses)
    category_data = expenses_df.groupby(category_col)['Importe'].sum().abs()
    
    # Sort by amount in descending order
    category_data = category_data.sort_values(ascending=False)
    
    # Calculate percentages
    total_expenses = category_data.sum()
    percentages = (category_data / total_expenses * 100).round(2)
    
    # Create labels with category name, amount and percentage
    labels = [f"{cat} ({amt:.2f}€ - {pct:.2f}%)" 
              for cat, amt, pct in zip(category_data.index, category_data.values, percentages)]
    
    # Create pie chart
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=category_data.values,
        hole=0.4,
        textinfo='percent',
        insidetextorientation='radial',
        marker=dict(
            colors=px.colors.qualitative.Pastel,
            line=dict(color='#FFFFFF', width=2)
        )
    )])
    
    fig.update_layout(
        title="Distribución de Gastos por Categoría",
        height=500,
        margin=dict(l=50, r=50, t=100, b=50),
    )
    
    # Save chart as JSON
    fig.write_json(os.path.join(app.static_folder, 'charts', 'category_distribution.json'))

def get_summary(df):
    """Get summary statistics"""
    total_income = df[df["Importe"] > 0]["Importe"].sum()
    total_expenses = df[df["Importe"] < 0]["Importe"].sum()
    balance = total_income + total_expenses
    
    return {
        'income': f"{total_income:.2f}€",
        'expenses': f"{total_expenses:.2f}€",
        'balance': f"{balance:.2f}€"
    }

def get_category_data(df):
    """Get category data for pie chart"""
    # Ensure required columns exist
    if 'Importe' not in df.columns:
        # Return empty data if Importe column doesn't exist
        return pd.Series(dtype='float64')
    
    # Use Concepto as Categoría if Categoría doesn't exist
    category_col = 'Categoría' if 'Categoría' in df.columns else 'Concepto'
    
    # Filter for expenses (negative amounts)
    expenses_df = df[df['Importe'] < 0].copy()
    
    if expenses_df.empty:
        return pd.Series(dtype='float64')
    
    # Clean category names
    expenses_df.loc[:, category_col] = expenses_df[category_col].astype(str).str.replace('dtype:object', '')
    
    # Exclude transfers between accounts
    excluded_categories = ['Traspaso a cuenta', 'Traspaso desde cuenta']
    expenses_df = expenses_df[~expenses_df[category_col].isin(excluded_categories)]
    
    if expenses_df.empty:
        return pd.Series(dtype='float64')
    
    # Group by category and sum amounts (use absolute values for expenses)
    category_data = expenses_df.groupby(category_col)['Importe'].agg(['sum', 'count'])
    category_data['sum'] = category_data['sum'].abs()
    
    # Sort by amount in descending order
    category_data = category_data.sort_values('sum', ascending=False)
    
    # Format the data for the template
    result = []
    for category, row in category_data.iterrows():
        result.append({
            'name': category,
            'total': format_currency(row['sum']),
            'count': row['count']
        })
    
    return result

def create_monthly_chart(df):
    """Create monthly chart showing income vs expenses"""
    # Ensure required columns exist
    if 'Importe' not in df.columns or 'Fecha' not in df.columns:
        # Create an empty chart if required columns don't exist
        fig = go.Figure()
        fig.update_layout(title="No hay datos suficientes para el gráfico mensual")
        fig.write_json(os.path.join(app.static_folder, 'charts', 'monthly_overview.json'))
        return
    
    # Split into income and expenses
    income_df = df[df["Importe"] > 0]
    expenses_df = df[df["Importe"] < 0]
    
    if income_df.empty and expenses_df.empty:
        # Create an empty chart if there are no transactions
        fig = go.Figure()
        fig.update_layout(title="No hay transacciones disponibles")
        fig.write_json(os.path.join(app.static_folder, 'charts', 'monthly_overview.json'))
        return
    
    # Group by month and sum
    income_monthly = income_df.groupby(income_df["Fecha"].dt.strftime('%Y-%m'))["Importe"].sum()
    expenses_monthly = expenses_df.groupby(expenses_df["Fecha"].dt.strftime('%Y-%m'))["Importe"].sum().abs()
    
    # Merge income and expenses
    monthly_data = pd.DataFrame({
        'Income': income_monthly,
        'Expenses': expenses_monthly
    }).fillna(0)
    
    # Calculate balance
    monthly_data['Balance'] = monthly_data['Income'] - monthly_data['Expenses']
    
    # Format month names
    month_labels = []
    for month_key in monthly_data.index:
        year, month_num = month_key.split('-')
        month_name = {
            '01': 'Ene', '02': 'Feb', '03': 'Mar', '04': 'Abr',
            '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Ago',
            '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dic'
        }.get(month_num, month_num)
        month_labels.append(f"{month_name} {year}")
    
    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Add traces
    fig.add_trace(
        go.Bar(
            x=month_labels,
            y=monthly_data['Expenses'],
            name="Gastos",
            marker_color='#FF6B6B'
        ),
        secondary_y=False,
    )
    
    fig.add_trace(
        go.Bar(
            x=month_labels,
            y=monthly_data['Income'],
            name="Ingresos",
            marker_color='#4ECDC4'
        ),
        secondary_y=False,
    )
    
    fig.add_trace(
        go.Scatter(
            x=month_labels,
            y=monthly_data['Balance'],
            name="Balance",
            line=dict(color='#1A535C', width=3),
            mode='lines+markers'
        ),
        secondary_y=True,
    )
    
    # Add annotations for expense percentage of income
    for i, (month, row) in enumerate(monthly_data.iterrows()):
        if row['Income'] > 0:
            expense_percentage = (row['Expenses'] / row['Income']) * 100
            fig.add_annotation(
                x=month_labels[i],
                y=row['Expenses'],
                text=f"{expense_percentage:.1f}%",
                showarrow=False,
                yshift=10,
                font=dict(color="white", size=10),
                bgcolor="#FF6B6B",
                bordercolor="#FF6B6B",
                borderwidth=1,
                borderpad=3,
                opacity=0.8
            )
    
    # Update layout
    fig.update_layout(
        title="Resumen Mensual: Ingresos vs Gastos",
        barmode='group',
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=50, r=50, t=100, b=50),
    )
    
    # Set y-axes titles
    fig.update_yaxes(title_text="Euros (€)", secondary_y=False)
    fig.update_yaxes(title_text="Balance (€)", secondary_y=True)
    
    # Save chart as JSON
    fig.write_json(os.path.join(app.static_folder, 'charts', 'monthly_overview.json'))

def create_category_analysis_chart(df):
    """Create bar chart for category analysis"""
    # Ensure required columns exist
    if 'Importe' not in df.columns:
        # Create an empty chart if required columns don't exist
        fig = go.Figure()
        fig.update_layout(title="No hay datos suficientes para el análisis por categoría")
        fig.write_json(os.path.join(app.static_folder, 'charts', 'category_analysis.json'))
        return
    
    # Determine which column to use for categories
    category_col = 'Categoría' if 'Categoría' in df.columns else 'Concepto'
    
    # Filter for expenses only (negative amounts)
    expenses_df = df[df["Importe"] < 0].copy()
    
    if expenses_df.empty:
        # Create an empty chart if there are no expenses
        fig = go.Figure()
        fig.update_layout(title="No hay gastos disponibles para analizar")
        fig.write_json(os.path.join(app.static_folder, 'charts', 'category_analysis.json'))
        return
    
    # Clean category names and group by category
    expenses_df[category_col] = expenses_df[category_col].fillna("Sin categoría")
    expenses_df[category_col] = expenses_df[category_col].str.strip().str.capitalize()
    
    # Exclude transfers between accounts
    excluded_categories = ['Traspaso a cuenta', 'Traspaso desde cuenta']
    expenses_df = expenses_df[~expenses_df[category_col].isin(excluded_categories)]
    
    if expenses_df.empty:
        # Create an empty chart if there are no expenses after filtering
        fig = go.Figure()
        fig.update_layout(title="No hay gastos disponibles para analizar (excluyendo traspasos)")
        fig.write_json(os.path.join(app.static_folder, 'charts', 'category_analysis.json'))
        return
    
    # Group by category and calculate total expenses and count
    category_data = expenses_df.groupby(category_col).agg({
        'Importe': [('total', lambda x: abs(x.sum())), ('count', 'count')]
    }).reset_index()
    
    # Flatten the multi-level columns
    category_data.columns = [' '.join(col).strip() for col in category_data.columns.values]
    
    # Sort by total expenses and limit to top 15 for readability
    category_data = category_data.sort_values('Importe total', ascending=False).head(15)
    
    # Create the bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=category_data['Categoría'] if 'Categoría' in category_data.columns else category_data['Concepto'],
        y=category_data['Importe total'],
        text=category_data['Importe total'].apply(lambda x: f"{x:.2f}€"),
        textposition='auto',
        marker_color='#FF6B6B',
        hoverinfo='text',
        hovertext=[
            f"Categoría: {cat}<br>Total: {total:.2f}€<br>Transacciones: {count}" 
            for cat, total, count in zip(
                category_data['Categoría'] if 'Categoría' in category_data.columns else category_data['Concepto'],
                category_data['Importe total'], 
                category_data['Importe count']
            )
        ]
    ))
    
    # Update layout
    fig.update_layout(
        title="Análisis de Gastos por Categoría",
        xaxis_title="Categoría",
        yaxis_title="Total Gastado (€)",
        xaxis={'categoryorder':'total descending'},
        height=500,
        margin=dict(l=50, r=50, t=100, b=150),
        xaxis_tickangle=-45
    )
    
    # Save chart as JSON
    fig.write_json(os.path.join(app.static_folder, 'charts', 'category_analysis.json'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 