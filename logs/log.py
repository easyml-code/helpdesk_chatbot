import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_PATH = os.path.join(LOG_DIR, "app.log")

formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(name)s %(module)s:%(lineno)d - %(message)s"
)

handler = RotatingFileHandler(
    LOG_PATH, 
    maxBytes=1 * 1024 * 1024,
    backupCount=5
)
handler.setFormatter(formatter)

logger = logging.getLogger("app_logger")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Optional: also print logs to console in development
console = logging.StreamHandler()
console.setFormatter(formatter)
logger.addHandler(console)
