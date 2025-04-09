import serial
import time


class Command:
    def __init__(self, comm, command, data_time=None, expired=False):
        self.comm = comm
        self.serial_command = command
        self.data_time = data_time or time.perf_counter_ns()
        self.expired = expired

    def send_serial(self):
        if self.serial_command is None:
            return
        try:
            if not self.expired:
                self.comm.write(bytes(self.serial_command.encode()))

            # print(self.data_time, time.perf_counter_ns(), self.serial_command, self.expired)
            # tmp = self.comm.readline()
        except (OSError, serial.SerialTimeoutException):
            self.comm.close()
            self.comm.open()
            print(self.comm.port, 'REOPENED')
