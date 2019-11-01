import alarms


class TransAlarm(alarms):
    def __init__(self, alarm_dict):
        alarms.__init__(self, alarm_dict)
        self.holderType = alarm_dict['holderType']
        self.alarmCheck = alarm_dict['alarmCheck']
        self.layer = alarm_dict['layer']
