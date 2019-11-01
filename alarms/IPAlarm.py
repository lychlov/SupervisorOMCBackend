import alarms


class IPAlarm(alarms):
    def __init__(self, alarm_dict):
        alarms.__init__(self, alarm_dict)
        self.neIp = alarm_dict['neIp']
        self.pairFlag = alarm_dict['pairFlag']
        self.alarmCount = alarm_dict['alarmCount']
