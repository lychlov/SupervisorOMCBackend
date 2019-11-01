import json
import socket
import struct
import threading
import math
import sched
from alarms.Alarm import Alarm
from adapters.MQAdapter import MQAdapter
from django.core.cache import cache
import select
import time
import redis

from utils.MsgTypeEnum import MsgTypeEnum
from utils.SocketMessage import SocketMessage
from backends.check_tasks import alarm_check
import logging

SPEED_INTERVAL = 5


def setup_django_env():
    import os
    import django

    config = 'OMC_Checker.settings'
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", config)
    django.setup()


class SocketAdapter(object):
    # host = '10.87.86.213'
    host = '10.87.67.59'
    port = 31232
    username = 'nmsu4'
    password = 'Nmsvfr4'
    req_id = 1
    status_record = {'status': 'stop',
                     'start_time': 0,
                     'end_time': 0,
                     }
    current_seq = 0
    alarm_count = 0
    message_count = 0
    recv_t = None
    heartbeat_t = None
    speed_test_t = None
    flag = False
    sk = None

    def __init__(self, host, port, username, password):
        setup_django_env()
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.logger = logging.getLogger('socket-adapter')
        self.logger.setLevel(logging.INFO)
        self.start_time = int(time.time())
        self.cache_pre = '{}@{}:'.format(self.start_time, self.host)
        pool = redis.ConnectionPool(host='localhost', port=6379, db=2)
        self.r = redis.Redis(connection_pool=pool)
        self.sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.mq = MQAdapter('10.217.2.36', 61613)

        cache.set(self.cache_pre + 'latency', 0, timeout=None)
        cache.set(self.cache_pre + 'new_alarm_count', 0, timeout=None)
        cache.set(self.cache_pre + 'message_count', 0, timeout=None)
        cache.set(self.cache_pre + 'alarm_count', 0, timeout=None)

    def send_message(self, msg_tpy: 'int' = 0, msg_body: 'str' = ''):
        sm = SocketMessage(msg_tpy, msg_body)
        self.logger.warning(
            '发送消息-req_id:{},type:{},time:{},body:{}'.format(self.req_id, sm.message_type, sm.time_seconds, sm.body))
        self.req_id += 1
        self.mq.send_log('info',
                         '发送消息-req_id:{},type:{},time:{},body:{}'.format(self.req_id, sm.message_type, sm.time_seconds,
                                                                         sm.body))
        threading.Thread(target=self.sent_to_omc, args=(self.sk, sm.get_message(),)).start()

    def recv_message(self):
        self.recv_t = threading.Thread(target=self.read_from_omc, args=(self.sk,))
        self.recv_t.start()

    def sync_alarm_msg(self, alarm_seq: 'int' = 1):
        self.send_message(MsgTypeEnum.reqSyncAlarmMsg.value,
                          'reqSyncAlarmMsg;reqId={};alarmSeq={}'.format(self.req_id, alarm_seq))

    def sync_alarm_file(self, start_time: 'str' = '', end_time: 'str' = '', alarm_seq: 'int' = 1,
                        sync_source: 'int' = 0):
        if start_time and end_time:
            self.send_message(MsgTypeEnum.reqSyncAlarmFile.value,
                              'reqSyncAlarmFile;reqId={};startTime={};endTime={}; syncSource ={}'.format(
                                  self.req_id, start_time, end_time, sync_source))
        else:
            self.send_message(MsgTypeEnum.reqSyncAlarmFile.value,
                              'reqSyncAlarmFile;reqId={};alarmSeq={};syncSource ={}'.format(
                                  self.req_id, alarm_seq, sync_source))

    def req_login_ftp(self):
        self.send_message(MsgTypeEnum.reqLoginAlarm.value,
                          'reqLoginAlarm;user={};key={};type=ftp'.format(self.username, self.password))

    def req_login_msg(self):
        self.send_message(MsgTypeEnum.reqLoginAlarm.value,
                          'reqLoginAlarm;user={};key={};type=msg'.format(self.username, self.password))

    def connect(self):
        self.sk.connect((self.host, self.port))
        self.flag = True
        self.req_login_msg()
        self.req_login_ftp()
        self.start_heartbeat()
        self.start_speed_test()
        self.recv_message()
        self.status_record['status'] = 'running'
        self.status_record['start_time'] = self.start_time
        cache.set(self.cache_pre + 'status_record', self.status_record)
        self.mq.send_data('start', {'status': 'running',
                                    'timestamp': self.start_time})

    def close(self):
        self.mq.send_data('stopping', {'status': 'stopping',
                                       'timestamp': int(time.time())})
        self.send_message(MsgTypeEnum.closeConnAlarm.value, 'closeConnAlarm')
        self.flag = False
        self.recv_t.join(timeout=0)
        self.logger.info('接收关闭')
        self.speed_test_t.join(timeout=0)
        self.heartbeat_t.join(timeout=0)
        self.logger.info('心跳关闭')
        self.sk.close()
        self.status_record['status'] = 'closed'
        self.status_record['end_time'] = int(time.time())
        cache.set(self.cache_pre + 'status_record', self.status_record)
        self.mq.send_data('stopped', {'status': 'stopped',
                                      'timestamp': int(time.time())})

    def start_heartbeat(self):
        self.heartbeat_t = threading.Thread(target=self.keep_heartbeat)
        self.heartbeat_t.start()

    def start_speed_test(self):
        self.speed_test_t = threading.Thread(target=self.speet_test)
        self.speed_test_t.start()

    def speet_test(self):
        while self.flag:
            counts = len(self.r.keys(self.cache_pre + 'message:*'))
            # print('speed:{}:{}'.format(counts, math.ceil(counts / SPEED_INTERVAL)))
            self.mq.send_data('speed', {'speed_in_5': math.ceil(counts / SPEED_INTERVAL),
                                        'timestamp': int(time.time())})
            time.sleep(SPEED_INTERVAL)

    def keep_heartbeat(self):
        while self.flag:
            self.send_message(MsgTypeEnum.reqHeartBeat.value, 'reqHeartBeat;reqId={}'.format(self.req_id))
            time.sleep(60)

    def read_from_omc(self, sk):
        while True:
            sm = None
            body = b''
            # try:
            header = sk.recv(9)
            header_decode = [-1, -1, -1, -1]
            header_decode = struct.unpack('>HbiH', header)
            if header_decode[3] >= 0:
                body = sk.recv(header_decode[3])
            else:
                pass
            if body:
                sm = SocketMessage(recv_msg=b''.join([header, body]))
            else:
                sm = ''
            # print(sm)
            if sm.message_type == MsgTypeEnum.realTimeAlarm.value:
                alarm_dict = json.loads(sm.body)
                alarm = Alarm(alarm_dict)
                # TODO 告警消息计数
                cache.incr(self.cache_pre + 'message_count')
                self.message_count += 1
                self.mq.send_data('message_count', {'message_count': self.message_count})
                # TODO 告警消息测速
                self.r.set(self.cache_pre + 'message:{}'.format(alarm.alarmSeq), '1', px=SPEED_INTERVAL * 1000 + 50)
                if alarm.alarmStatus == 1:
                    self.r.set(self.cache_pre + 'active:{}'.format(alarm.alarmId), str(sm), ex=None)
                    cache.incr(self.cache_pre + 'alarm_count')
                    self.alarm_count += 1
                    self.mq.send_data('alarm_count', {'alarm_count': self.alarm_count})
                else:
                    if self.r.get(self.cache_pre + 'active:{}'.format(alarm.alarmId)):
                        self.logger.info("告警正常清除-alarmId:{};alarmTitle:{}".format(alarm.alarmId, alarm.alarmTitle))
                        self.mq.send_log('info',
                                         "告警正常清除-alarmId:{};alarmTitle:{}".format(alarm.alarmId, alarm.alarmTitle))
                        self.r.delete(self.cache_pre + 'active:{}'.format(alarm.alarmId))
                    else:
                        self.logger.error(
                            '告警时序异常-alarmSeq:{};alarmId:{};alarmTitle:{}'.
                                format(alarm.alarmSeq, alarm.alarmId, alarm.alarmTitle))
                        self.mq.send_log("error", '告警时序异常-alarmSeq:{};alarmId:{};alarmTitle:{}'
                                         .format(alarm.alarmSeq, alarm.alarmId, alarm.alarmTitle))
                # 缓存告警
                if self.start_time > alarm.alarmTimeStamp:
                    self.logger.info('缓存告警-timeStamp:{};body:{}'.format(alarm.alarmTimeStamp, sm.body))
                    self.mq.send_log('info', '缓存告警-timeStamp:{};body:{}'.format(alarm.alarmTimeStamp, sm.body))
                # 实时告警
                else:
                    alarm_check.delay(alarm_dict)
                    # TODO 告警消息时延
                    latency_item = sm.time_seconds - alarm.alarmTimeStamp
                    print("告警时延-本机时间:{};消息时间:{};告警时间:{};计算时延:{}".format(int(time.time()), sm.time_seconds,
                                                                        alarm.alarmTimeStamp, latency_item))
                    if latency_item < 0:
                        self.logger.error("告警时延异常-latency:{};body:{}".format(latency_item, sm.body))
                        self.mq.send_log('error', "告警时延异常-latency:{};body:{}".format(latency_item, sm.body))
                    else:
                        cache.incr(self.cache_pre + 'new_alarm_count')
                        cache.incr(self.cache_pre + 'latency', latency_item)
                        if latency_item > 5:
                            self.logger.error("告警时延超长-latency:{};body:{}".format(latency_item, sm.body))
                            self.mq.send_log('error', "告警时延超长-latency:{};body:{}".format(latency_item, sm.body))
                        self.mq.send_data('latency', {'latency_item': latency_item,
                                                      'new_alarm_count': cache.get(
                                                          self.cache_pre + 'new_alarm_count'),
                                                      'latency_sum': cache.get(self.cache_pre + 'latency')})
                    # print(cache.get(self.cache_pre + 'new_alarm_count'))
                    # print(cache.get(self.cache_pre + 'latency'))
                    # TODO 序列号检查
                    if self.current_seq != alarm.alarmSeq - 1 \
                            and 0 != self.current_seq:
                        # TODO 序列号错误
                        self.logger.error("序列号错误-alarmSeq:{}".format(alarm.alarmSeq))
                        self.mq.send_log('error', "序列号错误-alarmSeq:{}".format(alarm.alarmSeq))

                    self.current_seq = alarm.alarmSeq
                    self.mq.send_data('current_seq', {'current_seq': self.current_seq})

            elif sm.message_type == MsgTypeEnum.ackHeartBeat.value:
                self.logger.info('心跳消息-timeStamp:{}'.format(sm.time_seconds))
                self.mq.send_log('info', '心跳消息-timeStamp:{}'.format(sm.time_seconds))
            elif sm.message_type == MsgTypeEnum.ackSyncAlarmFile.value:
                self.logger.info('文件请求响应-timeStamp:{};body:{}'.format(sm.time_seconds, sm.body))
                self.mq.send_log('info', '文件请求响应-timeStamp:{};body:{}'.format(sm.time_seconds, sm.body))
            elif sm.message_type == MsgTypeEnum.ackSyncAlarmFileResult.value:
                self.logger.info('文件同步结果-timeStamp:{};body:{}'.format(sm.time_seconds, sm.body))
                self.mq.send_log('info', '文件同步结果-timeStamp:{};body:{}'.format(sm.time_seconds, sm.body))
            elif sm.message_type == MsgTypeEnum.ackLoginAlarm.value:
                self.logger.info('登录请求响应-timeStamp:{};body:{}'.format(sm.time_seconds, sm.body))
                self.mq.send_log('info', '登录请求响应-timeStamp:{};body:{}'.format(sm.time_seconds, sm.body))
            else:
                self.logger.error('未知消息:{}'.format(sm.body))
                self.mq.send_log('error', '未知消息:{}'.format(sm.body))

    @staticmethod
    def sent_to_omc(sk, sm):
        # try:
        #     sk.connect((self.host, self.port))
        # except:
        #     pass
        sk.send(sm)


