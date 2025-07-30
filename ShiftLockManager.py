import os
import sys
import shutil
import threading
import webbrowser
import time
import subprocess
from PIL import Image, ImageDraw
from tkinter import filedialog, Tk
import pystray
from pystray import MenuItem as Item

# === Resource Handling ===
def resource_path(relative_path):
    """Get absolute path to resource for both dev and PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# === Roblox Path Detection ===
def find_roblox_player_path():
    """Find the correct Roblox Player installation path"""
    appdata = os.getenv('LOCALAPPDATA')
    if not appdata:
        return None
    
    versions_path = os.path.join(appdata, "Roblox", "Versions")
    if not os.path.exists(versions_path):
        return None
    
    # Find all version folders
    version_folders = [
        f for f in os.listdir(versions_path) 
        if f.startswith('version-') and 
        os.path.isdir(os.path.join(versions_path, f))
    ]
    
    if not version_folders:
        return None
    
    # Sort by creation time (newest first)
    version_folders.sort(key=lambda f: os.path.getctime(os.path.join(versions_path, f)), reverse=True)
    
    # Check each version folder for Player (not Studio)
    for version in version_folders:
        version_path = os.path.join(versions_path, version)
        
        # Skip Studio versions
        if os.path.exists(os.path.join(version_path, "RobloxStudioBeta.exe")):
            continue
            
        # Verify Player executable exists
        if os.path.exists(os.path.join(version_path, "RobloxPlayerBeta.exe")):
            cursor_path = os.path.join(version_path, "content", "textures", "MouseLockedCursor.png")
            if os.path.exists(cursor_path):
                return cursor_path
    
    return None

# === Constants ===
ICON_FILE = resource_path("Logo.png")
ORIGINAL_CURSOR = resource_path("OriginalMouseLockedCursor.png")
CURSOR_PATH = find_roblox_player_path()  # Auto-detected path
ROBLOX_PROCESS_NAME = "RobloxPlayerBeta.exe"

# Global variables
tray_icon = None

# === Roblox Functions ===
def is_roblox_running():
    """Check if Roblox is currently running"""
    try:
        output = subprocess.check_output('tasklist', shell=True, text=True)
        return ROBLOX_PROCESS_NAME in output
    except:
        return False

def force_cursor_reload():
    """Force Roblox to reload the cursor texture"""
    if not CURSOR_PATH or not os.path.exists(CURSOR_PATH):
        return False
        
    if not is_roblox_running():
        return False
        
    try:
        # Technique 1: Modify file timestamp
        current_time = time.time()
        os.utime(CURSOR_PATH, (current_time, current_time))
        
        # Technique 2: Temporary rename
        temp_path = CURSOR_PATH + ".tmp"
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        os.rename(CURSOR_PATH, temp_path)
        time.sleep(0.1)
        os.rename(temp_path, CURSOR_PATH)
        
        return True
    except Exception as e:
        print(f"Cursor reload error: {e}")
        return False

# === Cursor Actions ===
def upload_cursor():
    """Handle cursor upload from user"""
    if not CURSOR_PATH:
        show_notification("❌ Roblox installation not found", "Error")
        return
    
    root = Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select Custom Shiftlock", 
        filetypes=[("Image files", "*.png;*.jpg;*.jpeg")]
    )
    root.destroy()
    
    if not file_path:
        return

    try:
        img = Image.open(file_path).convert("RGBA").resize((32, 32), Image.LANCZOS)
        
        # Create directory if needed
        os.makedirs(os.path.dirname(CURSOR_PATH), exist_ok=True)
        
        # Create backup if none exists
        backup = CURSOR_PATH + ".bak"
        if not os.path.exists(backup):
            if os.path.exists(ORIGINAL_CURSOR):
                shutil.copy(ORIGINAL_CURSOR, backup)
            else:
                # Create default cursor as backup
                default_img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
                draw = ImageDraw.Draw(default_img)
                draw.rectangle([0, 0, 31, 31], outline="white")
                default_img.save(backup)

        img.save(CURSOR_PATH)
        
        if force_cursor_reload():
            show_notification("✅ Custom cursor applied! Changes should appear shortly", "Success")
        else:
            show_notification("✅ Custom cursor applied! Restart Roblox if not visible", "Success")
    except Exception as e:
        show_notification(f"❌ Failed: {str(e)[:50]}", "Error")

def restore_original():
    """Restore the original cursor"""
    if not CURSOR_PATH:
        show_notification("❌ Roblox installation not found", "Error")
        return
    
    try:
        backup = CURSOR_PATH + ".bak"
        
        # Try to restore from backup first
        if os.path.exists(backup):
            shutil.copy(backup, CURSOR_PATH)
            message = "from backup"
        # Fall back to included original
        elif os.path.exists(ORIGINAL_CURSOR):
            shutil.copy(ORIGINAL_CURSOR, CURSOR_PATH)
            message = "from app resources"
        # Create default if nothing else
        else:
            default_img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
            draw = ImageDraw.Draw(default_img)
            draw.rectangle([0, 0, 31, 31], outline="white")
            default_img.save(CURSOR_PATH)
            message = "default cursor created"
        
        if force_cursor_reload():
            show_notification(f"✅ Original cursor restored ({message})! Changes visible shortly", "Success")
        else:
            show_notification(f"✅ Original cursor restored ({message})! Restart Roblox if needed", "Success")
    except Exception as e:
        show_notification(f"❌ Failed: {str(e)[:50]}", "Error")

# === UI Functions ===
def show_notification(message, title):
    """Show system tray notification"""
    global tray_icon
    if tray_icon:
        tray_icon.notify(message, title)

def open_github():
    """Open GitHub repository"""
    webbrowser.open("https://github.com/ItsSomeBoringNerd/ShiftlockCursorManager/")

def quit_app(icon, item):
    """Quit the application"""
    icon.stop()

# === Tray Icon Setup ===
def setup_icon():
    """Create and configure the system tray icon"""
    global tray_icon
    
    # Load or create icon
    try:
        icon_img = Image.open(ICON_FILE)
    except:
        # Create fallback icon
        icon_img = Image.new('RGB', (64, 64), color=(40, 80, 120))
        draw = ImageDraw.Draw(icon_img)
        draw.text((10, 25), "SL", fill="white")
    
    icon_img = icon_img.resize((64, 64), Image.LANCZOS)

    # Create tray icon
    tray_icon = pystray.Icon("ShiftLockChanger")
    tray_icon.icon = icon_img
    tray_icon.title = "ShiftLock Cursor Manager"

    # Create menu
    tray_icon.menu = pystray.Menu(
        Item("Upload Shiftlock", lambda: threading.Thread(target=upload_cursor).start()),
        Item("Restore Original", lambda: threading.Thread(target=restore_original).start()),
        Item("Visit GitHub", lambda: threading.Thread(target=open_github).start()),
        Item("Exit", quit_app)
    )

    # Show startup notification
    if CURSOR_PATH:
        show_notification("✅ Ready! ShiftLock Manager is active", "Started")
    else:
        show_notification("⚠️ Roblox not detected. Some features may not work", "Warning")
    
    tray_icon.run()

if __name__ == "__main__":
    setup_icon()