# server.py
import sqlite3
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import ServerSettings

settings = ServerSettings()
BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()

#Cross-Origin Resource Sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def get_index():
    return FileResponse(BASE_DIR / "index.html")


# Database
conn = sqlite3.connect(
    settings.database_path,
    check_same_thread=False,
)

with conn:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp REAL,
        host TEXT,
        cpu REAL,
        memory REAL,
        disk REAL,
        gpu REAL
    )
    """)

# datamodel
class Metrics(BaseModel):
    host: str
    cpu: float
    memory: float
    disk: float
    gpu: Optional[float] = None

# Data reception
@app.post("/metrics")
def receive_metrics(request: Request, data: Metrics):
    client_ip = request.client.host

    #  check IP permitted or not
    if client_ip not in settings.allowed_ips:
        print(f"Access from an unauthorized IP address: {client_ip}")
        return {"error": "forbidden"}

    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO metrics (timestamp, host, cpu, memory, disk, gpu) VALUES (?, ?, ?, ?, ?, ?)",
            (
                time.time(),
                data.host,
                float(data.cpu),
                float(data.memory),
                float(data.disk),
                float(data.gpu) if data.gpu is not None else None
            )
        )
        conn.commit()
        return {"status": "ok"}

    except Exception as e:
        print("DBerror:", e)
        return {"error": str(e)}

#Data update
@app.get("/latest_all")
def get_latest_all():
    cur = conn.cursor()
    now = time.time()

    cur.execute("""
        SELECT host, cpu, memory, disk, gpu, timestamp
        FROM metrics
        WHERE id IN (SELECT MAX(id) FROM metrics GROUP BY host)
    """)
    rows = cur.fetchall()

    result = []
    for r in rows:
        last_time = r[5]
        # comparison of current time and data time
        status = (
            "online"
            if (now - last_time) < settings.offline_threshold_seconds
            else "offline"
        )
        
        result.append({
            "host": r[0],
            "cpu": r[1],
            "memory": r[2],
            "disk": r[3],
            "gpu": r[4],
            "status": status  
        })
    return result

# get history (chart)
@app.get("/history/{host}")
def get_history(host: str):
    cur = conn.cursor()
    cur.execute("""
        SELECT timestamp, cpu, gpu
        FROM metrics
        WHERE host = ?
        ORDER BY id DESC
        LIMIT 20
    """, (host,))

    rows = cur.fetchall()
    rows.reverse() # Sort by oldest first to display on the chart correctly

    return {
        "timestamps": [r[0] for r in rows],
        "cpu": [r[1] for r in rows],
        "gpu": [r[2] for r in rows]
    }
