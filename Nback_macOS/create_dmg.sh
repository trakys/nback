#!/bin/bash

# Configuration
APP_NAME="NBackExperiment"
VOLUME_NAME="NBack"
DMG_NAME="NBack_Installer"
BACKGROUND_IMAGE="background.png"
APP_BUNDLE="NBackExperiment.app" 
OUTPUT_DIR="dist"

# Clean previous builds
rm -f "${OUTPUT_DIR}/${DMG_NAME}.dmg"
rm -rf "${OUTPUT_DIR}/${VOLUME_NAME}"

# Create directory structure
mkdir -p "${OUTPUT_DIR}/${VOLUME_NAME}"
cp -R "${APP_BUNDLE}" "${OUTPUT_DIR}/${VOLUME_NAME}/"

# Create .background directory and copy image
mkdir -p "${OUTPUT_DIR}/${VOLUME_NAME}/.background"
cp "${BACKGROUND_IMAGE}" "${OUTPUT_DIR}/${VOLUME_NAME}/.background/"

# Create Applications shortcut
ln -s /Applications "${OUTPUT_DIR}/${VOLUME_NAME}/Applications"

# Calculate size (add 25% buffer for metadata)
SIZE=$(du -sm "${OUTPUT_DIR}/${VOLUME_NAME}" | cut -f1)
SIZE=$((SIZE + SIZE/4))

# Create temporary disk image
hdiutil create -srcfolder "${OUTPUT_DIR}/${VOLUME_NAME}" \
               -volname "${VOLUME_NAME}" \
               -fs HFS+ \
               -fsargs "-c c=64,a=16,e=16" \
               -format UDRW \
               -size ${SIZE}m \
               "${OUTPUT_DIR}/temp.dmg"

# Mount the image
DEVICE=$(hdiutil attach -readwrite -noverify -noautoopen "${OUTPUT_DIR}/temp.dmg" | 
         awk 'NR==1{print$1}' | sed 's/[[:space:]]*$//')

# Wait for volume to mount
sleep 5

# Set visual properties (FIXED)
echo '
tell application "Finder"
    tell disk "'${VOLUME_NAME}'"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set bounds of container window to {400, 100, 1000, 500}
        set viewOptions to the icon view options of container window
        set arrangement of viewOptions to not arranged
        set icon size of viewOptions to 96
        
        -- Set background (CRITICAL FIX)
        set backgroundFile to file ".background:'${BACKGROUND_IMAGE}'"
        set background picture of viewOptions to backgroundFile
        
        -- Set icon positions (only App and Applications)
        set position of item "'${APP_BUNDLE}'" of container window to {150, 250}
        set position of item "Applications" of container window to {450, 250}
        
        close
        open
        update without registering applications
        delay 2  -- Critical pause for changes to apply
    end tell
end tell
' | osascript

# Set permissions
chmod -Rf go-w "/Volumes/${VOLUME_NAME}"

# Unmount
hdiutil detach "$DEVICE"

# Create final compressed DMG
hdiutil convert "${OUTPUT_DIR}/temp.dmg" \
                -format UDZO \
                -imagekey zlib-level=9 \
                -o "${OUTPUT_DIR}/${DMG_NAME}.dmg"

# Clean up
rm -f "${OUTPUT_DIR}/temp.dmg"
rm -rf "${OUTPUT_DIR}/${VOLUME_NAME}"

echo "✅ DMG created: ${OUTPUT_DIR}/${DMG_NAME}.dmg"