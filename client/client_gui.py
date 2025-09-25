#!/usr/bin/env python3
"""
Clipboard Sync Client GUI - Minimal system tray version
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import asyncio
import websockets
import json
import pyperclip
import threading
import time
import os
import sys
from datetime import datetime
import queue
import base64
import io
from PIL import Image
import win32clipboard
import win32con

try:
    import pystray
    from pystray import MenuItem as item
    from PIL import ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

class ClipboardClientGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Clipboard Sync Client")
        self.root.geometry("500x400")
        self.root.resizable(True, True)
        
        # Client state
        self.websocket = None
        self.is_connected = False
        self.last_clipboard = ""
        self.user_id = ""
        self.password = ""
        self.server_url = "ws://172.20.42.107:8765"
        self.running = False
        
        # GUI state
        self.log_queue = queue.Queue()
        self.log_file = f"client_gui_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.tray_icon = None
        self.is_hidden = False
        self.tray_running = False
        
        self.load_config()
        self.setup_ui()
        self.start_log_updater()
        
        if TRAY_AVAILABLE:
            self.setup_tray()
        
    def load_config(self):
        """Load configuration from config.json"""
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
                self.server_url = config.get("server_url", self.server_url)
        except FileNotFoundError:
            config = {"server_url": self.server_url}
            with open("config.json", "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self.log_message(f"Warning: Could not read config.json: {e}")
    
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Clipboard Sync Client", 
                               font=('Arial', 14, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Server URL frame
        url_frame = ttk.LabelFrame(main_frame, text="Server Configuration", padding="5")
        url_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        url_frame.columnconfigure(1, weight=1)
        
        ttk.Label(url_frame, text="Server URL:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.url_var = tk.StringVar(value=self.server_url)
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var)
        self.url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        # Control buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=(10, 10), sticky=(tk.W, tk.E))
        
        # Connect/Disconnect button
        self.connect_btn = ttk.Button(button_frame, text="Connect", 
                                     command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=0, padx=(0, 10))
        
        # Status label
        self.status_label = ttk.Label(button_frame, text="Status: Disconnected", 
                                     foreground="red")
        self.status_label.grid(row=0, column=1, padx=(10, 0))
        
        # Hide to tray button
        if TRAY_AVAILABLE:
            self.tray_btn = ttk.Button(button_frame, text="Hide to Tray", 
                                      command=self.hide_to_tray)
            self.tray_btn.grid(row=0, column=2, padx=(10, 0))
        
        # User info frame
        info_frame = ttk.LabelFrame(main_frame, text="User Information", padding="5")
        info_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 10))
        info_frame.columnconfigure(1, weight=1)
        
        self.user_var = tk.StringVar(value="Not logged in")
        ttk.Label(info_frame, text="User:").grid(row=0, column=0, sticky=tk.W)
        self.user_label = ttk.Label(info_frame, textvariable=self.user_var, 
                                   foreground="blue")
        self.user_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Connection Logs", padding="5")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
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
        image = Image.new('RGB', (64, 64), color='green')
        draw = ImageDraw.Draw(image)
        draw.rectangle([16, 16, 48, 48], fill='white')
        draw.text((20, 24), "CC", fill='green')
        
        # Create menu
        menu = pystray.Menu(
            item('Show', self.show_window, default=True),
            item('Connect', self.connect_from_tray, enabled=lambda item: not self.is_connected),
            item('Disconnect', self.disconnect_from_tray, enabled=lambda item: self.is_connected),
            pystray.Menu.SEPARATOR,
            item('Exit', self.quit_app)
        )
        
        self.tray_icon = pystray.Icon("clipboard_client", image, "Clipboard Sync Client", menu)
        
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
                threading.Timer(1.0, update_logs).start()
            
        self.root.after(100, update_logs)
        
    def get_credentials(self):
        """Get credentials via dialog"""
        if not self.user_id:
            self.user_id = simpledialog.askstring("Login", "Enter your User ID:", parent=self.root)
            if not self.user_id:
                return False
                
        if not self.password:
            self.password = simpledialog.askstring("Login", "Enter your Password:", 
                                                  parent=self.root, show='*')
            if not self.password:
                return False
                
        return True
        
    def toggle_connection(self):
        if self.is_connected:
            self.disconnect()
        else:
            self.connect()
            
    def connect(self):
        """Connect to server"""
        if self.is_connected:
            return
            
        # Update server URL
        self.server_url = self.url_var.get().strip()
        if not self.server_url:
            messagebox.showerror("Error", "Please enter a server URL")
            return
            
        # Get credentials
        if not self.get_credentials():
            self.log_message("Connection cancelled - no credentials provided")
            return
            
        # Start connection in background thread
        self.running = True
        self.log_message(f"Connecting to server: {self.server_url}")
        self.log_message(f"User: {self.user_id}")
        
        # Update UI
        self.connect_btn.config(text="Connecting...", state=tk.DISABLED)
        
        # Start connection thread
        threading.Thread(target=self.run_client, daemon=True).start()
        
    def disconnect(self):
        """Disconnect from server"""
        self.running = False
        self.is_connected = False
        
        if self.websocket:
            try:
                # This will cause the client loop to exit
                asyncio.run_coroutine_threadsafe(
                    self.websocket.close(), 
                    self.client_loop
                )
            except:
                pass
            
        # Update UI
        if not self.is_hidden:
            self.connect_btn.config(text="Connect", state=tk.NORMAL)
            self.status_label.config(text="Status: Disconnected", foreground="red")
            self.user_var.set("Not logged in")
        
        self.log_message("Disconnected from server")
        
        # Clear credentials for next connection
        self.user_id = ""
        self.password = ""
        
    def connect_from_tray(self, icon=None, item=None):
        """Connect from tray menu"""
        self.connect()
        
    def disconnect_from_tray(self, icon=None, item=None):
        """Disconnect from tray menu"""
        self.disconnect()
        
    def run_client(self):
        """Run the client in asyncio loop"""
        try:
            self.client_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.client_loop)
            self.client_loop.run_until_complete(self.client_main())
        except Exception as e:
            self.log_message(f"Client error: {e}")
        finally:
            if not self.is_hidden:
                self.root.after(0, lambda: self.connect_btn.config(text="Connect", state=tk.NORMAL))
            
    async def client_main(self):
        """Main client logic"""
        try:
            # Connect to server
            self.websocket = await websockets.connect(
                self.server_url,
                ping_interval=30,
                ping_timeout=10
            )
            
            # Send authentication
            auth_message = {
                "type": "auth",
                "user_id": self.user_id,
                "password": self.password
            }
            
            await self.websocket.send(json.dumps(auth_message))
            
            # Wait for authentication response
            response = await self.websocket.recv()
            auth_result = json.loads(response)
            
            if auth_result.get("type") == "auth_success":
                self.is_connected = True
                self.log_message(f"✅ {auth_result.get('message')}")
                self.log_message("🔄 Clipboard sync is now active!")
                
                # Update UI on main thread
                if not self.is_hidden:
                    self.root.after(0, self.update_connected_ui)
                
                # Initialize clipboard with cleaned text
                try:
                    initial_clipboard = pyperclip.paste()
                    # Clean and normalize the initial clipboard text  
                    self.last_clipboard = initial_clipboard.encode('utf-8', errors='ignore').decode('utf-8')
                except:
                    self.last_clipboard = ""
                
                # Start clipboard monitoring
                clipboard_thread = threading.Thread(target=self.monitor_clipboard, daemon=True)
                clipboard_thread.start()
                
                # Listen for messages
                await self.listen_for_messages()
                
            else:
                self.log_message(f"❌ Authentication failed: {auth_result.get('message')}")
                
        except Exception as e:
            self.log_message(f"❌ Connection error: {e}")
        finally:
            self.is_connected = False
            self.running = False
            if not self.is_hidden:
                self.root.after(0, self.update_disconnected_ui)
                
    def update_connected_ui(self):
        """Update UI when connected"""
        self.connect_btn.config(text="Disconnect", state=tk.NORMAL)
        self.status_label.config(text="Status: Connected", foreground="green")
        self.user_var.set(self.user_id)
        
    def update_disconnected_ui(self):
        """Update UI when disconnected"""
        self.connect_btn.config(text="Connect", state=tk.NORMAL)
        self.status_label.config(text="Status: Disconnected", foreground="red")
        self.user_var.set("Not logged in")
        
    async def listen_for_messages(self):
        """Listen for messages from server"""
        try:
            async for message in self.websocket:
                if not self.running:
                    break
                    
                try:
                    # Ensure proper UTF-8 handling for received messages
                    if isinstance(message, bytes):
                        message = message.decode('utf-8', errors='ignore')
                    
                    data = json.loads(message)
                    message_type = data.get("type")
                    
                    if message_type == "clipboard_sync":
                        content_type = data.get("content_type", "text")
                        clipboard_text = data.get("text", "")
                        clipboard_image = data.get("image", "")
                        from_user = data.get("from_user", "Unknown")
                        
                        if content_type == "image" and clipboard_image:
                            if self.set_clipboard_image(clipboard_image):
                                self.log_message(f"🖼️ Image received from {from_user}")
                            else:
                                self.log_message(f"❌ Failed to set image from {from_user}")
                        
                        elif content_type == "text" and clipboard_text:
                            # Clean received text to ensure proper encoding
                            try:
                                clean_text = clipboard_text.encode('utf-8', errors='ignore').decode('utf-8')
                                
                                if clean_text != self.last_clipboard:
                                    pyperclip.copy(clean_text)
                                    self.last_clipboard = clean_text
                                    
                                    preview = clean_text[:50] + "..." if len(clean_text) > 50 else clean_text
                                    self.log_message(f"📋 Text from {from_user}: {preview}")
                                    
                            except UnicodeError as e:
                                self.log_message(f"❌ Text encoding error on receive: {e}")
                                
                except json.JSONDecodeError as e:
                    self.log_message(f"❌ JSON decode error: {e}")
                except Exception as e:
                    self.log_message(f"❌ Message processing error: {e}")
                            
        except websockets.exceptions.ConnectionClosed:
            self.log_message("🔌 Connection to server lost")
        except Exception as e:
            self.log_message(f"❌ Error listening for messages: {e}")
            
    def monitor_clipboard(self):
        """Monitor clipboard changes"""
        last_image_hash = None
        
        while self.running and self.is_connected:
            try:
                # Monitor text clipboard
                try:
                    current_clipboard = pyperclip.paste()
                    
                    # Clean and normalize current clipboard for consistent comparison  
                    clean_current = current_clipboard.encode('utf-8', errors='ignore').decode('utf-8')
                    
                    if clean_current != self.last_clipboard and clean_current.strip():
                        
                        # Update last_clipboard with cleaned text  
                        self.last_clipboard = clean_current
                        
                        # Send text to server using already cleaned text
                        try:
                            # Send text to server
                            message = {
                                "type": "clipboard_sync",
                                "content_type": "text",
                                "content": clean_current
                            }
                            
                            if self.websocket:
                                try:
                                    # Ensure JSON is properly encoded
                                    json_message = json.dumps(message, ensure_ascii=False)
                                    
                                    asyncio.run_coroutine_threadsafe(
                                        self.websocket.send(json_message),
                                        self.client_loop
                                    )
                                    preview = clean_current[:50] + "..." if len(clean_current) > 50 else clean_current
                                    self.log_message(f"📤 Sent text: {preview}")
                                except Exception as e:
                                    self.log_message(f"❌ Error sending text: {e}")
                                    
                        except UnicodeError as e:
                            self.log_message(f"❌ Text encoding error: {e}")
                            
                except Exception as e:
                    self.log_message(f"❌ Error reading text clipboard: {e}")
                
                # Monitor image clipboard  
                try:
                    image_data = self.get_clipboard_image_silent()  # Silent version that doesn't log
                    if image_data:
                        # Create hash to avoid sending same image repeatedly
                        import hashlib
                        image_hash = hashlib.md5(image_data.encode()).hexdigest()
                        
                        if image_hash != last_image_hash:
                            last_image_hash = image_hash
                            
                            # Only log when we have a NEW image
                            self.log_message("📸 New image detected, sending to server")
                            
                            message = {
                                "type": "clipboard_sync",
                                "content_type": "image",
                                "content": image_data
                            }
                            
                            if self.websocket:
                                try:
                                    json_message = json.dumps(message, ensure_ascii=False)
                                    asyncio.run_coroutine_threadsafe(
                                        self.websocket.send(json_message),
                                        self.client_loop
                                    )
                                    self.log_message("📤 Sent image")
                                except Exception as e:
                                    self.log_message(f"❌ Error sending image: {e}")
                                    
                except Exception as e:
                    self.log_message(f"❌ Error reading image clipboard: {e}")
                
                time.sleep(0.5)  # Check every 500ms
                
            except Exception as e:
                self.log_message(f"❌ Clipboard monitor error: {e}")
                time.sleep(1)
                
    def get_clipboard_image_silent(self):
        """Get image from clipboard without logging every capture"""
        return self._get_clipboard_image_internal(log_capture=False)
                
    def get_clipboard_image(self):
        """Get image from clipboard with logging"""
        return self._get_clipboard_image_internal(log_capture=True)
        
    def _get_clipboard_image_internal(self, log_capture=True):
        """Get image from clipboard"""
        try:
            win32clipboard.OpenClipboard()
            try:
                # Check for different image formats
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
                    # DIB format (most common for screenshots)
                    data = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
                    
                    # DIB data starts with BITMAPINFOHEADER (40 bytes)
                    # followed by color table (if present) and bitmap data
                    if len(data) > 40:
                        try:
                            # Create PIL Image from DIB data
                            # Skip the BITMAPINFOHEADER (40 bytes)
                            image_data = data[40:]
                            
                            # Parse BITMAPINFOHEADER to get image dimensions
                            import struct
                            header = data[:40]
                            width = struct.unpack('<L', header[4:8])[0]
                            height = abs(struct.unpack('<l', header[8:12])[0])  # Height can be negative
                            bit_count = struct.unpack('<H', header[14:16])[0]
                            
                            # Calculate expected data size
                            bytes_per_line = ((width * bit_count + 31) // 32) * 4  # 32-bit aligned
                            expected_size = bytes_per_line * height
                            
                            # Validate data size
                            if len(image_data) < expected_size:
                                self.log_message(f"⚠️ Image data too small: {len(image_data)} < {expected_size}")
                                return None
                            
                            # Create a temporary BMP file in memory
                            bmp_header = b'BM'  # BMP signature
                            file_size = 14 + len(data)  # File header + DIB data
                            bmp_header += struct.pack('<L', file_size)  # File size
                            bmp_header += b'\x00\x00\x00\x00'  # Reserved
                            bmp_header += struct.pack('<L', 14 + 40)  # Offset to pixel data
                            
                            # Combine BMP header with DIB data
                            bmp_data = bmp_header + data
                            
                            # Open with PIL
                            image = Image.open(io.BytesIO(bmp_data))
                            
                            # Convert to PNG and encode as base64
                            buffer = io.BytesIO()
                            image.save(buffer, format='PNG')
                            image_b64 = base64.b64encode(buffer.getvalue()).decode()
                            
                            if log_capture:
                                self.log_message(f"📸 Captured image: {width}x{height}, {bit_count}-bit")
                            return image_b64
                            
                        except Exception as e:
                            if log_capture:
                                self.log_message(f"❌ Error processing DIB image: {e}")
                            return None
                            
                elif win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_BITMAP):
                    # Handle CF_BITMAP format
                    if log_capture:
                        self.log_message("⚠️ CF_BITMAP format not fully supported, trying alternative method")
                    return None
                    
                else:
                    # No image format available
                    return None
                    
            finally:
                win32clipboard.CloseClipboard()
                
        except Exception as e:
            if log_capture:
                self.log_message(f"❌ Error accessing clipboard for image: {e}")
            return None
            
        return None
        
    def set_clipboard_image(self, image_data):
        """Set image to clipboard"""
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            self.log_message(f"📥 Setting image to clipboard: {image.size[0]}x{image.size[1]}")
            
            # Convert to RGB if necessary (remove alpha channel)
            if image.mode in ('RGBA', 'LA'):
                # Create white background
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'RGBA':
                    background.paste(image, mask=image.split()[-1])  # Use alpha channel as mask
                else:
                    background.paste(image)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert to DIB format for clipboard
            # Create BMP in memory first
            bmp_buffer = io.BytesIO()
            image.save(bmp_buffer, format='BMP')
            bmp_data = bmp_buffer.getvalue()
            
            # Extract DIB data (skip BMP file header - first 14 bytes)
            dib_data = bmp_data[14:]
            
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, dib_data)
                self.log_message("✅ Image set to clipboard successfully")
            finally:
                win32clipboard.CloseClipboard()
                
            return True
            
        except Exception as e:
            self.log_message(f"❌ Error setting clipboard image: {e}")
            return False
            
    def hide_to_tray(self):
        """Hide window to system tray"""
        if TRAY_AVAILABLE:
            self.is_hidden = True
            self.root.withdraw()
            self.log_message("Application minimized to system tray")
            
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
        
    def quit_app(self, icon=None, item=None):
        """Quit application completely"""
        self.disconnect()
        
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
        if TRAY_AVAILABLE and self.is_connected:
            # Just hide to tray if connected
            self.hide_to_tray()
        else:
            # Ask before quitting
            if self.is_connected:
                if messagebox.askokcancel("Quit", "Client is connected. Disconnect and quit?"):
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
    
    app = ClipboardClientGUI()
    app.run()

if __name__ == "__main__":
    main()