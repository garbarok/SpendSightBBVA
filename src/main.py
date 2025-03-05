import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def launch_desktop_app():
    """Launch the desktop version of the application"""
    from src.gui.main_window import MainWindow
    app = MainWindow()
    app.run()

def launch_web_app():
    """Launch the web version of the application with system tray icon"""
    try:
        # Import here to avoid circular imports
        from src import tray_app
        tray_app.main()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start web application: {str(e)}")
        raise

def main():
    """Main entry point that allows choosing between desktop and web versions"""
    # Create launcher window
    root = tk.Tk()
    root.title("BBVAnalyzer Launcher")
    root.geometry("400x300")
    root.resizable(False, False)
    
    # Center window
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    
    # Create main frame
    main_frame = ttk.Frame(root, padding="20")
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Add title
    title_label = ttk.Label(main_frame, text="BBVAnalyzer", font=("Arial", 18, "bold"))
    title_label.pack(pady=10)
    
    # Add description
    desc_label = ttk.Label(main_frame, text="Choose which version of the application to launch:", wraplength=350)
    desc_label.pack(pady=10)
    
    # Add buttons
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(pady=20)
    
    # Desktop version button
    desktop_btn = ttk.Button(
        button_frame, 
        text="Desktop Application", 
        command=lambda: [root.destroy(), launch_desktop_app()]
    )
    desktop_btn.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
    
    # Web version button
    web_btn = ttk.Button(
        button_frame, 
        text="Web Application", 
        command=lambda: [root.destroy(), launch_web_app()]
    )
    web_btn.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
    
    # Configure button sizes
    for btn in [desktop_btn, web_btn]:
        btn.configure(width=20)
    
    # Add info text
    info_frame = ttk.Frame(main_frame)
    info_frame.pack(fill=tk.X, pady=10)
    
    ttk.Label(info_frame, text="Desktop: Traditional application with local UI", 
             font=("Arial", 9), foreground="gray").pack(anchor="w")
    ttk.Label(info_frame, text="Web: Access via browser, can be used from other devices", 
             font=("Arial", 9), foreground="gray").pack(anchor="w")
    
    # Start the main loop
    root.mainloop()

if __name__ == "__main__":
    main() 