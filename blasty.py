import socket
import serial

import regex_patterns
import time
import sys
import psutil
import signal
from configuration import AppConfig, GameConfig
from devices import Device
from serial.tools import list_ports
import hid

HOST = "127.0.0.1"
PORT = 8000


def signal_handler(sig, frame):
    if sig or frame:
        pass
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def get_pid(pid, output_providers):
    if pid is None:
        for proc in psutil.process_iter():
            if any(x in proc.name().lower() for x in output_providers):
                return proc.pid
    else:
        for proc in psutil.process_iter():
            if pid == proc.pid:
                return proc.pid
    return None


def main():
    AppConfig().update_config()
    GameConfig().update_config()

    pid = None
    DEVICES = []
    while True:
        pid = get_pid(pid, ["mame", "demulshooter"])
        if pid is None:
            time.sleep(2)
            continue

        try:
            for device in DEVICES:
                if device.comm is not None:
                    device.comm.close()
        except Exception as e:
            print(getattr(e, 'message', repr(e)))

        conf = AppConfig().get_config()
        DEVICES = [device for device in
                   [Device(conf[device]['ID'] or 0,
                           conf[device]['PROFILE'],
                           {
                               'port': conf[device]['PORT'] or "",
                               'baudrate': conf[device]['BAUDRATE'] or 9600,
                               'bytesize': conf[device]['BYTESIZE'] or serial.EIGHTBITS,
                               'parity': conf[device]['PARITY'] or serial.PARITY_NONE,
                               'stopbits': conf[device]['STOPBITS'] or serial.STOPBITS_ONE,
                               'timeout': conf[device]['TIMEOUT'] or 0.1,
                               'rtscts': conf[device]['RTSCTS'] or False,
                               'dsrdtr': conf[device]['DSRDTR'] or False,
                           },
                           [port.vid for port in list_ports.comports() if conf[device]['PORT'] == port.device][-1],
                           [port.pid for port in list_ports.comports() if conf[device]['PORT'] == port.device][-1],
                           ([device_dict['path'] for port in list_ports.comports() if port.device == conf[device]['PORT'] for device_dict in hid.enumerate() if device_dict['vendor_id'] == port.vid and device_dict['product_id'] == port.pid and device_dict['usage'] == 5] + [None])[0],
                           conf[device]['MONITOR'] or 'False',
                           ) for device in conf
                    if conf[device]['PORT'] and conf[device]['PROFILE'] and
                    conf[device]['PORT'] in [port.device for port in list_ports.comports()]]
                   if device.comm is not None or device.hid_path is not None]

        for device in DEVICES:
            GameConfig(profile=device.profile).update_config()

        game = None

        with (socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s):
            try:
                s.connect((HOST, PORT))
            except ConnectionRefusedError:
                continue
            while True:
                try:
                    data = s.recv(1024).decode()
                    if not data:
                        break
                except OSError:
                    break

                data_time = time.perf_counter_ns()

                for output in data.split('\r'):
                    if "=" not in output:
                        continue
                    out, val = (regex_patterns.output_split.split(output.rstrip()) + [None])[:2]
                    match out:
                        case 'mame_start' if '___empty' not in val:
                            game = {'name': val, 'known_outputs': {}}
                            for device in DEVICES:
                                device.load_config(game['name'])
                                device.start()
                        case 'mame_start':
                            pass
                        case 'mame_stop' if val == '1':
                            if game:
                                for device in DEVICES:
                                    device.stop()
                                GameConfig(game['name']).update_config(outputs=game['known_outputs'])
                        case 'mame_stop':
                            pass
                        case 'pause':
                            if game:
                                for device in DEVICES:
                                    device.pause(val)
                        case _:
                            for device in DEVICES:
                                device.add_to_output_queue(out, val, data_time)

                    if game:
                        if out not in game['known_outputs']:
                            game['known_outputs'][out] = [val]
                        else:
                            if val not in game['known_outputs'][out]:
                                game['known_outputs'][out].append(val)


if __name__ == "__main__":
    main()
