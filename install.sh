#!/bin/bash
# Straddle Unified Installer
echo "Installing Straddle Infrastructure..."

# 1. Setup Venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Patch Hermes (Injection)
echo "Injecting Maintenance Panel into Hermes WebUI..."
# Simple injection: append the panel import and usage to App.tsx
sed -i '/import { SidebarStatusStrip }/a import { MaintenancePanel } from "./components/MaintenancePanel";' ~/.hermes/hermes-agent/web/src/App.tsx
# Injects the component before the closing layout tag (simplified for this automation)
sed -i '/<\/div>/i <MaintenancePanel />' ~/.hermes/hermes-agent/web/src/App.tsx

# 3. Rebuild Hermes WebUI
echo "Rebuilding Hermes WebUI (ETA: 3-5m)..."
cd ~/.hermes/hermes-agent/web/ && npm install && npm run build

# 4. Finalize
echo "Installation Complete. Restarting services..."
systemctl --user restart hermes-webui.service
