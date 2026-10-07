# agent.py
# This python file on the server you want to monitor
#Required libraries psutil requests GPUtil

import psutil
import time
import requests
import socket

from config import AgentSettings

settings = AgentSettings()

#GPU
try:
    import GPUtil #if the server has GPU
except:
    GPUtil = None #if the server doesn't have GPU

HOSTNAME = socket.gethostname() #For server identification

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
        cpu = psutil.cpu_percent(
            interval = settings.cpu_sample_interval_seconds
        )
        memory = psutil.virtual_memory().percent
        disk = psutil.disk_usage(settings.disk_path).percent
        gpu = get_gpu_usage()

        data = {
            "host": HOSTNAME,
            "cpu": float(cpu),
            "memory": float(memory),
            "disk": float(disk),
            "gpu": float(gpu) if gpu is not None else None
        }

        res = requests.post(
            str(settings.server_url),
            json = data,
            timeout=settings.request_timeout_seconds,
        )
    
    except Exception as e:
        print(f"Sending Failed:{e}")

    #Transmission interval
    time.sleep(settings.send_interval_seconds)
