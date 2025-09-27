# 📋 Clipboard Sync - GUI Edition

Instantly sync clipboards (text AND images) between computers with a beautiful, invisible GUI interface. Copy on one computer**🌐 Environment Variables** (Override .env file)
```cmd
set CLIPBOARD_USERS=admin:mypassword,user1:password1,user2:password2
```

**🔒 Benefits:**
- Uses your existing .env file automatically
- No code changes needed
- Environment variables override .env file
- Safe for version control completely seamless!

## ✨ Key Features

- 📝 **Text Sync**: Copy any text content between devices instantly
- 🖼️ **Image Sync**: Copy images (PNG, JPG, etc.) between devices seamlessly
- �️ **Invisible GUI**: Clean system tray interface with no terminal windows
- 🌐 **Internet Ready**: Works locally OR over internet with ngrok tunnels
- 🔒 **Secure**: Password-protected with user authentication
- ⚡ **Real-time**: Instant synchronization across all devices
- 👥 **Multi-user**: Support for multiple users with individual accounts

## 🎯 Super Quick Start

### 1. Server Computer (Host)
```cmd
# Navigate to server folder
cd server

# Start server invisibly - double-click this file:
start_invisible.vbs
```

### 2. Client Computer(s)
```cmd
# Navigate to client folder  
cd client

# Start client invisibly - double-click this file:
start_client_invisible.vbs
```

### 3. Connect & Sync
1. **Find system tray icons**: Look for server (blue "CS") and client (green "CC") icons
2. **Connect client**: Right-click client tray → "Connect" 
3. **Login**: Use `admin`/`admin123` or any default user
4. **Start syncing**: Copy/paste works instantly across all devices!

## 🎨 GUI Features

### **100% Invisible Operation**
- No terminal windows or command prompts
- Clean system tray interface
- Silent startup and background operation

### **Smart Interface**
- **Server GUI**: Start/stop server, view public URLs, monitor connections
- **Client GUI**: Connect/disconnect, server configuration, activity logs
- **System Tray**: Full control from system tray menus

### **Professional Experience**
- Real-time status indicators
- Automatic error handling and reconnection
- Activity logging with timestamps
- Clean credential management
## 📁 Project Structure

```
clipboard-sync/
│
├── server/                          # Server files
│   ├── server.py                   # Main server (unchanged)
│   ├── server_tray_gui.py          # GUI with system tray
│   ├── start_invisible.vbs         # 🚀 MAIN SERVER LAUNCHER
│   ├── force_stop_server.bat       # Emergency stop
│   ├── ngrok.yml                   # Internet tunnel config
│   └── requirements.txt            # Dependencies
│
├── client/                          # Client files  
│   ├── client.py                   # Original client
│   ├── client_gui.py               # GUI with system tray
│   ├── start_client_invisible.vbs  # 🚀 MAIN CLIENT LAUNCHER
│   ├── force_stop_client.bat       # Emergency stop
│   ├── config.json                 # Server connection config
│   └── requirements.txt            # Dependencies
│
└── README.md                       # This file
```

## 🔐 Default User Accounts

| Username | Password    | Description |
|----------|-------------|-------------|
| admin    | admin123    | Administrator |
| user1    | user123     | Standard user |
| user2    | pass123     | Standard user |
| guest    | guest123    | Guest access |

## 🛠️ How It Works

### **Local Network Mode**
1. **Server** runs on host computer with GUI in system tray
2. **Clients** connect from other devices on same network  
3. **Real-time sync** - copy on any device, paste on all others

### **Internet Mode (with ngrok)**
1. **Server** creates secure public tunnel automatically
2. **Clients** connect from anywhere in the world
3. **Same seamless experience** over internet

## 🎮 Daily Usage

### **Starting Up**
1. **Server**: Double-click `server/start_invisible.vbs`
2. **Client(s)**: Double-click `client/start_client_invisible.vbs`
3. **Connect**: Right-click client tray icon → "Connect"
4. **Login**: Enter username/password
5. **Sync away**: Copy/paste works instantly!

