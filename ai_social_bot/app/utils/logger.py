import logging
import logging.handlers
from pathlib import Path

LOG_FILE = Path('ai_social_bot/logs/app.log')
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    fh = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=10_000_00, backupCount=5)
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    fh.setFormatter(fmt)
    logger.addHandler(fh)
