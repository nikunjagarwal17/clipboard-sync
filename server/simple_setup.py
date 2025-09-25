#!/usr/bin/env python3
"""
Simple Setup Script for 4-User Clipboard Sync Server
Creates basic environment configuration for exactly 4 users
"""

import os
import secrets
import string

def generate_secret_key(length=32):
    """Generate a simple secret key"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def simple_setup():
    """Simple setup for 4 fixed users"""
    print("\n" + "="*50)
    print("    SIMPLE CLIPBOARD SYNC SETUP")
    print("="*50)
    
    # Check if .env already exists
    if os.path.exists('.env'):
        overwrite = input("\n.env file already exists. Overwrite? (y/N): ").lower()
        if overwrite != 'y':
            print("Setup cancelled.")
            return
    
    print("\nSetting up simple 4-user configuration...")
    
    # Generate secret key
    secret_key = generate_secret_key()
    
    # Get server configuration
    print("\n--- Server Configuration ---")
    port = input("Server port (default: 8765): ").strip() or "8765"
    
    # Get user credentials
    print("\n--- User Configuration (4 users) ---")
    users = []
    
    default_users = [
        ("admin", "admin123"),
        ("user1", "password123"),
        ("user2", "password456"),
        ("guest", "guest789")
    ]
    
    print("Configure 4 users (press Enter to use defaults):")
    
    for i, (default_name, default_pass) in enumerate(default_users, 1):
        print(f"\nUser {i}:")
        name = input(f"  Username (default: {default_name}): ").strip() or default_name
        password = input(f"  Password (default: {default_pass}): ").strip() or default_pass
        users.append((name, password))
    
    # Create .env file
    env_content = f"""# Simple Clipboard Sync Server Configuration
# Generated on {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# Server Configuration
PORT={port}

# Security Settings
SECRET_KEY={secret_key}

# Fixed User Authentication (4 Users)
USER1_NAME={users[0][0]}
USER1_PASS={users[0][1]}

USER2_NAME={users[1][0]}
USER2_PASS={users[1][1]}

USER3_NAME={users[2][0]}
USER3_PASS={users[2][1]}

USER4_NAME={users[3][0]}
USER4_PASS={users[3][1]}

# Connection Settings
MAX_CONNECTIONS=4

# Logging
LOG_LEVEL=INFO
"""
    
    # Write .env file
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print(f"\n✅ Simple configuration saved to .env")
    print(f"✅ Created 4 users")
    print(f"✅ Server will run on port {port}")
    
    print("\n" + "="*50)
    print("    SETUP COMPLETE!")
    print("="*50)
    print("\nYour 4 users:")
    for i, (username, password) in enumerate(users, 1):
        print(f"  {i}. {username} / {password}")
    
    print(f"\nTo start the server:")
    print(f"  Local: python server.py")
    print(f"  Deploy: Use render.yaml, railway.toml, or fly.toml")
    print(f"\n⚠️  Change default passwords for production!")

def main():
    """Main setup function"""
    if not os.path.exists('server.py'):
        print("Error: This script must be run from the server directory!")
        print("Please navigate to the server directory and try again.")
        return
    
    try:
        simple_setup()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
    except Exception as e:
        print(f"\nError during setup: {e}")

if __name__ == "__main__":
    main()