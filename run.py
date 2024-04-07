# run.py
from app.main import app
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.info('Logger initialized.')

if __name__ == "__main__":
    app.run(debug=True)

