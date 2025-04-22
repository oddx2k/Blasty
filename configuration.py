import os
from configparser import ConfigParser


class Config:
    def __init__(self):
        pass

    def read_config(self, file):
        if os.path.exists(file):
            config = ConfigParser(comment_prefixes='/', allow_no_value=True, interpolation=None)
            config.optionxform = str
            config.read(file)
            return config

        return None


class AppConfig(Config):
    def __init__(self):
        super().__init__()
        self.name = 'blasty'
        self.file_name = self.name + '.ini'
        self.config = self.read_config(self.file_name) or self.default_config()

    def default_config(self):
        defaults = ConfigParser(comment_prefixes='/', allow_no_value=True)
        defaults.optionxform = str
        for player in range(1, 5):
            defaults['Lightgun' + str(player)] = {
                'ID': '',
                'PROFILE': '',
                'MONITOR': 0,
                'PORT': '',
                'BAUDRATE': 9600,
                'BYTESIZE': 8,
                'PARITY': 'N',
                'STOPBITS': 1,
                'TIMEOUT': .1,
                'RTSCTS': True,
                'DSRDTR': True,
            }
        return defaults

    def update_config(self):
        config_base = self.default_config()

        updated = False
        for section in config_base:
            if section not in self.config:
                self.config[section] = config_base[section]
                updated = True
                continue
            for key in config_base[section]:
                if key not in self.config[section]:
                    self.config[section][key] = config_base[section][key]
                    updated = True

        if updated or not os.path.exists(self.file_name):
            if not os.path.exists(os.path.split(os.path.abspath(self.file_name))[0]):
                os.makedirs(os.path.split(os.path.abspath(self.file_name))[0], exist_ok=True)
            with open(self.file_name, 'w') as f:
                self.config.write(f, space_around_delimiters=False)

    def get_config(self):
        # config = self.read_config('blasty.ini') or self.default_config()
        return {section: {key: self.config[section][key] for key in self.config[section]} for section in self.config if
                self.config[section]}


class GameConfig(Config):
    def __init__(self, name='default', profile=None):
        super().__init__()
        self.name = name
        self.profile = profile or ""
        self.file_name = os.path.join('config', self.profile, self.name + '.ini')
        self.default_file_name = os.path.join('config', self.profile, 'default' + '.ini')
        self.config = self.read_config(self.file_name) or self.read_config(self.default_file_name) or self.default_config()

    def default_config(self):
        defaults = ConfigParser(comment_prefixes='/', allow_no_value=True)
        defaults.optionxform = str
        defaults['General'] = {
            'MameStart': '',
            'MameStop': '',
            # 'StateChange': '',
            # 'OnRotate': '',
            'OnPause': '',
            'MaxRate': '',
            'Monitor': 0,
        }
        # defaults['KeyStates'] = {
        #     'RefreshTime': '',
        # }
        defaults['Output'] = {}
        return defaults

    def update_config(self, outputs=None):
        config_base = self.default_config()

        updated = False
        for section in config_base:
            if section not in self.config:
                self.config[section] = config_base[section]
                updated = True
                continue
            for key in config_base[section]:
                if key not in self.config[section]:
                    self.config[section][key] = config_base[section][key]
                    updated = True

        if outputs is not None:
            for output in outputs:
                if all(x.lower() not in output.lower() for x in ["mame_start", "mame_stop", "pause", "Orientation"]):
                    # if output not in self.config['Output'] and "; " + output not in self.config['Output']:
                    self.config['Output']['; ' + output] = '|'.join([x for x in outputs[output]])
                    updated = True

        if updated or not os.path.exists(self.file_name):
            if not os.path.exists(os.path.split(os.path.abspath(self.file_name))[0]):
                os.makedirs(os.path.split(os.path.abspath(self.file_name))[0], exist_ok=True)
            with open(self.file_name, 'w') as f:
                self.config.write(f, space_around_delimiters=False)

    def get_config(self):
        return (self.read_config(self.file_name) or
                self.read_config(self.default_file_name) or
                self.default_config())
