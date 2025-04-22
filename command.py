import time


class Command:
    def __init__(self, comm, command, data_time=None, expired=False, mon_level=0):
        self.comm = comm
        self.serial_command = command
        self.data_time = data_time or time.perf_counter_ns()
        self.expired = expired
        self.mon_level = mon_level

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