### **Managing**
- **View activity**: Right-click tray icons → "Show" 
- **Check status**: Look at tray icon tooltips
- **Disconnect**: Right-click client → "Disconnect"
- **Stop server**: Right-click server → "Stop Server"

### **Emergency Stop**
- Run `force_stop_server.bat` or `force_stop_client.bat` if needed

## ⚙️ Advanced Configuration

### **Change Server URL**
Edit `client/config.json`:
```json
{
  "server_url": "ws://192.168.1.100:8765"
}
```

### **Internet Access (ngrok)**
1. Install ngrok: https://ngrok.com/download
2. Get auth token from ngrok.com
3. Configure: `ngrok config add-authtoken YOUR_TOKEN`
4. Server GUI will show public URL automatically

### **Custom Users**

**🎯 Recommended: .env File** (Your existing format works!)
Your existing `server/.env` format is supported:
```env
USER1_NAME=admin
USER1_PASS=admin123
USER2_NAME=user1  
USER2_PASS=password123
USER3_NAME=user2
USER3_PASS=password456
USER4_NAME=guest
USER4_PASS=guest789
```

**🔧 Alternative .env Formats** (Also supported)
```env
# Option 1: Single variable with multiple users
CLIPBOARD_USERS=admin:mypassword,user1:password1,user2:password2

# Option 2: Individual user variables
CLIPBOARD_USER_ADMIN=mypassword
CLIPBOARD_USER_USER1=password1
CLIPBOARD_USER_USER2=password2
```

**� Alternative: Environment Variables**
```cmd
set CLIPBOARD_USERS=admin:mypassword,user1:password1,user2:password2
# or
set CLIPBOARD_USER_ADMIN=mypassword
set CLIPBOARD_USER_USER1=password1
```

**📝 Last Resort: Edit Code** (Less secure)
Edit `server/server.py` user dictionary (fallback only):
```python
self.users = {
    "your_username": "your_password",
    "another_user": "another_pass"
}
```

**🔒 Benefits:**
- Passwords not stored in source code
- Easy deployment without code changes
- Environment variables override .env file
- Safe for version control

## 🛡️ Security Features

- **bcrypt password hashing** - Passwords never stored in plain text
- **Rate limiting** - Prevents spam/abuse (30 requests/minute)
- **IP blocking** - Auto-blocks after 5 failed login attempts  
- **Message size limits** - Prevents memory attacks (10MB limit)
- **Connection monitoring** - Real-time connection tracking

## 🔧 Technical Requirements

### **Dependencies (Auto-installed)**
- **pystray** - System tray functionality
- **Pillow** - Image processing
- **websockets** - Real-time communication
- **pyperclip** - Clipboard access
- **pywin32** - Windows clipboard images

### **System Requirements**
- **Windows 10/11** (primary support)
- **Python 3.7+** installed
- **Same WiFi network** (local mode) OR **Internet** (ngrok mode)

## 🆘 Troubleshooting

### **Connection Issues**
- ✅ Check both devices on same WiFi
- ✅ Verify server is running (check tray icon)
- ✅ Confirm correct server URL in client config
- ✅ Try restarting both server and client

### **GUI Not Appearing**
- ✅ Look for system tray icons (blue "CS" server, green "CC" client)
- ✅ Right-click tray icon → "Show"
- ✅ Run `pip install pystray pillow` if dependencies missing

### **Emergency Stops**
- ✅ Use `force_stop_server.bat` or `force_stop_client.bat`
- ✅ Check Task Manager for python.exe processes
- ✅ Restart computer if all else fails

---

## 🚀 Ready to Sync?

**Just double-click these files and start syncing:**
- **Server**: `server/start_invisible.vbs` 
- **Client**: `client/start_client_invisible.vbs`

**It's that simple!** ✨