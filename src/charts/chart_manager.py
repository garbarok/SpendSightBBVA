import tkinter as tk
from tkinter import ttk
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import webbrowser
import os
from datetime import datetime

class ChartManager:
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        self.setup_charts_tab()

    def setup_charts_tab(self):
        # Create main frame for charts
        self.charts_frame = ttk.Frame(self.parent_frame)
        self.parent_frame.add(self.charts_frame, text="Charts")
        
        # Create buttons frame
        self.buttons_frame = ttk.Frame(self.charts_frame)
        self.buttons_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Add buttons for different chart types
        ttk.Button(self.buttons_frame, text="View Category Distribution", 
                  command=lambda: self.show_chart('pie')).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.buttons_frame, text="View Category Totals", 
                  command=lambda: self.show_chart('bar')).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.buttons_frame, text="View Monthly Overview", 
                  command=lambda: self.show_chart('monthly')).pack(side=tk.LEFT, padx=5)
        
        # Store the last DataFrame for chart updates
        self.last_df = None

    def update_charts(self, df):
        self.last_df = df
        self.create_all_charts(df)

    def create_all_charts(self, df):
        # Create a directory for charts if it doesn't exist
        if not os.path.exists('charts'):
            os.makedirs('charts')
        
        # Create and save all charts
        self.create_pie_chart(df)
        self.create_bar_chart(df)
        self.create_monthly_chart(df)

    def create_pie_chart(self, df):
        category_totals = df.groupby("Categoría")["Importe"].sum().abs()
        
        fig = px.pie(
            values=category_totals.values,
            names=category_totals.index,
            title="Category Distribution",
            template="plotly_white"
        )
        
        fig.write_html('charts/category_distribution.html')

    def create_bar_chart(self, df):
        category_totals = df.groupby("Categoría")["Importe"].agg(['sum', 'count']).reset_index()
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Add bars for total amounts
        fig.add_trace(
            go.Bar(
                x=category_totals["Categoría"],
                y=category_totals["sum"],
                name="Total Amount",
                marker_color='rgb(55, 83, 109)'
            ),
            secondary_y=False,
        )
        
        # Add line for transaction count
        fig.add_trace(
            go.Scatter(
                x=category_totals["Categoría"],
                y=category_totals["count"],
                name="Transaction Count",
                mode='lines+markers',
                marker_color='rgb(26, 118, 255)'
            ),
            secondary_y=True,
        )
        
        fig.update_layout(
            title="Category Analysis",
            xaxis_title="Category",
            yaxis_title="Total Amount (EUR)",
            yaxis2_title="Number of Transactions",
            template="plotly_white"
        )
        
        fig.write_html('charts/category_analysis.html')

    def create_monthly_chart(self, df):
        monthly_data = df.groupby(df["Fecha"].dt.strftime("%Y-%m"))["Importe"].agg(['sum', 'count']).reset_index()
        monthly_data = monthly_data.sort_values('Fecha')
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Add bars for monthly totals
        fig.add_trace(
            go.Bar(
                x=monthly_data["Fecha"],
                y=monthly_data["sum"],
                name="Monthly Total",
                marker_color='rgb(55, 83, 109)'
            ),
            secondary_y=False,
        )
        
        # Add line for transaction count
        fig.add_trace(
            go.Scatter(
                x=monthly_data["Fecha"],
                y=monthly_data["count"],
                name="Transaction Count",
                mode='lines+markers',
                marker_color='rgb(26, 118, 255)'
            ),
            secondary_y=True,
        )
        
        fig.update_layout(
            title="Monthly Overview",
            xaxis_title="Month",
            yaxis_title="Total Amount (EUR)",
            yaxis2_title="Number of Transactions",
            template="plotly_white"
        )
        
        fig.write_html('charts/monthly_overview.html')

    def show_chart(self, chart_type):
        if self.last_df is None:
            return
            
        chart_files = {
            'pie': 'charts/category_distribution.html',
            'bar': 'charts/category_analysis.html',
            'monthly': 'charts/monthly_overview.html'
        }
        
        if chart_type in chart_files:
            webbrowser.open('file://' + os.path.realpath(chart_files[chart_type])) 