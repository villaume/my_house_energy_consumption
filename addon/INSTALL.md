# Home Assistant Add-on Installation Guide

## Step-by-Step Installation

### Step 1: Copy Files to Home Assistant

You need to copy the add-on files to your Home Assistant's add-ons directory.

**Find your HA username first:**
```bash
# Try to SSH and see what works
ssh root@homeassistant.local
# or
ssh hassio@homeassistant.local
# or
ssh your-username@your-ha-ip
```

**Copy the add-on directory:**
```bash
# From your project directory
scp -r addon username@homeassistant.local:/addons/tibber_energy_api/
```

**Common paths depending on your setup:**
- Home Assistant OS: `/addons/`
- Supervised: `/usr/share/hassio/addons/local/`

### Step 2: Copy Database File

```bash
# Copy your existing database
scp tibber_data.duckdb username@homeassistant.local:/usr/share/hassio/share/

# Verify it's there
ssh username@homeassistant.local
ls -lh /usr/share/hassio/share/tibber_data.duckdb
```

### Step 3: Install the Add-on

1. Open Home Assistant web interface
2. Go to **Settings** → **Add-ons**
3. Click **Add-on Store** (bottom right)
4. Click **⋮** (three dots, top right)
5. Click **Repositories**
6. Click **Check for updates**
7. Go back to Add-on Store
8. Scroll down to **Local add-ons** section
9. You should see **Tibber Energy API**
10. Click on it
11. Click **Install** (this may take 5-10 minutes)

### Step 4: Configure the Add-on

1. After installation, go to the **Configuration** tab
2. Add your API key (optional):
   ```yaml
   api_key: "generate-with-openssl-rand-hex-32"
   log_level: info
   ```
3. Click **Save**

### Step 5: Start the Add-on

1. Go to the **Info** tab
2. Click **Start**
3. Wait for it to start (watch the logs)
4. Enable **Start on boot**
5. Enable **Watchdog** (auto-restart on crash)

### Step 6: Verify It's Working

1. Click on the **Log** tab
2. You should see:
   ```
   [INFO] Starting Tibber Energy API...
   [INFO] Database path: /share/tibber_data.duckdb
   ```

3. Test the API:
   ```bash
   # From your computer
   curl http://your-ha-ip:8000/health

   # Should return: {"status":"healthy"}
   ```

4. Test an API endpoint:
   ```bash
   curl -H "X-API-Key: your-key" http://your-ha-ip:8000/api/stats
   ```

### Step 7: Add to Home Assistant

Edit `configuration.yaml`:

```yaml
sensor:
  - platform: rest
    resource: http://localhost:8000/api/latest
    headers:
      X-API-Key: your-secret-key
    name: "Tibber Latest Consumption"
    value_template: "{{ value_json.consumption }}"
    unit_of_measurement: "kWh"
    device_class: energy
    scan_interval: 3600
```

Restart Home Assistant and check if the sensor appears.

## Troubleshooting

### "Add-on not found in store"

The add-on directory might not be in the right place. Try:

```bash
# SSH to Home Assistant
ssh root@homeassistant.local

# Check where add-ons should go
ls -la /addons/
ls -la /usr/share/hassio/addons/local/

# Move to correct location if needed
mv /addons/tibber_energy_api /usr/share/hassio/addons/local/
```

Then refresh the add-on store.

### "No module named uvicorn"

The Dockerfile needs to install dependencies. Make sure you're using the updated Dockerfile I provided.

### "Database not found"

```bash
# Check database location
ssh root@homeassistant.local
ls -la /usr/share/hassio/share/

# Copy if missing
# From your computer:
scp tibber_data.duckdb root@homeassistant.local:/usr/share/hassio/share/
```

### "Cannot connect to API"

1. Check add-on is running: Settings → Add-ons → Tibber Energy API
2. Check logs for errors
3. Verify port 8000 is exposed: should show in add-on info
4. Try from HA itself: `http://localhost:8000/health`

### Build Fails

If the add-on build fails:

1. Check the logs during installation
2. Common issues:
   - Missing dependencies in Dockerfile
   - Wrong base image
   - Network issues downloading packages

Solution: Update Dockerfile with all dependencies as shown.

## Alternative: Quick Test Without Add-on

If you just want to test the API quickly:

```bash
# SSH to Home Assistant
ssh root@homeassistant.local

# Install Python (if not available)
apk add python3 py3-pip

# Install dependencies
pip3 install httpx polars duckdb fastapi uvicorn pyarrow pytz

# Copy API files (from another terminal)
scp -r api root@homeassistant.local:/tmp/

# Run API manually
cd /tmp/api
DATABASE_PATH=/share/tibber_data.duckdb python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

This is temporary (won't survive reboot) but good for testing.

## Need Help?

If you get stuck, share:
1. The exact error message from the logs
2. Your Home Assistant version (Settings → System → About)
3. The output of: `ls -la /addons/` or `ls -la /usr/share/hassio/addons/local/`

And I can help debug! 🔧
