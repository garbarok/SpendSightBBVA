import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from datetime import datetime
import os
import pandas as pd

from src.utils.data_processor import DataProcessor
from src.charts.chart_manager import ChartManager

class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.setup_gui()
        self.df = None
        self.loaded_files = []  # Keep track of loaded files

    def setup_gui(self):
        self.root.title("Bank Transaction Analyzer")
        self.root.geometry("1200x800")
        
        # Create main frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create controls frame
        self.controls_frame = ttk.Frame(self.main_frame)
        self.controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create a frame for the file list
        file_frame = ttk.LabelFrame(self.controls_frame, text="Loaded Files", padding="5")
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Add file list
        self.file_listbox = tk.Listbox(file_frame, height=3)
        self.file_listbox.pack(fill=tk.X, expand=True)
        
        # Create buttons frame
        buttons_frame = ttk.Frame(self.controls_frame)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Add file button
        ttk.Button(buttons_frame, text="Add File", command=self.add_file).pack(side=tk.LEFT, padx=5)
        
        # Remove file button
        ttk.Button(buttons_frame, text="Remove Selected", command=self.remove_file).pack(side=tk.LEFT, padx=5)
        
        # Add month filter
        ttk.Label(buttons_frame, text="Filter by Month:").pack(side=tk.LEFT, padx=(20, 5))
        self.month_var = tk.StringVar(value="All Months")
        self.month_filter = ttk.Combobox(buttons_frame, textvariable=self.month_var, state="readonly")
        self.month_filter.pack(side=tk.LEFT, padx=5)
        self.month_filter.bind('<<ComboboxSelected>>', lambda e: self.update_filtered_view())
        
        # Analyze button
        ttk.Button(buttons_frame, text="Analyze Transactions", command=self.analyze_files).pack(side=tk.LEFT, padx=20)
        
        # Download button
        ttk.Button(buttons_frame, text="Download Results", command=self.download_results).pack(side=tk.LEFT, padx=5)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create frames for each tab
        self.transactions_frame = ttk.Frame(self.notebook)
        self.grouped_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.transactions_frame, text="All Transactions")
        self.notebook.add(self.grouped_frame, text="Grouped by Category")
        
        # Setup transaction view
        self.setup_all_transactions_tab()
        self.setup_grouped_tab()
        
        # Create summary frame
        self.summary_frame = ttk.Frame(self.main_frame)
        self.summary_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.summary_text = tk.Text(self.summary_frame, height=3, width=50)
        self.summary_text.pack(side=tk.LEFT, padx=5)
        
        # Initialize chart manager
        self.chart_manager = ChartManager(self.notebook)

    def add_file(self):
        filenames = filedialog.askopenfilenames(
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        for filename in filenames:
            if filename not in self.loaded_files:  # Avoid duplicates
                self.loaded_files.append(filename)
                self.file_listbox.insert(tk.END, os.path.basename(filename))

    def remove_file(self):
        selection = self.file_listbox.curselection()
        if selection:
            index = selection[0]
            self.loaded_files.pop(index)
            self.file_listbox.delete(index)

    def analyze_files(self):
        if not self.loaded_files:
            messagebox.showwarning("Warning", "Please add at least one file first")
            return
            
        try:
            # Load and combine all files
            dfs = []
            for file_path in self.loaded_files:
                try:
                    df = DataProcessor.load_and_clean_data(file_path)
                    df = DataProcessor.analyze_transactions(df)
                    # Add source file column
                    df['Source'] = os.path.basename(file_path)
                    dfs.append(df)
                except Exception as e:
                    messagebox.showerror("Error", f"Error processing file {os.path.basename(file_path)}: {str(e)}")
                    return
            
            # Combine all dataframes
            self.df = pd.concat(dfs, ignore_index=True)
            
            # Sort by date
            self.df = self.df.sort_values('Fecha', ascending=False)
            
            self.update_month_filter()
            
            # Update views with filtered data
            self.update_filtered_view()
            
            # messagebox.showinfo("Success", "Analysis complete!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def download_results(self):
        if self.df is None:
            messagebox.showwarning("Warning", "Please analyze files first")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=f"bank_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        
        if filename:
            try:
                self.df.to_excel(filename, index=False)
                messagebox.showinfo("Success", f"Results saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Error saving file: {str(e)}")

    def setup_all_transactions_tab(self):
        # Create Treeview
        columns = ("Fecha", "Concepto", "Movimiento", "Importe", "Categoría", "Source")
        self.tree = ttk.Treeview(self.transactions_frame, columns=columns, show="headings")
        
        # Add column headings
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_treeview(c))
            self.tree.column(col, width=150)
        
        # Make Concept column wider
        self.tree.column("Concepto", width=300)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.transactions_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack elements
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def setup_grouped_tab(self):
        # Create Treeview for grouped results
        columns = ("Categoría", "Total", "Cantidad")
        self.grouped_tree = ttk.Treeview(self.grouped_frame, columns=columns, show="headings")
        
        # Add column headings
        for col in columns:
            self.grouped_tree.heading(col, text=col, command=lambda c=col: self.sort_grouped_treeview(c))
            self.grouped_tree.column(col, width=150)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.grouped_frame, orient=tk.VERTICAL, command=self.grouped_tree.yview)
        self.grouped_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack elements
        self.grouped_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind double-click event
        self.grouped_tree.bind("<Double-1>", self.show_category_details)
        
    def sort_treeview(self, col):
        items = [(self.tree.set(item, col), item) for item in self.tree.get_children("")]
        
        # Convert amounts to float for proper sorting
        if col == "Importe":
            items = [(float(value.replace("€", "").replace(",", "").strip()), item) for value, item in items]
        
        # Convert dates for proper sorting
        elif col == "Fecha":
            items = [(datetime.strptime(value, "%Y-%m-%d"), item) for value, item in items]
            
        items.sort(reverse=getattr(self, "reverse_sort", False))
        
        for index, (_, item) in enumerate(items):
            self.tree.move(item, "", index)
            
        self.reverse_sort = not getattr(self, "reverse_sort", False)
        
    def sort_grouped_treeview(self, col):
        items = [(self.grouped_tree.set(item, col), item) for item in self.grouped_tree.get_children("")]
        
        # Convert numeric values for proper sorting
        if col in ["Total", "Cantidad"]:
            items = [(float(value.replace("€", "").replace(",", "").strip()), item) for value, item in items]
            
        items.sort(reverse=getattr(self, "reverse_sort_grouped", False))
        
        for index, (_, item) in enumerate(items):
            self.grouped_tree.move(item, "", index)
            
        self.reverse_sort_grouped = not getattr(self, "reverse_sort_grouped", False)
        
    def show_category_details(self, event):
        item = self.grouped_tree.selection()[0]
        category = self.grouped_tree.item(item)["values"][0]
        
        # Create new window
        details_window = tk.Toplevel(self.root)
        details_window.title(f"Transactions for {category}")
        details_window.geometry("800x600")
        
        # Create Treeview
        columns = ("Fecha", "Concepto", "Movimiento", "Importe")
        tree = ttk.Treeview(details_window, columns=columns, show="headings")
        
        # Add column headings
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(details_window, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack elements
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Filter and display data
        category_df = self.df[self.df["Categoría"] == category]
        for _, row in category_df.iterrows():
            values = (
                row["Fecha"].strftime("%Y-%m-%d"),
                row["Concepto"],
                row["Movimiento"],
                f"{row['Importe']:.2f}€"
            )
            tree.insert("", tk.END, values=values)
            
    def update_month_filter(self):
        if self.df is not None:
            months = ["All Months"] + sorted(self.df["Fecha"].dt.strftime("%Y-%m").unique().tolist())
            self.month_filter["values"] = months
            self.month_filter.set("All Months")
            
    def filter_by_month(self, df):
        selected_month = self.month_var.get()
        if selected_month != "All Months":
            return df[df["Fecha"].dt.strftime("%Y-%m") == selected_month]
        return df
        
    def update_grouped_view(self, df):
        # Clear previous items
        for item in self.grouped_tree.get_children():
            self.grouped_tree.delete(item)
            
        # Group data
        grouped = df.groupby("Categoría").agg({
            "Importe": ["sum", "count"]
        }).reset_index()
        
        # Add items
        for _, row in grouped.iterrows():
            values = (
                row["Categoría"],
                f"{row[('Importe', 'sum')]:.2f}€",
                row[('Importe', 'count')]
            )
            self.grouped_tree.insert("", tk.END, values=values)
            
    def update_treeview(self, df):
        # Clear previous items
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Add items
        for _, row in df.iterrows():
            values = (
                row["Fecha"].strftime("%Y-%m-%d"),
                row["Concepto"],
                row["Movimiento"],
                f"{row['Importe']:.2f}€",
                row["Categoría"],
                row["Source"]
            )
            self.tree.insert("", tk.END, values=values)
            
    def update_summary(self, df):
        total_income = df[df["Importe"] > 0]["Importe"].sum()
        total_expenses = df[df["Importe"] < 0]["Importe"].sum()
        balance = total_income + total_expenses
        
        summary = f"Total Income: {total_income:.2f}€\n"
        summary += f"Total Expenses: {total_expenses:.2f}€\n"
        summary += f"Balance: {balance:.2f}€"
        
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(tk.END, summary)
        
    def update_filtered_view(self):
        if self.df is not None:
            filtered_df = self.filter_by_month(self.df)
            self.update_treeview(filtered_df)
            self.update_grouped_view(filtered_df)
            self.update_summary(filtered_df)
            self.chart_manager.update_charts(filtered_df)
        
    def run(self):
        self.root.mainloop() 