import logging
from pathlib import Path
import json
import os
from datetime import datetime as datetime

def setup_logging(config_path: str = 'logging_config.json', log_path: Path = Path('log')):
    config_file = Path(config_path)
    with open(config_file) as f_in:
        config = json.load(f_in)

    if not os.path.exists(log_path):
        os.mkdir(log_path)

    config['handlers']['error_file_handler']['filename'] = Path(log_path, f'{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_errors.log')
    config['handlers']['info_file_handler']['filename'] = Path(log_path, f'{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_info.log')
    config['handlers']['payment_file_handler']['filename'] = Path(log_path, f'{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_payments.json')

    logging.addLevelName(15, "PAYMENT")
    logging.config.dictConfig(config)
