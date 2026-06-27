from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import json
import navigator

app = FastAPI()
with open("team_data.json", "r", encoding="utf-8") as f:
    team_data = json.load(f)

app.mount("/static", StaticFiles(directory="static"), name="static")

class CoordRequest(BaseModel):
    s_lat: float; s_lon: float
    e_lat: float; e_lon: float
    config: str; mode: str
    passengers: int; temp: float; oil: float

@app.get("/")
def read_root(): return FileResponse("static/html/index.html")

@app.post("/calculate-route")
def calculate_route(req: CoordRequest):
    return navigator.process_navigation(
        team_data, req.s_lat, req.s_lon, req.e_lat, req.e_lon,
        req.config, req.mode, req.passengers, req.temp, req.oil
    )

@app.get("/run-tests")
def run_tests():
    return navigator.run_synthetic_tests(team_data)