import serial
import time


class Command:
    def __init__(self, comm, command, window_time, data_time=None):
        self.comm = comm
        self.serial_command = command
        self.data_time = data_time or time.perf_counter_ns()
        self.window_time = window_time or time.perf_counter_ns()

    def send_serial(self):
        if time.perf_counter_ns() > self.window_time:
            print(self.serial_command, 'window expired')
            return

        if self.serial_command is None:
            return
        try:
            # print(bytes(self.serial_command.encode()))
            self.comm.write(bytes(self.serial_command.encode()))
        except (OSError, serial.SerialTimeoutException):
            self.comm.close()
            self.comm.open()
            print('Serial COM REOPENED')
        # print(self.get_age())

    def get_age(self):
        return int((time.perf_counter_ns() - self.data_time) / 1000)  # in μs
