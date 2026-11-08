"""Generate assets/i-arrange.ico from the in-app logo."""
import os
from PySide6.QtGui import QGuiApplication
from culler import icons

os.makedirs("assets", exist_ok=True)
app = QGuiApplication([])
pm = icons.logo(256)
pm.setDevicePixelRatio(1)
print("saved:", pm.scaled(256, 256).save("assets/i-arrange.ico", "ICO"))
