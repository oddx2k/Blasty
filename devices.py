import concurrent.futures
import queue
import time
import serial
import regex_patterns
from serial.tools import list_ports
from configuration import get_game_config
from command import Command


class Device:
    def __init__(self, player_id, profile, init, monitor=0):
        self.player_id = player_id
        self.profile = profile
        self.monitor = bool(int(monitor))
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
        self.temp_vars = {}
        self.enabled = True
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self.t1 = self.pool.submit(self.process_output_queue)
        self.t2 = self.pool.submit(self.process_send_queue)
        self.filter = ['lwp', 'lws', 'lwc', 'lwr', 'lwk', 'iws', 'iwc', 'iwr', 'iwk', 'mls', 'mlc', 'mlr', 'mlk', 'lhs',
                       'lhc', 'lhr', 'lhk', 'uls', 'uli', 'ulf', 'uld', 'ulc', 'ulp', 'ulk', 'ghd', 'kbd', 'spk', 'ply',
                       'pya', 'dsp', 'dss', 'dff', 'ffa', 'xip', 'xia', 'wii', 'lpt', 'lpe', 'cmo', 'cmc', 'css', 'csl',
                       'cmr', 'cmw', 'lds', 'sds', 'sdf', 'sbf', 'ibf', 'bmo', 'cpy', 'kll', 'log', 'nll', 'wat', 'rfs',
                       'lop', 'lfs', 'kls', 'lwa', 'cmd', 'cdw', 'qut', 'ref', '']

    def compute(self, exp, val):
        exp = self.sub_var_tokens(exp, val)
        exp = regex_patterns.mod.sub(r'%', exp)
        exp = regex_patterns.eval_filter.sub('', exp)
        return int(eval(exp))

    def put_var(self, name, value):
        if name not in self.temp_vars:
            self.temp_vars[name] = {}

        if "values" not in self.temp_vars[name]:
            self.temp_vars[name]['values'] = [value]
        else:
            if value not in self.temp_vars[name]['values']:
                self.temp_vars[name]['values'].append(value)

        if "last" in self.temp_vars[name]:
            last = int(self.temp_vars[name]['last'])
            if int(value) + 1 < last or int(value) - 1 > last and int(value) > 0:
                self.temp_vars[name]['values'] = [value]

        self.temp_vars[name]['last'] = value

    def get_var(self, name):
        if name in self.temp_vars and "last" in self.temp_vars[name]:
            return self.temp_vars[name]["last"]
        return 0

    def get_var_max(self, name):
        if name in self.temp_vars and "values" in self.temp_vars[name]:
            values = [int(value) for value in self.temp_vars[name]["values"] if value.isnumeric()]
            if values:
                return max(values)
        return 0

    def get_var_min(self, name):
        if name in self.temp_vars and "values" in self.temp_vars[name]:
            values = [int(value) for value in self.temp_vars[name]["values"] if value.isnumeric()]
            if values:
                return min(values)
        return 0

    def var_color_wheel(self, clw, var_max, val):
        def lerp(start, end, v):
            return start + v * (end - start)

        def transition(i, n=2):
            return list(zip(*(i[p:] for p in range(n))))

        def hex_rgb(color):
            return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))

        def rgb_hex(r, g, b):
            return '{:02X}{:02X}{:02X}'.format(r, g, b)

        if clw is None:
            return 0

        if len(clw) == 1:
            return clw[0]

        transitions = transition(clw, 2)

        t = len(transitions) / int(var_max) * (int(var_max) - int(val))

        return rgb_hex(int(lerp(hex_rgb(transitions[int(t)][0])[0], hex_rgb(transitions[int(t)][1])[0], t - int(t))),
                       int(lerp(hex_rgb(transitions[int(t)][0])[1], hex_rgb(transitions[int(t)][1])[1], t - int(t))),
                       int(lerp(hex_rgb(transitions[int(t)][0])[2], hex_rgb(transitions[int(t)][1])[2], t - int(t))))

    def skip_value(self, out, val):
        match = regex_patterns.skip.search(out)
        while match is not None:
            var_skp = match.group(2).split(':')
            if val in var_skp:
                out = regex_patterns.skip.sub('', out, 1)
            else:
                out = regex_patterns.skip.sub(match.group(1), out, 1)

            match = regex_patterns.skip.search(out)

            if self.monitor and bool(int(self.general_config['Monitor'])):
                print(self.init['port'], out)

        return out

    def sub_var_tokens(self, out, val):
        # if self.monitor and bool(int(self.general_config['Monitor'])):
        #     print(self.init['port'], out)

        match = regex_patterns.var_token.search(out)
        while match is not None:
            match match.group(0):
                case _ if match.group(0) in ['#s#', '#S#']:
                    out = regex_patterns.var_token.sub(val, out, 1)

                case _ if match.group(1)[:3] == 'HEX':
                    var_hex = str(int(match.group(1)[3:], 16))
                    out = regex_patterns.var_token.sub(var_hex, out, 1)

                case _ if match.group(1)[:3] == 'MAX':
                    var_max = str(self.get_var_max(match.group(1)[3:]))
                    out = regex_patterns.var_token.sub(var_max, out, 1)

                case _ if match.group(1)[:3] == 'MIN':
                    var_min = str(self.get_var_min(match.group(1)[3:]))
                    out = regex_patterns.var_token.sub(var_min, out, 1)

                case _ if match.group(1)[:3] == 'VAR':
                    self.put_var(match.group(1)[3:], val)
                    out = regex_patterns.var_token.sub('', out, 1)

                case _ if match.group(1)[:3] == 'CLW':
                    var_clw = match.group(1)[3:].split(':')
                    var_max = self.get_var_max(var_clw.pop(0))
                    var_clw = [v for v in var_clw if regex_patterns.hex_filter.match(v) and
                               len(regex_patterns.hex_filter.match(v).group(0)) == 6]
                    color = 0
                    if var_max:
                        color = int(self.var_color_wheel(var_clw, var_max, val), 16)
                    out = regex_patterns.var_token.sub(str(color), out, 1)

                case _:
                    out = regex_patterns.var_token.sub('', out, 1)

            match = regex_patterns.var_token.search(out)

        if self.monitor and bool(int(self.general_config['Monitor'])):
            print(self.init['port'], out)

        return out.strip(',')

    def sub_tokens(self, output, value):
        out = self.get_output(self.output_config, output, value)

        if self.monitor and bool(int(self.general_config['Monitor'])):
            print(self.init['port'], out)

        out = self.skip_value(out, value)
        out = self.sub_var_tokens(out, value)
        match = regex_patterns.token.search(out)
        while match is not None:
            match match.group(0):
                case _ if match.group(1)[:3] == 'RMP':
                    remap = regex_patterns.remap.search(match.group(1)[3:])
                    if remap is not None and remap.group(1) == value:
                        new = self.get_output(self.full_config, output, remap.group(2))
                        if 'RMP' not in new:
                            out = new
                    out = regex_patterns.token.sub('', out, 1)

                case _ if match.group(1)[:3] == 'EVL':
                    v = self.compute(match.group(1)[3:], value)
                    new = self.get_output(self.full_config, output, v)
                    if 'EVAL' not in new:
                        out = regex_patterns.token.sub(new, out, 1)
                    else:
                        out = regex_patterns.token.sub(self.get_output(self.full_config, output, 0), out, 1)

                case _ if match.group(1)[:3] == 'RVL':
                    v = self.compute(match.group(1)[3:], value)
                    out = regex_patterns.token.sub(str(v), out, 1)

                case _ if regex_patterns.cleanup.search(match.group(0)):
                    out = regex_patterns.cleanup.sub(r',(\1),', out)

                case _:
                    out = regex_patterns.token.sub(self.get_output(self.full_config, match.group(1), value) or '', out, 1)

            out = self.skip_value(out, value)
            out = self.sub_var_tokens(out, value)
            match = regex_patterns.token.search(out)
        out = regex_patterns.extra_comma.sub(r',', out)

        if self.monitor and bool(int(self.general_config['Monitor'])):
            print(self.init['port'], out)

        return out

    def get_output(self, config, output, value):
        if output not in config:
            return None
        if len(config[output].split('|')) > int(value):
            return config[output].split('|')[int(value)]
        return config[output].split('|')[-1]

    def get_max_time(self, data_time):
        return int(data_time + (self.max_rate * 1000000000))

    def process_output_queue(self):
        try:
            time_queue = {}
            blocks = {}
            ready_queue = queue.Queue()
            while True:
                while not self.output_queue.empty():
                    output, value, data_time = self.output_queue.get()

                    if output not in self.output_config:
                        continue

                    if self.monitor and bool(int(self.general_config['Monitor'])):
                        print(self.init['port'], "PROCESS:", output, value)

                    out = self.sub_tokens(output, value)

                    if self.monitor and bool(int(self.general_config['Monitor'])):
                        print(self.init['port'], "RESULT: ", out)

                    if out:
                        time_queue[time.perf_counter_ns()] = (out, data_time, 0)

                for c in list(time_queue):
                    if time.perf_counter_ns() > int(c):
                        ready_queue.put(c)

                for b in list(blocks):
                    if time.perf_counter_ns() > int(blocks[b]):
                        del blocks[b]

                while not ready_queue.empty():
                    # print(time_queue)
                    expired = False
                    out, data_time, offset = time_queue.pop(ready_queue.get())

                    if time.perf_counter_ns() > (self.get_max_time(data_time) + offset):
                        expired = True
                    elif out in blocks:
                        time_queue[time.perf_counter_ns()] = (out, data_time, offset)
                        continue
                    else:
                        blocks[out] = self.get_max_time(time.perf_counter_ns())

                    for i, o in enumerate(out.split(',')):
                        if o[:3] not in self.filter:
                            match = regex_patterns.reval.search(o)
                            if match is not None and not expired:
                                match match.group(1):
                                    case _ if match.group(1)[:4] == 'WAIT':
                                        time.sleep(int(match.group(1)[4:]) * .001)
                                        continue
                                    case _ if match.group(1)[:4] == 'TIME':
                                        time_queue[
                                            time.perf_counter_ns() + int(match.group(1)[4:]) * 1000000] = (",".join(
                                             out.split(',')[i + 1:]), data_time, offset + int(match.group(1)[4:]) * 1000000)
                                    case _ if match.group(1)[:4] == 'TIMR':
                                        rem = ",".join(out.split(',')[i + 1:])
                                        for c in list(time_queue):
                                            if time_queue[c][0] == rem:
                                                del time_queue[c]

                                        time_queue[
                                            time.perf_counter_ns() + int(match.group(1)[4:]) * 1000000] = (",".join(
                                             out.split(',')[i + 1:]), data_time, offset + int(match.group(1)[4:]) * 1000000)
                                    case _:
                                        pass
                                break

                            if self.enabled:
                                self.add_to_send_queue(Command(self.comm, o, data_time, expired))

                time.sleep(.000001)
        except Exception as e:
            print(getattr(e, 'message', repr(e)))

    def add_to_output_queue(self, out, val, data_time):
        self.output_queue.put((out, val, data_time))
        if not self.t1.running():
            print('RESTARTING t1', str(self.player_id))
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
            print('RESTARTING t2', str(self.player_id))
            self.t2 = self.pool.submit(self.process_send_queue)

    def start(self):
        if 'MameStart' in self.general_config:
            self.enabled = True
            self.add_to_send_queue(Command(self.comm, self.general_config['MameStart']))

    def stop(self):
        if 'MameStop' in self.general_config:
            self.enabled = False
            self.add_to_send_queue(Command(self.comm, self.general_config['MameStop']))

    def pause(self, val):
        self.enabled = bool(val)

    def open_com(self):
        if self.init['port'] not in [port.device for port in list_ports.comports()]:
            print("WARNING:", self.init['port'], "NOT FOUND")
            return
        try:
            ser = serial.Serial()
            ser.port = self.init['port']
            ser.baudrate = int(self.init['baudrate'])
            ser.bytesize = int(self.init['bytesize'])
            ser.parity = self.init['parity']
            ser.stopbits = int(self.init['stopbits'])
            ser.timeout = float(self.init['timeout'])
            ser.rtscts = bool(self.init['rtscts'])
            ser.dsrdtr = bool(self.init['dsrdtr'])
            ser.open()
            if ser.is_open:
                return ser
        except Exception as e:
            print(getattr(e, 'message', repr(e)))

        return None

    def load_config(self, name):
        config = get_game_config(name, self.profile)
        self.full_config = {key: config[section][key] for section in config for key in config[section] if config[section][key]}
        self.general_config = {key: config['General'][key] for key in config['General'] if config['General'][key]}
        self.key_states_config = {key: config['KeyStates'][key] for key in config['KeyStates'] if
                                  config['KeyStates'][key]}
        self.output_config = {key: config['Output'][key] for key in config['Output'] if config['Output'][key]
                              if not regex_patterns.player.match(key) or
                              key[:2] == "P" + str(self.player_id) or key[:7] == "Player" + str(self.player_id)}
        self.max_rate = 1 / (float(self.general_config['MaxRate']) or 10)
