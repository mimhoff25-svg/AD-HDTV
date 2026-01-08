# 🔧 GDbus Error Fix & Display Server Troubleshooting

## Problem: GDbus Error When Running WebGridPlayer

When you try to run WebGridPlayer, you may see errors like:
```
GDbus error: org.freedesktop.DBus.Error.ServiceUnknown
```

## Root Cause

The `DISPLAY` environment variable is not set, so the application cannot connect to the X server.

---

## Solution 1: Auto-Detect (Recommended) ✅

The launch script now automatically detects Chrome Remote Desktop:

```bash
cd /home/mike/projects/webgridplayer
bash scripts/run_webgridplayer.sh
```

**What it does:**
- Detects Chrome Remote Desktop X server (`:20` or similar)
- Sets `DISPLAY` variable automatically
- Sets `XAUTHORITY` to prevent permission errors
- Configures DBus for headless environments

---

## Solution 2: Manual Display Configuration

If auto-detect doesn't work, manually set the DISPLAY:

### Step 1: Find your X server display
```bash
ps aux | grep Xorg | grep -v grep
```

Look for output like:
```
mike  12345  0.0  1.6 1813696 269980 ?  Sl  Jan05  447:13 /usr/lib/xorg/Xorg :20 -auth ...
                                                              ↑
                                                        Display number
```

### Step 2: Set DISPLAY and run
```bash
export DISPLAY=:20
export XAUTHORITY=$HOME/.Xauthority
bash scripts/run_webgridplayer.sh
```

Or in one line:
```bash
DISPLAY=:20 XAUTHORITY=$HOME/.Xauthority bash scripts/run_webgridplayer.sh
```

---

## Solution 3: Virtual Display (Headless Systems)

If you don't have an X server, use the virtual display:

```bash
cd /home/mike/projects/webgridplayer
bash scripts/run_with_xvfb.sh
```

This creates a virtual framebuffer display for headless systems.

---

## Solution 4: Suppress DBus Warnings

If you still see DBus warnings but the app runs, add:

```bash
export DBUS_SYSTEM_BUS_ADDRESS="unix:path=/var/run/dbus/system_bus_socket"
bash scripts/run_webgridplayer.sh
```

---

## Diagnostic Commands

### Check current display status
```bash
echo "DISPLAY=$DISPLAY"
echo "XAUTHORITY=$XAUTHORITY"
ps aux | grep Xorg | grep -v grep
```

### Check DBus status
```bash
echo $DBUS_SESSION_BUS_ADDRESS
ps aux | grep dbus-daemon | grep -v grep
```

### Verify X11 connection
```bash
xset q
```

If this works, your display is configured correctly.

---

## Full Working Command

For Chrome Remote Desktop (most common case):

```bash
cd /home/mike/projects/webgridplayer && \
export DISPLAY=:20 && \
export XAUTHORITY=$HOME/.Xauthority && \
export DBUS_SYSTEM_BUS_ADDRESS="unix:path=/var/run/dbus/system_bus_socket" && \
/home/mike/projects/.venv/bin/python src/webgridplayer.py
```

---

## Environment Variables Explained

| Variable | Purpose | Example |
|----------|---------|---------|
| `DISPLAY` | X server display number | `:20` or `:0` |
| `XAUTHORITY` | X authentication file location | `$HOME/.Xauthority` |
| `DBUS_SYSTEM_BUS_ADDRESS` | D-Bus system bus address | `unix:path=/var/run/dbus/system_bus_socket` |

---

## Quick Test

Run this to test if display is configured correctly:

```bash
bash << 'EOF'
if [ -z "$DISPLAY" ]; then
    echo "❌ DISPLAY not set - using auto-detect..."
    DISPLAY=$(ps aux | grep "Xorg :" | grep -v grep | sed -n 's/.*Xorg \(:[0-9]*\).*/\1/p' | head -1)
    if [ -n "$DISPLAY" ]; then
        echo "✅ Found display: $DISPLAY"
        export DISPLAY
        export XAUTHORITY=$HOME/.Xauthority
    else
        echo "❌ No X server found!"
        exit 1
    fi
else
    echo "✅ DISPLAY already set: $DISPLAY"
fi

xset q 2>/dev/null && echo "✅ X server connection OK" || echo "❌ X server connection failed"
EOF
```

---

## If All Else Fails

Run with verbose output to see exactly what's happening:

```bash
export QT_DEBUG_PLUGINS=1
bash scripts/run_webgridplayer.sh 2>&1 | head -100
```

This will show detailed information about what the application is trying to access.

---

## Scripts Updated

Both launch scripts have been updated with:
- ✅ Automatic DISPLAY detection
- ✅ XAUTHORITY configuration
- ✅ DBus setup for headless environments

Just use:
```bash
bash scripts/run_webgridplayer.sh
```

It should now work without manual configuration! 🚀
