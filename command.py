import hid
import time
import hid_rules


class Command:
    def __init__(self, device, command, data_time=None, expired=False, mon_level=0):
        self.comm = device.comm
        self.device = device
        self.hid_command = hid_rules.get_hid(command, self.device.profile)
        self.serial_command = command
        self.data_time = data_time or time.perf_counter_ns()
        self.expired = expired
        self.mon_level = mon_level

    def send(self):
        if self.hid_command is not None and self.device.hid_path is not None:
            self.send_hid()
        elif self.device.comm is not None:
            self.send_serial()

    def send_serial(self):
        if self.serial_command is None:
            return
        try:
            if not self.expired and self.comm.is_open:
                self.comm.write(bytes(self.serial_command.encode()))

            if self.mon_level == 2:
                print(self.data_time, time.perf_counter_ns(), self.serial_command, self.expired)
            if self.mon_level == 3 and self.comm.is_open:
                line = self.comm.readline()
                if line:
                    print(line)

        except Exception as e:
            print(self.comm.port, 'EXCEPTION send_serial')
            print(getattr(e, 'message', repr(e)))
            self.comm.close()
            self.comm.open()
            print(self.comm.port, 'REOPENED')

    def send_hid(self):
        try:
            with hid.Device(path=self.device.hid_path) as device:
                for c in self.hid_command:
                    device.write(bytes(c))
                    print(bytes(c))
        except Exception as e:
            print(f"Failed to send HID output report: {e}")
