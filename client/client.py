#!/usr/bin/env python3
"""
Clipboard Sync Client
"""

import asyncio
import websockets
import json
import pyperclip
import logging
import time
import sys
import getpass
from typing import Optional
import threading
import base64
import io
from PIL import Image
import win32clipboard
import win32con


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class ClipboardClient:
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.last_clipboard = ""
        self.user_id = ""
        self.running = True
        self.last_ping = time.time()
        
    def get_credentials(self):
        print("=" * 50)
        print("   CLIPBOARD SYNC CLIENT")
        print("=" * 50)
        print()
        
        self.user_id = input("Enter your User ID: ").strip()
        if not self.user_id:
            print("Error: User ID cannot be empty!")
            sys.exit(1)
            
        password = getpass.getpass("Enter your Password: ").strip()
        if not password:
            print("Error: Password cannot be empty!")
            sys.exit(1)
            
        return self.user_id, password
    
    async def connect_to_server(self):
        user_id, password = self.get_credentials()
        
        try:
            print(f"\nConnecting to server: {self.server_url}")
            self.websocket = await websockets.connect(
                self.server_url,
                ping_interval=30,
                ping_timeout=10
            )
            
            # Send authentication
            auth_message = {
                "type": "auth",
                "user_id": user_id,
                "password": password
            }
            
            await self.websocket.send(json.dumps(auth_message))
            
            # Wait for authentication response
            response = await self.websocket.recv()
            auth_result = json.loads(response)
            
            if auth_result.get("type") == "auth_success":
                self.is_connected = True
                print(f"✅ {auth_result.get('message')}")
                print(f"🔄 Clipboard sync is now active!")
                print("💡 Copy any text or image to sync across your devices.")
                print("🖼️ Supports: Text, PNG, JPG, and other image formats.")
                print("🚪 Press Ctrl+C to disconnect")
                print("-" * 50)
                return True
            else:
                print(f"❌ Authentication failed: {auth_result.get('message')}")
                return False
                
        except websockets.exceptions.InvalidURI:
            print(f"❌ Error: Invalid server URL: {self.server_url}")
            return False
        except websockets.exceptions.ConnectionClosed:
            print("❌ Error: Connection to server was closed")
            return False
        except Exception as e:
            print(f"❌ Error connecting to server: {e}")
            return False
    
    async def listen_for_messages(self):
        try:
            async for message in self.websocket:
                data = json.loads(message)
                message_type = data.get("type")
                
                if message_type == "clipboard_sync":
                    content_type = data.get("content_type", "text")
                    clipboard_text = data.get("text", "")
                    clipboard_image = data.get("image", "")
                    from_user = data.get("from_user", "Unknown")
                    
                    if content_type == "image" and clipboard_image:
                        # Handle image clipboard
                        if self.set_clipboard_image(clipboard_image):
                            print(f"🖼️ Image received from {from_user}")
                        else:
                            print(f"❌ Failed to set image from {from_user}")
                    
                    elif content_type == "text" and clipboard_text:
                        # Handle text clipboard  
                        if clipboard_text != self.last_clipboard:
                            pyperclip.copy(clipboard_text)
                            self.last_clipboard = clipboard_text
                            
                            # Show notification
                            preview = clipboard_text[:50] + "..." if len(clipboard_text) > 50 else clipboard_text
                            print(f"📋 Text received from {from_user}: {preview}")
                
                elif message_type == "clipboard_history":
                    # Note: History handling removed as server no longer sends it
                    pass
                    
                elif message_type == "pong":
                    # Server responded to ping
                    pass
                    
        except websockets.exceptions.ConnectionClosed:
            print("\n🔌 Connection to server lost")
            self.is_connected = False
        except json.JSONDecodeError:
            logger.error("Received invalid JSON from server")
        except Exception as e:
            logger.error(f"Error listening for messages: {e}")
            self.is_connected = False
    
    def get_clipboard_image(self):
        try:
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIB):
                    data = win32clipboard.GetClipboardData(win32con.CF_DIB)
                    img = Image.open(io.BytesIO(data))
                    
                    buffer = io.BytesIO()
                    img.save(buffer, format='PNG')
                    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    return f"data:image/png;base64,{img_base64}"
                    
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            logger.debug(f"No image in clipboard or error: {e}")
        return None
    
    def set_clipboard_image(self, base64_data):
        try:
            if base64_data.startswith("data:image/"):
                base64_str = base64_data.split("base64,")[1]
            else:
                base64_str = base64_data
                
            img_data = base64.b64decode(base64_str)
            img = Image.open(io.BytesIO(img_data))
            
            output = io.BytesIO()
            img.convert('RGB').save(output, 'BMP')
            data = output.getvalue()[14:]
            
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_DIB, data)
            finally:
                win32clipboard.CloseClipboard()
                
            return True
            
        except Exception as e:
            logger.error(f"Error setting image to clipboard: {e}")
            return False
    
    def monitor_clipboard(self):
        last_text_clipboard = ""
        last_image_hash = ""
        
        while self.running and self.is_connected:
            try:
                current_text = pyperclip.paste()
                text_changed = (current_text != last_text_clipboard and 
                               current_text.strip() and 
                               not current_text.startswith("data:image"))
                
                current_image = self.get_clipboard_image()
                image_hash = str(hash(current_image)) if current_image else ""
                image_changed = (current_image and image_hash != last_image_hash)
                
                if text_changed or image_changed:
                    if self.websocket and not self.websocket.closed:
                        message = {
                            "type": "clipboard_update",
                            "text": current_text if text_changed else "",
                            "image": current_image if image_changed else ""
                        }
                        
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(self.websocket.send(json.dumps(message)))
                            
                            if text_changed:
                                last_text_clipboard = current_text
                                preview = current_text[:50] + "..." if len(current_text) > 50 else current_text
                                print(f"📤 Text sent: {preview}")
                            
                            if image_changed:
                                last_image_hash = image_hash
                                print(f"🖼️ Image sent ({len(current_image)} chars)")
                                
                        except Exception as e:
                            logger.error(f"Error sending clipboard update: {e}")
                        finally:
                            loop.close()
                
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error monitoring clipboard: {e}")
                time.sleep(1)
    
    async def send_ping(self):
        while self.is_connected:
            try:
                if self.websocket and not self.websocket.closed:
                    await self.websocket.send(json.dumps({"type": "ping"}))
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Error sending ping: {e}")
                break
    
    async def run(self):
        if not await self.connect_to_server():
            return
        
        
        try:
            self.last_clipboard = pyperclip.paste()
        except:
            self.last_clipboard = ""
        
        clipboard_thread = threading.Thread(target=self.monitor_clipboard, daemon=True)
        clipboard_thread.start()
        
        try:
            await asyncio.gather(
                self.listen_for_messages(),
                self.send_ping()
            )
        except KeyboardInterrupt:
            print("\n👋 Disconnecting from clipboard sync...")
        except Exception as e:
            print(f"\n❌ Error: {e}")
        finally:
            self.running = False
            self.is_connected = False
            if self.websocket:
                await self.websocket.close()

def main():
    server_url = "ws://172.20.42.107:8765"
    
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            server_url = config.get("server_url", server_url)
    except FileNotFoundError:
        config = {"server_url": server_url}
        with open("config.json", "w") as f:
            json.dump(config, f, indent=2)
        print(f"Created config.json with default server URL: {server_url}")
    except Exception as e:
        print(f"Warning: Could not read config.json: {e}")
    
    print(f"Using server URL: {server_url}")
    print("💡 You can change the server URL in config.json")
    print()
    
    client = ClipboardClient(server_url)
    
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Client error: {e}")

if __name__ == "__main__":
    main()