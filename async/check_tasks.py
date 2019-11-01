import redis
from celery import Celery
from alarms.Alarm import Alarm
from adapters.MQAdapter import MQAdapter

app = Celery('check_tasks', broker='redis://localhost:6379/5', backend='redis://localhost:6379/6')

app.conf.update(
    result_expires=3600,
)

pool = redis.ConnectionPool(host='10.217.2.36', port=6379, password='HNtyci!23$')
r = redis.Redis(connection_pool=pool)


@app.task
def add(x, y):
    return x + y


@app.task
def alarm_check(alarm_dict):
    alarm = Alarm(alarm_dict)
    result_check = alarm.check()
    mq = MQAdapter('10.217.2.36', 61613)
    if result_check:
        mq.send_data('error_alarm', {'reason': result_check,
                                     'alarm': alarm_dict})
    rmuid = alarm.objectUID
    result_rmu = r.sismember('rmuid', rmuid)
    if not result_rmu:
        mq.send_data('error_alarm', {'reason': 'RMUID核对失败',
                                     'RMUID': rmuid,
                                     'alarm': alarm_dict})
    return result_check, result_rmu


@app.task
def check_rmuid(alarm_dict):
    pass
