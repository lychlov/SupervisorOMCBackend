import time
import struct
from .MsgTypeEnum import MsgTypeEnum


class SocketMessage(object):
    body = ''
    message_type = ''
    body_size = ''
    time_seconds = ''
    MSG_START = 65535

    def __init__(self, message_type: "int" = 0, body: 'str' = '', recv_msg: 'bytes' = None):
        self.body = body
        self.message_type = message_type
        self.time_seconds = int(time.time())
        self.body_size = len(body)
        if recv_msg is not None:
            self.body = recv_msg[9:].decode('utf-8')
            header = struct.unpack('>HbiH', recv_msg[:9])
            self.message_type = header[1]
            self.time_seconds = header[2]
            self.body_size = header[3]

    def __str__(self):
        return "timestamp:{} type:{} body:{}".format(str(self.time_seconds), MsgTypeEnum(self.message_type).name,
                                                     self.body)
        # return self.body

    def get_header(self):
        return struct.pack('>HbiH', self.MSG_START, self.message_type, self.time_seconds, self.body_size)

    def get_message(self):
        return b''.join([self.get_header(), self.body.encode('utf-8')])
