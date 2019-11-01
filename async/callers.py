from async.check_tasks import add, alarm_check

alarm_dict = {"alarmSeq": 1164737,
              "alarmTitle": "BTS booted at 2019-06-06 14:18:52 GMT+0800 due to trs power-on reset",
              "alarmStatus": 0,
              "alarmType": "EQUIPMENT",
              "origSeverity": 3,
              "eventTime": "2019-06-06 14:26:26",
              "alarmId": "3152892",
              "specificProblemID": "61006",
              "specificProblem": "BTS booted at 2019-06-06 14:18:52 GMT+0800 due to trs power-on reset",
              "neUID": "4101NSWXUENB0185F3",
              "neName": "ZMBAISHAJIEJUCHENG3DMIMOD-NLH",
              "neType": "ENB",
              "objectUID": "4101NSWXUENB0185F3sdfsdf",
              "objectName": "ZMBAISHAJIEJUCHENG3DMIMOD-NLH",
              "objectType": "EnbFunction",
              "locationInfo": "PLMN-PLMN/MRBTS-557631/LNBTS-557631/FTM-1",
              "addInfo": "DIAGNOSTIC_INFO:additionalFaultId\\:61006\\;;SUPPLEMENTARY_INFO:;USER_ADDITIONAL_INFO:;DN:PLMN-PLMN/MRBTS-557631/LNBTS-557631/FTM-1",
              "rNeUID": "",
              "rNeName": "",
              "rNeType": ""}

result = alarm_check(alarm_dict)
print(result)
