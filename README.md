# Bank Transaction Analyzer

A Python application to analyze bank transactions from Excel files. The application provides a graphical interface to visualize your transactions, with features like category grouping, monthly filtering, and interactive charts.

## Features

- Load multiple Excel files
- Categorize transactions automatically
- Filter transactions by month
- Interactive charts using Plotly:
  - Category distribution (pie chart)
  - Category analysis (bar chart with transaction counts)
  - Monthly overview
- Sort transactions by any column
- Export results to Excel
- Detailed transaction views
- Summary statistics

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/garbarok/bank.git
cd bank
```

2. Create a virtual environment (recommended):

```bash
# On macOS/Linux
python -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
.\venv\Scripts\activate
```

3. Install required packages:

```bash
pip install -r requirements.txt
```

## Usage

1. Start the application:

```bash
python src/main.py
```

2. Using the application:
   - Click "Add File" to load one or more Excel files
   - The files should be in BBVA format with the following columns:
     - ID
     - F. Valor
     - Fecha
     - Concepto
     - Movimiento
     - Importe
     - Divisa
     - Disponible
     - Divisa_2
     - Observaciones
   - Click "Analyze Transactions" to process the files
   - Use the month filter to view transactions for specific months
   - Navigate between tabs:
     - "All Transactions": View detailed transaction list
     - "Grouped by Category": See totals by category
     - "Charts": Access interactive visualizations
   - Double-click on a category in the grouped view to see its transactions
   - Click column headers to sort data
   - Use "Download Results" to save the analyzed data to Excel

## Charts

The application provides three types of interactive charts:

1. **Category Distribution**:

   - Pie chart showing the distribution of expenses by category
   - Click on the legend to show/hide categories
   - Hover for detailed information

2. **Category Analysis**:

   - Bar chart showing total amounts per category
   - Line overlay showing number of transactions
   - Dual Y-axes for amounts and counts

3. **Monthly Overview**:
   - Bar chart showing total amounts per month
   - Line overlay showing transaction counts
   - Chronological ordering

## File Format

The application expects Excel files exported from BBVA online banking with the following structure:

- Sheet name: "Informe BBVA"
- Required columns: Fecha, Concepto, Movimiento, Importe, Divisa
- Data should start from row 5 (first 4 rows are headers)

## Troubleshooting

1. If you get an error loading files:

   - Ensure the Excel file is in the correct format
   - Check that the sheet name is "Informe BBVA"
   - Verify the data starts from row 5

2. If charts don't open:

   - Ensure you have a default web browser installed
   - Check that the 'charts' directory exists and is writable

3. If the application doesn't start:
   - Verify all dependencies are installed
   - Check Python version (3.8 or higher required)
   - Ensure you're in the correct directory when running the script

## Contributing

Feel free to submit issues and enhancement requests!
