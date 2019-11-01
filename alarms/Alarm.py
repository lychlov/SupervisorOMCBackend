import time

words = ['alarmTitle', 'alarmType', 'origSeverity', 'eventTime', 'alarmId', 'specificProblemID',
         'specificProblem', 'neUID', 'neName', 'neType', 'objectUID', 'objectName', 'objectType', 'locationInfo']


class Alarm(object):
    def __init__(self, alarm_dict):
        self.alarmSeq = alarm_dict['alarmSeq']
        self.alarmTitle = alarm_dict['alarmTitle']
        self.alarmStatus = alarm_dict['alarmStatus']
        self.alarmType = alarm_dict['alarmType']
        self.origSeverity = alarm_dict['origSeverity']
        self.eventTime = alarm_dict['eventTime']
        self.alarmId = alarm_dict['alarmId']
        self.specificProblemID = alarm_dict['specificProblemID']
        self.specificProblem = alarm_dict['specificProblem']
        self.neUID = alarm_dict['neUID']
        self.neName = alarm_dict['neName']
        self.neType = alarm_dict['neType']
        self.objectUID = alarm_dict['objectUID']
        self.objectName = alarm_dict['objectName']
        self.objectType = alarm_dict['objectType']
        self.locationInfo = alarm_dict['locationInfo']
        self.addInfo = alarm_dict['addInfo']
        try:
            time_array = time.strptime(self.eventTime, "%Y-%m-%d %H:%M:%S")
            self.alarmTimeStamp = int(time.mktime(time_array))
        except:
            self.alarmTimeStamp = 0
        self.alarmDict = alarm_dict
        self.error = []

    def check(self):
        for word in words:
            if not self.alarmDict[word] or self.alarmDict[word] == 0:
                self.error.append('字段缺失'.format(word))
        if self.origSeverity not in [1, 2, 3, 4]:
            self.error.append('原始级别错误')
        if self.alarmStatus not in [1, 0]:
            self.error.append('告警状态错误')
        if not self.alarmTimeStamp:
            self.error.append('事件时间错误')
        return self.error
