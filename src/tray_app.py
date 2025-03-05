import os
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox
import pystray
from PIL import Image, ImageDraw

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the Flask app
from src.web.app import app

# Global variables
server_thread = None
server_running = False
PORT = 5000

def create_icon_image(width, height, color1, color2):
    """Create a simple icon image for the system tray"""
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    
    # Draw a bank icon
    dc.rectangle((5, 10, width-5, height-5), fill=color2)
    dc.rectangle((10, 5, width-10, 10), fill=color2)
    
    # Draw columns
    column_width = (width - 20) // 3
    for i in range(3):
        x1 = 10 + i * (column_width + 2)
        dc.rectangle((x1, 15, x1 + column_width, height - 10), fill=color1)
    
    return image

def start_server():
    """Start the Flask server in a separate thread"""
    global server_running
    server_running = True
    app.run(host='0.0.0.0', port=PORT, debug=False)
    server_running = False

def open_browser():
    """Open the web browser to the application"""
    webbrowser.open(f'http://localhost:{PORT}')

def on_exit(icon):
    """Handle exit from the system tray"""
    icon.stop()
    os._exit(0)

def setup_tray_icon():
    """Set up the system tray icon and menu"""
    # Create an icon image
    icon_image = create_icon_image(64, 64, (0, 123, 255), (255, 255, 255))
    
    # Create the menu
    menu = (
        pystray.MenuItem('Open BBVAnalyzer', lambda: open_browser()),
        pystray.MenuItem('Exit', lambda: on_exit(icon))
    )
    
    # Create the icon
    icon = pystray.Icon("bbvanalyzer", icon_image, "BBVAnalyzer", menu)
    
    return icon

def show_notification():
    """Show a notification that the server is running"""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    messagebox.showinfo(
        "BBVAnalyzer Running",
        f"BBVAnalyzer is now running.\n\nAccess it at: http://localhost:{PORT}\n\nA system tray icon has been created."
    )
    
    root.destroy()

def main():
    """Main function to start the application"""
    global server_thread
    
    # Start the Flask server in a separate thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Show notification
    show_notification()
    
    # Open browser
    open_browser()
    
    # Set up and run the system tray icon
    icon = setup_tray_icon()
    icon.run()

if __name__ == "__main__":
    main() 