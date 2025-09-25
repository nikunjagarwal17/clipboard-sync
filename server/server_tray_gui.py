#!/usr/bin/env python3
"""
Clipboard Sync Server - System Tray Version
Requires: pip install pystray pillow
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import time
import os
import sys
from datetime import datetime
import queue
import json

try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

class ServerTrayGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Clipboard Sync Server")
        self.root.geometry("600x400")
        self.root.resizable(True, True)
        
        # Server processes
        self.server_process = None
        self.ngrok_process = None
        self.is_running = False
        
        # Log queue and file
        self.log_queue = queue.Queue()
        self.log_file = f"server_gui_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Tray icon
        self.tray_icon = None
        self.is_hidden = False
        self.tray_running = False
        
        self.setup_ui()
        self.start_log_updater()
        
        if TRAY_AVAILABLE:
            self.setup_tray()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Clipboard Sync Server", 
                               font=('Arial', 14, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Control buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, columnspan=3, pady=(0, 10), sticky=(tk.W, tk.E))
        
        # Start/Stop button
        self.start_stop_btn = ttk.Button(button_frame, text="Start Server", 
                                        command=self.toggle_server)
        self.start_stop_btn.grid(row=0, column=0, padx=(0, 10))
        
        # Status label
        self.status_label = ttk.Label(button_frame, text="Status: Stopped", 
                                     foreground="red")
        self.status_label.grid(row=0, column=1, padx=(10, 0))
        
        # Hide/Show tray button
        if TRAY_AVAILABLE:
            self.tray_btn = ttk.Button(button_frame, text="Hide to Tray", 
                                      command=self.hide_to_tray)
            self.tray_btn.grid(row=0, column=2, padx=(10, 0))
        
        # URL display frame
        url_frame = ttk.LabelFrame(main_frame, text="Public URL", padding="5")
        url_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 10))
        url_frame.columnconfigure(0, weight=1)
        
        self.url_var = tk.StringVar(value="Not available (server not started)")
        self.url_label = ttk.Label(url_frame, textvariable=self.url_var, 
                                  foreground="blue", cursor="hand2")
        self.url_label.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.url_label.bind("<Button-1>", self.copy_url_to_clipboard)
        
        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Server Logs", padding="5")
        log_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, 
                                                 state=tk.DISABLED, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def setup_tray(self):
        """Setup system tray icon"""
        # Create icon
        image = Image.new('RGB', (64, 64), color='blue')
        draw = ImageDraw.Draw(image)
        draw.rectangle([16, 16, 48, 48], fill='white')
        draw.text((20, 24), "CS", fill='blue')
        
        # Create menu
        menu = pystray.Menu(
            item('Show', self.show_window, default=True),
            item('Start Server', self.start_server, enabled=lambda item: not self.is_running),
            item('Stop Server', self.stop_server, enabled=lambda item: self.is_running),
            pystray.Menu.SEPARATOR,
            item('Exit', self.quit_app)
        )
        
        self.tray_icon = pystray.Icon("clipboard_sync", image, "Clipboard Sync Server", menu)
        
    def log_message(self, message):
        """Add message to log queue and file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        
        # Add to queue for GUI
        self.log_queue.put(full_message)
        
        # Write to file
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(full_message + '\n')
        except:
            pass
        
    def start_log_updater(self):
        """Start the log updater thread"""
        def update_logs():
            try:
                while True:
                    try:
                        message = self.log_queue.get_nowait()
                        if not self.is_hidden:
                            self.log_text.config(state=tk.NORMAL)
                            self.log_text.insert(tk.END, message + "\n")
                            self.log_text.see(tk.END)
                            self.log_text.config(state=tk.DISABLED)
                        self.log_queue.task_done()
                    except queue.Empty:
                        break
            except:
                pass
            
            # Schedule next update
            if not self.is_hidden:
                self.root.after(100, update_logs)
            else:
                # When hidden, update less frequently
                threading.Timer(1.0, update_logs).start()
            
        self.root.after(100, update_logs)
        
    def copy_url_to_clipboard(self, event):
        """Copy URL to clipboard when clicked"""
        url = self.url_var.get()
        if url and url != "Not available (server not started)":
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.log_message("URL copied to clipboard")
            
    def toggle_server(self):
        if self.is_running:
            self.stop_server()
        else:
            self.start_server()
            
    def start_server(self):
        """Start the server and ngrok in background"""
        if self.is_running:
            return
            
        self.log_message("Starting Clipboard Sync Server...")
        
        try:
            # Start Python server in background (no window)
            server_cmd = [sys.executable, "server.py"]
            self.server_process = subprocess.Popen(
                server_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                cwd=os.path.dirname(os.path.abspath(__file__)),
                text=True,
                bufsize=1
            )
            
            self.log_message("Python server started")
            
            # Wait a moment for server to initialize
            time.sleep(3)
            
            # Start ngrok in background (no window)
            ngrok_cmd = ["ngrok", "http", "8765", "--config", "ngrok.yml", "--log=stdout"]
            self.ngrok_process = subprocess.Popen(
                ngrok_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                cwd=os.path.dirname(os.path.abspath(__file__)),
                text=True,
                bufsize=1
            )
            
            self.log_message("Ngrok tunnel started")
            
            # Update UI
            self.is_running = True
            if not self.is_hidden:
                self.start_stop_btn.config(text="Stop Server")
                self.status_label.config(text="Status: Running", foreground="green")
            
            # Start monitoring threads
            threading.Thread(target=self.monitor_server, daemon=True).start()
            threading.Thread(target=self.monitor_ngrok, daemon=True).start()
            threading.Thread(target=self.get_ngrok_url, daemon=True).start()
            
        except FileNotFoundError as e:
            error_msg = f"Error: {e} - Make sure Python and ngrok are installed and in PATH"
            self.log_message(error_msg)
            if not self.is_hidden:
                messagebox.showerror("Error", f"Failed to start server: {e}")
        except Exception as e:
            error_msg = f"Error starting server: {e}"
            self.log_message(error_msg)
            if not self.is_hidden:
                messagebox.showerror("Error", error_msg)
            
    def stop_server(self):
        """Stop the server and ngrok"""
        if not self.is_running:
            return
            
        self.log_message("Stopping server...")
        
        # Stop ngrok
        if self.ngrok_process:
            try:
                self.ngrok_process.terminate()
                self.ngrok_process.wait(timeout=5)
            except:
                try:
                    self.ngrok_process.kill()
                except:
                    pass
            self.ngrok_process = None
            
        # Stop Python server
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except:
                try:
                    self.server_process.kill()
                except:
                    pass
            self.server_process = None
            
        # Update UI
        self.is_running = False
        if not self.is_hidden:
            self.start_stop_btn.config(text="Start Server")
            self.status_label.config(text="Status: Stopped", foreground="red")
            self.url_var.set("Not available (server stopped)")
        
        self.log_message("Server stopped")
        
    def monitor_server(self):
        """Monitor server output"""
        if not self.server_process:
            return
            
        try:
            for line in iter(self.server_process.stdout.readline, ''):
                if line:
                    self.log_message(f"SERVER: {line.strip()}")
                if self.server_process.poll() is not None:
                    break
        except:
            pass
            
    def monitor_ngrok(self):
        """Monitor ngrok output"""
        if not self.ngrok_process:
            return
            
        try:
            for line in iter(self.ngrok_process.stdout.readline, ''):
                if line:
                    # Filter out verbose ngrok logs, keep important ones
                    if any(keyword in line.lower() for keyword in ['error', 'tunnel', 'started', 'failed']):
                        self.log_message(f"NGROK: {line.strip()}")
                if self.ngrok_process.poll() is not None:
                    break
        except:
            pass
        
    def get_ngrok_url(self):
        """Get the ngrok public URL"""
        # Wait for ngrok to start
        time.sleep(5)
        
        for attempt in range(10):  # Try for 10 seconds
            try:
                import urllib.request
                
                response = urllib.request.urlopen("http://localhost:4040/api/tunnels")
                data = json.loads(response.read())
                
                for tunnel in data.get('tunnels', []):
                    if tunnel.get('config', {}).get('addr') == 'http://localhost:8765':
                        url = tunnel.get('public_url')
                        if url:
                            if not self.is_hidden:
                                self.url_var.set(url)
                            self.log_message(f"Public URL: {url}")
                            return
                            
            except Exception as e:
                if attempt == 9:  # Last attempt
                    self.log_message(f"Could not get ngrok URL: {e}")
                    if not self.is_hidden:
                        self.url_var.set("Check ngrok dashboard at http://localhost:4040")
                else:
                    time.sleep(1)  # Wait before retry
                    
    def hide_to_tray(self):
        """Hide window to system tray"""
        if TRAY_AVAILABLE:
            self.is_hidden = True
            self.root.withdraw()
            self.log_message("Application minimized to system tray")
            
            # Start tray icon in separate thread
            if not self.tray_running:
                self.tray_running = True
                threading.Thread(target=self.run_tray_icon, daemon=True).start()
        else:
            messagebox.showinfo("No Tray Support", 
                               "System tray not available. Install pystray and pillow:\n" +
                               "pip install pystray pillow")
    
    def run_tray_icon(self):
        """Run the tray icon"""
        try:
            self.tray_icon.run()
        except Exception as e:
            self.log_message(f"Tray icon error: {e}")
        finally:
            self.tray_running = False
            
    def show_window(self, icon=None, item=None):
        """Show window from tray"""
        self.is_hidden = False
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        
        # Update UI if server is running
        if self.is_running:
            self.start_stop_btn.config(text="Stop Server")
            self.status_label.config(text="Status: Running", foreground="green")
        else:
            self.start_stop_btn.config(text="Start Server")
            self.status_label.config(text="Status: Stopped", foreground="red")
            
    def quit_app(self, icon=None, item=None):
        """Quit application completely"""
        if self.is_running:
            self.stop_server()
        
        if self.tray_icon and self.tray_running:
            try:
                self.tray_icon.stop()
            except:
                pass
            self.tray_running = False
        
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass
        
    def on_closing(self):
        """Handle window closing"""
        if TRAY_AVAILABLE and self.is_running:
            # Just hide to tray if server is running
            self.hide_to_tray()
        else:
            # Ask before quitting
            if self.is_running:
                if messagebox.askokcancel("Quit", "Server is running. Stop server and quit?"):
                    self.quit_app()
            else:
                self.quit_app()
            
    def run(self):
        """Start the GUI"""
        self.root.mainloop()

def main():
    """Main function"""
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    if TRAY_AVAILABLE:
        app = ServerTrayGUI()
    else:
        print("Note: System tray support not available. Install with: pip install pystray pillow")
        from server_gui import ServerGUI
        app = ServerGUI()
        
    app.run()

if __name__ == "__main__":
    main()