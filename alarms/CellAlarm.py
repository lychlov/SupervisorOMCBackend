import alarms


class CellAlarm(alarms):
    def __init__(self, alarm_dict):
        alarms.__init__(self, alarm_dict)
        self.rNeUID = alarm_dict['rNeUID']
        self.rNeName = alarm_dict['rNeName']
        self.rNeType = alarm_dict['rNeType']
