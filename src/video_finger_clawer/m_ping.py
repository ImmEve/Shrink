import time
import matplotlib.pyplot as plt
import pandas as pd
from ping3 import ping


def m_ping_fun(record_path, dest_addr: str, count: int = 4, interval: float = 0, *args, **kwargs):
    timeout = kwargs.get("timeout")
    src = kwargs.get("src")
    unit = kwargs.setdefault("unit", "ms")
    i = 0
    time_list = []
    delay_list = []
    while i < count or count == 0:
        if interval > 0 and i > 0:
            time.sleep(interval)
        cur_time_sec = time.time()
        delay = ping(dest_addr, seq=i, *args, **kwargs)
        if delay is None:
            time_list.append(cur_time_sec)
            delay_list.append(-1)
        elif delay is False:
            time_list.append(cur_time_sec)
            delay_list.append(-1)
        else:
            time_list.append(cur_time_sec)
            delay_list.append(float(delay) / 1000)
        i += 1
    time_list_pd = pd.DataFrame(time_list)
    delay_list_pd = pd.DataFrame(delay_list)
    result = pd.concat([time_list_pd, delay_list_pd], axis=1)
    result.to_csv(record_path, mode='a+', header=False, index=False)


def plt_pic(x, y):
    plt.xlabel("time")
    plt.ylabel("rtt")
    plt.plot(x, y)
    plt.show()


'''
timeout:丢包时间
interval:发包间隔
count:发包数量
size:icmp包负载大小
'''
