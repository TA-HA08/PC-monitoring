# agent.py
# This python file on the server you want to monitor
#Required libraries psutil requests GPUtil

import psutil
import time
import requests
import socket

#GPU
try:
    import GPUtil #if the server has GPU
except:
    GPUtil = None #if the server doesn't have GPU

HOSTNAME = socket.gethostname() #For server identification

#IP address of the monitoring PC
URL = "http://xxx.xxx.xxx.xxx:port/metrics"

#GPU
def get_gpu_usage():
    if GPUtil is None:
        return None
    
    try:
        gpus = GPUtil.getGPUs()
        if len(gpus) == 0:
            return None
        
        return gpus[0].load * 100
    except:
        return None
    

while True:
    try:
        cpu = psutil.cpu_percent(interval = 0.5)
        memory = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        gpu = get_gpu_usage()

        data = {
            "host": HOSTNAME,
            "cpu": float(cpu),
            "memory": float(memory),
            "disk": float(disk),
            "gpu": float(gpu) if gpu is not None else None
        }

        res = requests.post(URL, json = data, timeout = 1)
    
    except Exception as e:
        print(f"Sending Failed:{e}")

    #Transmission interval
    time.sleep(1)
