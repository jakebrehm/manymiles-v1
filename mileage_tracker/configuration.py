import configparser
import os
import pathlib


class Configuration:

    def __init__(self, config=None):
        self.config = configparser.ConfigParser()

        if not config:
            project = pathlib.Path(__file__).resolve().parent.parent
            config = os.path.join(project, 'data', 'config.ini')

        self.config.read(config)

    def get(self, environment_name, config_section, config_name):
        try:
            return os.environ[environment_name]
        except KeyError:
            return self.config.get(config_section, config_name)