# if __name__ == "__main__":
#     sa = SocketAdapter('10.87.67.59', 31232, 'nmsu4', 'Nmsvfr4')
#     #     sa.logger.info('开始测试')
#     sa.connect()
#     #     print(cache.get(sa.cache_pre + 'status_record'))
#     time.sleep(5)
#     # sa.sync_alarm_msg(1496888)
#     #
#     #     # time.sleep(5)
#     #     counts = len(sa.r.keys(sa.cache_pre + 'message:*'))
#     #     print('{}:{}'.format(counts, counts / 5))
#     #
#     #     # sa.send_message(MsgTypeEnum.reqLoginAlarm.value, 'reqLoginAlarm;user={};key={};type=msg'.format('nmsu4', 'Nmsvfr4'))
#     #     # threading.Thread(target=sa.keep_heartbeat).start()
#     #     sa.sync_alarm_file(alarm_seq=1, sync_source=0)
#     time.sleep(5)
#     #     # sa.send_message(MsgTypeEnum.reqSyncAlarmMsg.value, 'reqSyncAlarmMsg;reqId=2;alarmSeq=60000')
#     #     # sa.sync_alarm_msg(62000)
#     #     # time.sleep(10)
#     sa.sync_alarm_file(alarm_seq=1, sync_source=1)
#     #     # sa.sync_alarm_msg(60400)
#     #     # sa.send_message(MsgTypeEnum.reqSyncAlarmMsg.value, 'reqSyncAlarmMsg;reqId=2;alarmSeq=1')
#     #     # sa.send_message(MsgTypeEnum.reqSyncAlarmMsg.value, 'reqSyncAlarmMsg;reqId=2;alarmSeq=60000')
#     # sa.close()
