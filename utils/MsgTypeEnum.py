from enum import Enum


class MsgTypeEnum(Enum):
    realTimeAlarm = 0
    reqLoginAlarm = 1
    ackLoginAlarm = 2
    reqSyncAlarmMsg = 3
    ackSyncAlarmMsg = 4
    reqSyncAlarmFile = 5
    ackSyncAlarmFile = 6
    ackSyncAlarmFileResult = 7
    reqHeartBeat = 8
    ackHeartBeat = 9
    closeConnAlarm = 10
