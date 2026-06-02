# logger_setup.py
import logging


def get_logger():
    """
    Description:
    Returns the shared EnvironmentExporter logger.
    Input:
    None
    Output:
    logger(obj) It stores the methor getLogger named Enviroment Exporter into a var.
    """
    # Grabs the python logger "EnviromentExporter."
    logger = logging.getLogger("EnvironmentExporter")
    if not logger.handlers:
        # It assings handler to mayas script editor system.
        handler = logging.StreamHandler()
        # It formats the messages.
        formatter = logging.Formatter("%(levelname)s: %(message)s")
        # Sets the formatter adn handler into the logger.
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        # It tells the logger what kind of messages to send.
        logger.setLevel(logging.INFO)
    return logger
