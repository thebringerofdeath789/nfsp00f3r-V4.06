# NFCClone V4.05 - Windows 10 ACR122 Deployment Guide

## 🖥️ **Windows 10 Hardware Deployment Setup**

### **Target Configuration:**
- **OS**: Windows 10 64-bit
- **Python**: 3.9
- **Reader**: ACR122U USB NFC Reader
- **Deployment**: Desktop development/testing environment

---

## 🚀 **Phase 1: Windows Environment Setup**

### **1. Verify Python Installation**
```powershell
# Check Python version
python --version  # Should show Python 3.9.x

# Check pip
pip --version
```

### **2. Install Windows-Specific Dependencies**
```powershell
# Core Python packages (Windows-compatible versions)
pip install pyscard==2.0.7
pip install pyserial==3.5
pip install cryptography==41.0.4
pip install PyQt5==5.15.10  # For GUI components

# Optional: For enhanced Windows PCSC support
pip install pycryptodome==3.18.0
```

### **3. ACR122U Driver Setup**
```powershell
# Windows 10 should auto-detect ACR122U
# If needed, download drivers from ACS website
# Verify installation with Device Manager
```

---

## 🔧 **Phase 2: ACR122 Validation**

### **Hardware Detection Test**
```powershell
# Test PCSC service
# Should be running by default on Windows 10
sc query "SCardSvr"

# Test reader detection
python -c "
from smartcard.System import readers
r = readers()
print(f'Available Readers: {r}')
print('✅ ACR122 detected' if 'ACR122' in str(r) else '❌ ACR122 not found')
"
```

### **Create Windows-Optimized Test Script**
