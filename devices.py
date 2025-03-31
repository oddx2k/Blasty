import concurrent.futures
import queue
import time
import serial
import regex_patterns
from serial.tools import list_ports
from configuration import get_game_config
from command import Command


class Device:
    def __init__(self, player, port, profile, init):
        self.player = player
        self.port = port
        self.profile = profile
        self.init = init
        self.comm = self.open_com()
        self.full_config = {}
        self.general_config = {}
        self.key_states_config = {}
        self.output_config = {}
        self.load_config('default')
        self.max_rate = 1 / (float(self.general_config['MaxRate']) or 10)
        self.output_queue = queue.Queue()
        self.send_queue = queue.Queue()
        self.block = []

        self.enabled = True
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self.t1 = self.pool.submit(self.process_output_queue)
        self.t2 = self.pool.submit(self.process_send_queue)
        self.filter = ['lwp', 'lws', 'lwc', 'lwr', 'lwk', 'iws', 'iwc', 'iwr', 'iwk', 'mls', 'mlc', 'mlr', 'mlk', 'lhs',
                       'lhc', 'lhr', 'lhk', 'uls', 'uli', 'ulf', 'uld', 'ulc', 'ulp', 'ulk', 'ghd', 'kbd', 'spk', 'ply',
                       'pya', 'dsp', 'dss', 'dff', 'ffa', 'xip', 'xia', 'wii', 'lpt', 'lpe', 'cmo', 'cmc', 'css', 'csl',
                       'cmr', 'cmw', 'lds', 'sds', 'sdf', 'sbf', 'ibf', 'bmo', 'cpy', 'kll', 'log', 'nll', 'wat', 'rfs',
                       'lop', 'lfs', 'kls', 'lwa', 'cmd', 'cdw', 'qut', 'ref', '']

    def compute(self, exp):
        match = regex_patterns.hex_dec.search(exp)
        while match is not None:
            exp = regex_patterns.hex_dec.sub(str(int(match.group(1), 16)), exp, 1)
            match = regex_patterns.hex_dec.search(exp)
        exp = regex_patterns.mod.sub(r'%', exp)
        exp = regex_patterns.eval_filter.sub('', exp)
        return int(eval(exp))

    def sub_tokens(self, output, value):
        out = self.get_output(self.output_config, output, value)
        out = regex_patterns.value_token.sub(value, out)
        match = regex_patterns.token.search(out)
        while match is not None:
            match match.group(0):
                case _ if match.group(1)[:4] == 'EVAL':
                    v = self.compute(match.group(1)[4:])
                    new = self.get_output(self.full_config, output, v)
                    if 'EVAL' not in new:
                        out = regex_patterns.token.sub(new, out, 1)
                    else:
                        out = regex_patterns.token.sub(self.get_output(self.full_config, output, 0), out, 1)
                case _ if match.group(1)[:5] == 'REVAL':
                    v = self.compute(match.group(1)[5:])
                    out = regex_patterns.token.sub(str(v), out, 1)
                case _ if regex_patterns.cleanup.search(match.group(0)):
                    out = regex_patterns.cleanup.sub(r',(\1),', out)
                case _:
                    out = regex_patterns.token.sub(self.get_output(self.full_config, match.group(1), value), out, 1)
            out = regex_patterns.value_token.sub(value, out)
            match = regex_patterns.token.search(out)
        out = regex_patterns.extra_comma.sub(r',', out)
        return out

    def get_output(self, config, output, value):
        if len(config[output].split('|')) > int(value):
            return config[output].split('|')[int(value)]
        return config[output].split('|')[-1]

    def get_window_time(self):
        return time.perf_counter_ns() + (self.max_rate * 1000000000 / 2)

    def process_output_queue(self):
        try:
            wait_queue = {}
            while True:
                window_time = self.get_window_time()
                if wait_queue or not self.output_queue.empty():
                    window_queue = queue.Queue()
                    ready_queue = queue.Queue()
                    block_list = []

                    if wait_queue:
                        for c in list(wait_queue):
                            if time.perf_counter_ns() > int(c):
                                ready_queue.put(c)

                    while not self.output_queue.empty():
                        window_queue.put(self.output_queue.get())

                    while not ready_queue.empty() or not window_queue.empty():
                        out = None
                        output = None
                        data_time = None

                        if not ready_queue.empty():
                            data_time = time.perf_counter_ns()
                            out = wait_queue.pop(ready_queue.get())

                        elif not window_queue.empty():
                            output, value, data_time = window_queue.get()
                            # print(output, value)

                            if output not in self.output_config:
                                # print(output, value)
                                continue

                            out = self.sub_tokens(output, value)

                        if not out:
                            continue

                        if out in block_list:
                            # print(out, 'already in queue to send')
                            continue

                        block_list.append(out)

                        for i, o in enumerate(out.split(',')):
                            if o[:3] not in self.filter:
                                match = regex_patterns.reval.search(o)
                                if match is not None:
                                    match match.group(1):
                                        case _ if match.group(1)[:4] == 'WAIT':
                                            self.block.append(output)
                                            time.sleep(int(match.group(1)[4:]) / 1000)
                                            self.block.remove(output)
                                        case _ if match.group(1)[:4] == 'TIME':
                                            wait_queue[time.perf_counter_ns() + int(match.group(1)[4:]) * 1000000] = ",".join(out.split(',')[i + 1:])
                                        case _:
                                            pass
                                    continue

                                if self.enabled:
                                    self.add_to_send_queue(Command(self.comm, o, window_time, data_time))

                time.sleep(self.max_rate)
        except Exception as e:
            print(getattr(e, 'message', repr(e)))

    def add_to_output_queue(self, out, val, data_time):
        if self.block and out in self.block:
            return
        self.output_queue.put((out, val, data_time))
        if not self.t1.running():
            print('RESTARTING t1', self.player)
            self.t1 = self.pool.submit(self.process_output_queue)

    def process_send_queue(self):
        try:
            while True:
                while not self.send_queue.empty():
                    cmd = self.send_queue.get()
                    cmd.send_serial()
                time.sleep(.0000000001)
        except Exception as e:
            print(getattr(e, 'message', repr(e)))

    def add_to_send_queue(self, command):
        self.send_queue.put(command)
        if not self.t2.running():
            print('RESTARTING t2', self.player)
            self.t2 = self.pool.submit(self.process_send_queue)

    def start(self):
        if 'MameStart' in self.general_config:
            self.enabled = True
            self.add_to_send_queue(Command(self.comm, self.general_config['MameStart'], self.get_window_time()))

    def stop(self):
        if 'MameStop' in self.general_config:
            self.enabled = False
            self.add_to_send_queue(Command(self.comm, self.general_config['MameStop'], self.get_window_time()))

    def pause(self, val):
        self.enabled = bool(val)

    def open_com(self):
        if self.port not in [port.device for port in list_ports.comports()]:
            print("WARNING:", self.port, "NOT FOUND")
            return
        try:
            ser = serial.Serial(self.port, int(self.init['baudrate']), int(self.init['bytesize']), self.init['parity'], int(self.init['stopbits']), float(self.init['timeout']), rtscts=bool(self.init['rtscts']), dsrdtr=bool(self.init['dsrdtr']))
            return ser
        except Exception as e:
            print(getattr(e, 'message', repr(e)))

    def load_config(self, name):
        config = get_game_config(name, self.profile)
        self.full_config = {key: config[section][key] for section in config for key in config[section] if config[section][key]}
        self.general_config = {key: config['General'][key] for key in config['General'] if config['General'][key]}
        self.key_states_config = {key: config['KeyStates'][key] for key in config['KeyStates'] if
                                  config['KeyStates'][key]}
        self.output_config = {key: config['Output'][key] for key in config['Output'] if config['Output'][key]
                              if not regex_patterns.player.match(key) or
                              key[:2] == "P" + self.player or key[:7] == "Player" + self.player}
