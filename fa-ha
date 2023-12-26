from fastapi import FastAPI
import requests
from asyncio import to_thread

app = FastAPI()
token = "eyJhbGc...LAkQSbn4"

@app.get("/gm")
async def gm():
    url = "http://localhost:8123/api/services/script/goodmorning"
    headers = {
    "Authorization": f"Bearer {token}",
    "content-type": "application/json",
    }
    r = await to_thread(requests.post, url=url, headers=headers)
    return {"message": "PLEASE CLOSE THIS TAB"}


@app.get("/monitor")
async def monitor():
    url = "http://localhost:8123/api/services/script/toggle_monitor_cast"
    headers = {
    "Authorization": f"Bearer {token}",
    "content-type": "application/json",
    }
    r = await to_thread(requests.post, url=url, headers=headers)
    return {"message":"PLEASE CLOSE THIS TAB" }


