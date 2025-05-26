import types
import re
import struct

hid_cache = {}

hid_rules = {
    # report[0] = REPORT_ID
    # # Enable all update flags
    # report[1] = 0  # EnableRumbleUpdate
    # report[2] = 0  # EnableRumbleFFBControl
    # report[3] = 0  # EnableLedUpdate
    # report[4] = 0  # EnableLedFFBControl
    # report[5] = 0  # EnableRecoilUpdate
    # report[6] = 0  # EnableRecoilFFBControl
    # # Rumble settings
    # report[15] = 0  # Rumble pulses
    # report[16] = 0  # RumbleOnPeriod
    # report[18] = 0  # RumbleOffPeriod
    # # LED settings (RGB)
    # report[20] = 0  # Red
    # report[21] = 0  # Green
    # report[22] = 0  # Blue
    # # Flash settings
    # report[23] = 0  # ledIndex
    # report[24] = 0  # Flashes
    # report[25] = 0  # LedFlashOffPeriod
    # report[27] = 0  # LedFlashOnPeriod
    # # Recoil settings
    # report[29] = 0  # Recoil pulses
    # report[30] = 0  # RecoilOnPeriod
    # report[31] = 0  # RecoilOffPeriod
    'BLAMCON':
        {
            'regex': re.compile(r'((?:CM|FB|SM)[.]\d+)(?:[.](\d+))?(?:[.](\d+))?(?:[.](\d+))?'),
            #  Init
            'SM.6':
                {
                    '0': {
                        'report': 0x10,
                        'report_size': 40,
                        'rules': [(1, ">B", 0),
                                  (2, ">B", 0),
                                  (3, ">B", 0),
                                  (4, ">B", 0),
                                  (5, ">B", 0),
                                  (6, ">B", 0)]
                    },
                    '_': {
                        'report': 0x10,
                        'report_size': 40,
                        'rules': [(1, ">B", 1),
                                  (2, ">B", 1),
                                  (3, ">B", 1),
                                  (4, ">B", 1),
                                  (5, ">B", 1),
                                  (6, ">B", 1)]
                    },
                },
            #  Recoil
            'FB.0':
                {
                    '0': {
                        'report': 0x20,
                        'report_size': 40,
                        'rules': [(1, ">B", 1),
                                  (2, ">B", 0)]
                    },
                    '_': {
                        'report': 0x20,
                        'report_size': 40,
                        'rules': [(1, ">B", 1),
                                  (2, ">B", lambda a: int(a[1]) if a[1] != '' else 0)]
                    },
                },
            #  Rumble
            'FB.1':
                {
                    '0': {
                        'report': 0x21,
                        'report_size': 40,
                        'rules': [(1, ">B", 1),
                                  (2, ">B", 0)]
                    },
                    '_': {
                        'report': 0x21,
                        'report_size': 40,
                        'rules': [(1, ">B", 1),
                                  (2, ">B", lambda a: int(a[1]) if a[1] != '' else 0)]
                    },
                },
            #  LED
            'FB.2':
                {
                    '0': {
                        'report': 0x22,
                        'report_size': 40,
                        'rules': [(1, ">B", 1),
                                  (2, ">B", 0),
                                  (3, ">B", 0),
                                  (4, ">B", 0),
                                  (5, ">B", 0),
                                  (6, ">B", 0)]
                    },
                    '1': {
                        'report': 0x22,
                        'report_size': 40,
                        'rules': [(1, ">B", 1),
                                  (2, ">B", 255),
                                  (5, ">B", 0)],
                        '_': {
                                'report': 0x22,
                                'report_size': 40,
                                'rules': [(1, ">B", 1),
                                          (2, ">B", lambda a: (int(a[2]) >> 16) & 255 if a[2] != '' else 0),
                                          (3, ">B", lambda a: (int(a[2]) >> 8) & 255 if a[2] != '' else 0),
                                          (4, ">B", lambda a: int(a[2]) & 255 if a[2] != '' else 0),
                                          (5, ">B", 0),
                                          (6, ">B", lambda a: int(a[3]) if a[3] != '' else 0)]
                            },
                    },
                },
        }
}


def get_settings(data, *args):
    # print(args, data)
    if args and data:
        if args[0]:
            value = data.get(args[0])
            if value is None:
                value = data.get('_')
            return data if value is None else value if len(args) == 1 else get_settings(value, *args[1:])
    return data


def get_hid(command, profile):
    # print(command)
    if command is None:
        return

    if profile in hid_cache and command in hid_cache[profile]:
        # print('returning cached')
        return hid_cache[profile][command]

    regex = None
    if profile in hid_rules and 'regex' in hid_rules[profile]:
        regex = hid_rules[profile]['regex']

    if regex is None:
        return

    matches = regex.findall(command)
    reports = []
    for match in matches:
        if match:
            # print(match)
            settings = get_settings(hid_rules, profile, *match)
            if settings.keys() >= {'report_size', 'report', 'rules'}:
                report = bytearray(settings['report_size'])
                report[0] = settings['report']
                for o, t, v in settings['rules']:
                    struct.pack_into(t, report, o, v(match) if type(v) is types.LambdaType else v)
                reports.append(report)

    # print('caching')
    if profile not in hid_cache:
        hid_cache[profile] = {}
    hid_cache[profile][command] = reports

    return reports if len(reports) > 0 else None
