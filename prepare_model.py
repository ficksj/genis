import shutil
import os
from app.paths import ensure_model, model_path
os.makedirs('assets', exist_ok=True)
shutil.copy(model_path(), os.path.join('assets','hand_landmarker.task'))