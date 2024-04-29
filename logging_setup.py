import logging
from pathlib import Path
import json
import os

def setup_logging(config_path: str = 'logging_config.json', log_path: Path = Path('log')):
    config_file = Path(config_path)
    with open(config_file) as f_in:
        config = json.load(f_in)

    if not os.path.exists(log_path):
        os.mkdir(log_path)

    config['handlers']['error_file_handler']['filename'] = Path(log_path, 'errors.log')
    config['handlers']['info_file_handler']['filename'] = Path(log_path, 'info.log')
    config['handlers']['payment_file_handler']['filename'] = Path(log_path, 'payments.log')

    logging.addLevelName(15, "PAYMENT")
    logging.config.dictConfig(config)
