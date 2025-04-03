import os
from configparser import ConfigParser


def read_config(file):
    if os.path.exists(file):
        config = ConfigParser(comment_prefixes='/', allow_no_value=True, interpolation=None)
        config.optionxform = str
        config.read(file)
        return config

    return None


def default_config():
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
            'TIMEOUT': .01,
            'RTSCTS': True,
            'DSRDTR': True,
        }
    return defaults


def default_game_config():
    defaults = ConfigParser(comment_prefixes='/', allow_no_value=True)
    defaults.optionxform = str
    defaults['General'] = {
        'MameStart': '',
        'MameStop': '',
        'StateChange': '',
        'OnRotate': '',
        'OnPause': '',
        'MaxRate': '',
        'Monitor': 0,
    }
    defaults['KeyStates'] = {
        'RefreshTime': '',
    }
    defaults['Output'] = {}
    return defaults


def update_config():
    config_base = default_config()
    config = read_config('blasty.ini') or default_config()
    config_file = 'blasty.ini'

    updated = False
    for section in config_base:
        if section not in config:
            config[section] = config_base[section]
            updated = True
            continue
        for key in config_base[section]:
            if key not in config[section]:
                config[section][key] = config_base[section][key]
                updated = True

    if updated or not os.path.exists(config_file):
        if not os.path.exists(os.path.split(os.path.abspath(config_file))[0]):
            os.makedirs(os.path.split(os.path.abspath(config_file))[0], exist_ok=True)
        with open(config_file, 'w') as f:
            config.write(f, space_around_delimiters=False)


def update_game_config(config, name, profile="", outputs=None, default=False):
    if default:
        config_base = default_game_config()
    else:
        config_base = read_config(os.path.join('config', profile, 'default' + '.ini')) or default_game_config()

    config_file = os.path.join('config', profile, name + '.ini')
    updated = False
    for section in config_base:
        if section not in config:
            config[section] = config_base[section]
            updated = True
            continue
        for key in config_base[section]:
            if key not in config[section]:
                config[section][key] = config_base[section][key]
                updated = True

    if outputs is not None:
        for output in outputs:
            if all(x.lower() not in output.lower() for x in ["mame_start", "mame_stop", "pause", "Orientation"]):
                if output not in config['Output'] and "; " + output not in config['Output']:
                    config['Output']['; ' + output] = '|'.join([x for x in outputs[output]])
                    updated = True

    if updated or not os.path.exists(config_file):
        if not os.path.exists(os.path.split(os.path.abspath(config_file))[0]):
            os.makedirs(os.path.split(os.path.abspath(config_file))[0], exist_ok=True)
        with open(config_file, 'w') as f:
            config.write(f, space_around_delimiters=False)


def get_config():
    # return read_config('blasty.ini') or default_config()
    config = read_config('blasty.ini') or default_config()
    return {section: {key: config[section][key] for key in config[section]} for section in config if config[section]}


def get_game_config(name, profile=""):
    return (read_config(os.path.join('config', profile, name + '.ini')) or
            read_config(os.path.join('config', profile, 'default' + '.ini')) or
            default_game_config())
