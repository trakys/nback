import PyInstaller.__main__
import platform
import os
import shutil

# Configuration
APP_NAME = "NBackExperiment"
MAIN_SCRIPT = "nback_experiment.py"
DATA_FILES = ["sample_sheet.csv", "entitlements.plist"]
ICON_DIR = "icons"

# Platform-specific settings
system = platform.system()
ICON = None
if system == "Darwin":  # macOS
    BUNDLE_ID = "com.yourcompany.nback"
    icon_path = os.path.join(ICON_DIR, "app_icon.icns")
    if os.path.exists(icon_path):
        ICON = icon_path
elif system == "Windows":
    BUNDLE_ID = None
    icon_path = os.path.join(ICON_DIR, "app_icon.ico")
    if os.path.exists(icon_path):
        ICON = icon_path
else:  # Linux
    BUNDLE_ID = None
    icon_path = os.path.join(ICON_DIR, "app_icon.png")
    if os.path.exists(icon_path):
        ICON = icon_path

# Create minimal entitlements.plist if missing
if not os.path.exists("entitlements.plist"):
    with open("entitlements.plist", "w") as f:
        f.write("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.automation.apple-events</key>
    <true/>
</dict>
</plist>""")

# Prepare build command
cmd = [
    MAIN_SCRIPT,
    f"--name={APP_NAME}",
    "--clean",
    "--noconfirm"
]

# Add data files
for file in DATA_FILES:
    if os.path.exists(file):
        cmd += ["--add-data", f"{file}:."]

# Add platform-specific options
if system == "Darwin":
    cmd += [
        "--windowed",
        "--osx-bundle-identifier", BUNDLE_ID,
        "--osx-entitlements-file", "entitlements.plist"
    ]
    if ICON:  # Only add icon if it exists
        cmd += ["--icon", ICON]
elif system == "Windows":
    cmd += [
        "--onefile",
        "--windowed"
    ]
    if ICON:  # Only add icon if it exists
        cmd += ["--icon", ICON]
else:  # Linux
    cmd += [
        "--onefile"
    ]
    if ICON:  # Only add icon if it exists
        cmd += ["--icon", ICON]

# Run PyInstaller
print(f"Building for {system}...")
print("Command:", " ".join(cmd))
PyInstaller.__main__.run(cmd)

# Cleanup
print("Build complete! Output in dist/ directory")
if os.path.exists("build"):
    shutil.rmtree("build")
