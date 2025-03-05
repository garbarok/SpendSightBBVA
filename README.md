# BBVAnalyzer

> 📊 A Python desktop application for analyzing BBVA bank statements. Easily track your expenses, visualize spending patterns with interactive charts, and manage multiple bank statements in one place. Perfect for personal finance management and expense tracking.

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
- **Two application modes**:
  - Desktop application (Tkinter-based UI)
  - Web application (Flask-based, accessible from any device on your network)

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

1. Start the application with the launcher (recommended):

```bash
python src/main.py
```

2. Choose your preferred application mode:

   - **Desktop Application**: Traditional UI that runs locally
   - **Web Application**: Runs a web server with a system tray icon, accessible from any device on your network

3. Alternatively, you can run the web application directly:

```bash
python run_web_app.py
```

### Desktop Application

The desktop application provides a traditional UI with:

- File management directly in the application
- Multiple tabs for different views
- Interactive charts embedded in the application

### Web Application

The web application offers:

- Access from any device on your network (via browser)
- Modern, responsive UI
- System tray icon for quick access
- Same functionality as the desktop version

When you start the web application:

1. A system tray icon will appear
2. Your default browser will open to http://localhost:5000
3. Other devices on your network can access it via http://your-ip-address:5000

### Using Either Version

Both versions allow you to:

- Load and analyze Excel files
- Filter transactions by month
- View transactions by category
- Generate interactive charts
- Export results to Excel

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

2. If charts don't display:

   - For desktop version: Ensure matplotlib is properly installed
   - For web version: Check that your browser supports JavaScript and Plotly

3. If the web application is not accessible from other devices:
   - Check your firewall settings
   - Ensure you're using the correct IP address
   - Verify port 5000 is not blocked

## Contributing

Feel free to submit issues and enhancement requests!
