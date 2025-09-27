#!/usr/bin/env python3
"""
Clipboard Sync Server - Internet Accessible with Security
"""

import asyncio
import websockets
import json
import logging
import time
import os
from typing import Dict, Set
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleClipboardServer:
    
    def __init__(self):
        self.users = self._load_users_from_env()
        
        self.connected_clients: Dict[websockets.WebSocketServerProtocol, str] = {}
        
        # Security features for public exposure
        self.rate_limits: Dict[str, list] = {}  # IP -> [timestamp, timestamp, ...]
        self.failed_attempts: Dict[str, int] = {}  # IP -> fail count
        self.blocked_ips: Set[str] = set()
        self.max_requests_per_minute = 30
        self.max_failed_attempts = 5
        self.max_message_size = 10 * 1024 * 1024  # 10MB limit
        
        logger.info(f"Loaded {len(self.users)} users: {list(self.users.keys())}")
        logger.info("Security features enabled for internet access")
    
    def _load_users_from_env(self):
        """Load users from .env file and environment variables"""
        users = {}
        env_vars = {}
        
        # Try to load from .env file first
        env_file_path = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(env_file_path):
            try:
                with open(env_file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")  # Remove quotes if present
                            env_vars[key] = value
                
                # Handle CLIPBOARD_USERS format
                if 'CLIPBOARD_USERS' in env_vars:
                    try:
                        for user_pair in env_vars['CLIPBOARD_USERS'].split(','):
                            if ':' in user_pair:
                                username, password = user_pair.strip().split(':', 1)
                                if username and password:
                                    users[username] = password
                        logger.info(f"Loaded users from CLIPBOARD_USERS in .env file")
                    except Exception as e:
                        logger.error(f"Error parsing CLIPBOARD_USERS from .env: {e}")
                
                # Handle individual CLIPBOARD_USER_ variables
                for key, value in env_vars.items():
                    if key.startswith('CLIPBOARD_USER_') and value:
                        username = key[15:].lower()  # Remove 'CLIPBOARD_USER_' prefix
                        if username:
                            users[username] = value
                
                # Handle existing format: USER1_NAME/USER1_PASS, USER2_NAME/USER2_PASS, etc.
                user_names = {}
                user_passwords = {}
                
                for key, value in env_vars.items():
                    if key.endswith('_NAME') and value:
                        user_id = key[:-5]  # Remove '_NAME' suffix
                        user_names[user_id] = value
                    elif key.endswith('_PASS') and value:
                        user_id = key[:-5]  # Remove '_PASS' suffix  
                        user_passwords[user_id] = value
                
                # Match names with passwords
                for user_id in user_names:
                    if user_id in user_passwords:
                        username = user_names[user_id]
                        password = user_passwords[user_id]
                        users[username] = password
                
                if users:
                    logger.info(f"Loaded {len(users)} users from .env file: {env_file_path}")
                    
            except Exception as e:
                logger.error(f"Error reading .env file: {e}")
        
        # Also check system environment variables (these take precedence)
        env_users = os.getenv('CLIPBOARD_USERS', '')
        if env_users:
            try:
                for user_pair in env_users.split(','):
                    if ':' in user_pair:
                        username, password = user_pair.strip().split(':', 1)
                        if username and password:
                            users[username] = password
                logger.info(f"Loaded users from CLIPBOARD_USERS environment variable")
            except Exception as e:
                logger.error(f"Error parsing CLIPBOARD_USERS: {e}")
        
        # Check for individual environment variables (CLIPBOARD_USER_<username>=password)
        for key, value in os.environ.items():
            if key.startswith('CLIPBOARD_USER_') and value:
                username = key[15:].lower()  # Remove 'CLIPBOARD_USER_' prefix
                if username:
                    users[username] = value
        
        # Fallback to default users if no users found
        if not users:
            users = {
                "admin": "admin123",
                "user1": "user123", 
                "user2": "pass123",
                "guest": "guest123"
            }
            logger.warning("No users found in .env file or environment variables, using default users")
            logger.warning("Add users to your .env file using existing format or: CLIPBOARD_USERS='user1:pass1,user2:pass2'")
        
        return users
    
    def _is_rate_limited(self, client_ip: str) -> bool:
        """Check if client is rate limited"""
        now = time.time()
        minute_ago = now - 60
        
        # Clean old entries
        if client_ip in self.rate_limits:
            self.rate_limits[client_ip] = [t for t in self.rate_limits[client_ip] if t > minute_ago]
        
        # Check current rate
        requests_in_minute = len(self.rate_limits.get(client_ip, []))
        
        if requests_in_minute >= self.max_requests_per_minute:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return True
        
        # Record this request
        if client_ip not in self.rate_limits:
            self.rate_limits[client_ip] = []
        self.rate_limits[client_ip].append(now)
        
        return False
    
    def _is_blocked(self, client_ip: str) -> bool:
        """Check if IP is blocked due to too many failed attempts"""
        return client_ip in self.blocked_ips
    
    def _record_failed_attempt(self, client_ip: str):
        """Record a failed authentication attempt"""
        self.failed_attempts[client_ip] = self.failed_attempts.get(client_ip, 0) + 1
        
        if self.failed_attempts[client_ip] >= self.max_failed_attempts:
            self.blocked_ips.add(client_ip)
            logger.warning(f"Blocked IP {client_ip} after {self.max_failed_attempts} failed attempts")
    
    def _record_successful_auth(self, client_ip: str):
        """Reset failed attempts counter on successful auth"""
        self.failed_attempts.pop(client_ip, None)
    
    def _validate_input(self, content: str, max_length: int = None) -> bool:
        if max_length is None:
            max_length = self.max_message_size
            
        if not content or len(content) > max_length:
            return False
        return True
    
    def _is_image_data(self, content: str) -> bool:
        return content.startswith("data:image/") and "base64," in content
    
    async def authenticate_user(self, websocket, user_id: str, password: str, client_ip: str) -> bool:
        if user_id in self.users and self.users[user_id] == password:
            self.connected_clients[websocket] = user_id
            self._record_successful_auth(client_ip)
            logger.info(f"User {user_id} authenticated from {client_ip}")
            return True
        else:
            self._record_failed_attempt(client_ip)
            logger.warning(f"Failed authentication attempt for {user_id} from {client_ip}")
        return False
    
    async def handle_client(self, websocket, path):
        client_ip = websocket.remote_address[0]
        logger.info(f"New connection from {client_ip}")
        
        # Security checks
        if self._is_blocked(client_ip):
            logger.warning(f"Blocked IP {client_ip} attempted connection")
            await websocket.close(code=1008, reason="Blocked")
            return
        
        if self._is_rate_limited(client_ip):
            logger.warning(f"Rate limited connection from {client_ip}")
            await websocket.close(code=1008, reason="Rate limited")
            return
        
        try:
            auth_message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
            
            # Handle UTF-8 encoding for auth message
            if isinstance(auth_message, bytes):
                auth_message = auth_message.decode('utf-8', errors='ignore')
                
            auth_data = json.loads(auth_message)
            
            if auth_data.get("type") != "auth":
                await websocket.send(json.dumps({
                    "type": "error", 
                    "message": "First message must be authentication"
                }, ensure_ascii=False))
                return
            
            user_id = auth_data.get("user_id", "").strip()
            password = auth_data.get("password", "").strip()
            
            if not user_id or not password:
                await websocket.send(json.dumps({
                    "type": "auth_error", 
                    "message": "Missing credentials"
                }, ensure_ascii=False))
                return
            
            if not await self.authenticate_user(websocket, user_id, password, client_ip):
                await websocket.send(json.dumps({
                    "type": "auth_failed",
                    "message": "Invalid credentials"
                }, ensure_ascii=False))
                return
            
            await websocket.send(json.dumps({
                "type": "auth_success",
                "message": f"Welcome {user_id}! Clipboard sync active."
            }, ensure_ascii=False))
            
            logger.info(f"User {user_id} connected. Total: {len(self.connected_clients)}")
            
            async for message in websocket:
                await self.handle_message(websocket, message)
                
        except asyncio.TimeoutError:
            logger.warning(f"Auth timeout: {client_ip}")
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_ip}")
        except Exception as e:
            logger.error(f"Error with {client_ip}: {e}")
        finally:
            if websocket in self.connected_clients:
                user_id = self.connected_clients[websocket]
                del self.connected_clients[websocket]
                logger.info(f"User {user_id} disconnected")
    
    async def handle_message(self, sender_websocket, message):
        try:
            # Handle UTF-8 encoding properly
            if isinstance(message, bytes):
                message = message.decode('utf-8', errors='ignore')
                
            data = json.loads(message)
            message_type = data.get("type")
            
            # Handle both old format (clipboard_update) and new format (clipboard_sync)
            if message_type in ["clipboard_update", "clipboard_sync"]:
                content_to_sync = None
                content_type = None
                
                # New format from GUI client
                if message_type == "clipboard_sync":
                    content_type = data.get("content_type", "text")
                    content_to_sync = data.get("content", "")
                    
                # Old format from original client  
                elif message_type == "clipboard_update":
                    clipboard_text = data.get("text", "").strip()
                    clipboard_image = data.get("image", "").strip()
                    
                    if clipboard_image and self._is_image_data(clipboard_image):
                        if self._validate_input(clipboard_image):
                            content_to_sync = clipboard_image
                            content_type = "image"
                    elif clipboard_text:
                        if self._validate_input(clipboard_text):
                            content_to_sync = clipboard_text
                            content_type = "text"
                
                # Validate content
                if not content_to_sync or not content_type:
                    return
                    
                # Clean and validate UTF-8 encoding
                try:
                    if content_type == "text":
                        content_to_sync = content_to_sync.encode('utf-8', errors='ignore').decode('utf-8')
                        if not self._validate_input(content_to_sync):
                            logger.warning("Rejected clipboard update: failed validation")
                            return
                    elif content_type == "image":
                        if not self._is_image_data(content_to_sync) or not self._validate_input(content_to_sync):
                            logger.warning("Rejected image update: failed validation")
                            return
                except UnicodeError as e:
                    logger.error(f"Unicode encoding error: {e}")
                    return
                
                sender_user = self.connected_clients.get(sender_websocket, "Unknown")
                
                if content_type == "image":
                    logger.info(f"Image from {sender_user}: {len(content_to_sync)} chars (base64)")
                else:
                    logger.info(f"Text from {sender_user}: {len(content_to_sync)} chars")
                
                # Create broadcast message with proper UTF-8 encoding
                broadcast_message = json.dumps({
                    "type": "clipboard_sync",
                    "content_type": content_type,
                    "text": content_to_sync if content_type == "text" else "",
                    "image": content_to_sync if content_type == "image" else "",
                    "from_user": sender_user
                }, ensure_ascii=False)
                
                # Broadcast to all other clients
                for client_websocket, user_id in list(self.connected_clients.items()):
                    if client_websocket != sender_websocket:
                        try:
                            await client_websocket.send(broadcast_message)
                        except Exception as e:
                            logger.warning(f"Failed to send to {user_id}: {e}")
                            if client_websocket in self.connected_clients:
                                del self.connected_clients[client_websocket]
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def start_server(self, host="0.0.0.0", port=8765):
        logger.info(f"Starting clipboard sync server on {host}:{port}")
        
        server = await websockets.serve(self.handle_client, host, port)
        logger.info("Server started! Waiting for connections...")
        await server.wait_closed()

def main():
    try:
        server = SimpleClipboardServer()
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")

if __name__ == "__main__":
    main()