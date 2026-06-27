from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json

from models.CoordRequest import CoordRequest
from router.processNavigation import process_navigation
from services.testingStaticData import run_synthetic_tests

app = FastAPI()

with open("team_data.json", "r", encoding="utf-8") as f:
    TEAM_DATA = json.load(f)

app.mount("/static", StaticFiles(directory="static"), name="static")

# ОТДАЕТ ИНТЕРФЕЙС
@app.get("/")
def read_root():
    # Убедитесь, что путь до вашего index.html правильный
    return FileResponse("static/html/index.html")

# ОТДАЕТ СКРИПТ ОФФЛАЙНА
@app.get("/sw.js")
def read_sw():
    return FileResponse("static/js/sw.js", media_type="application/javascript")

@app.post("/calculate-route")
def calculate_route(req: CoordRequest):
    return process_navigation(
        TEAM_DATA, req.s_lat, req.s_lon, req.e_lat, req.e_lon,
        req.config, req.mode, req.passengers, req.temp, req.oil
    )

@app.get("/run-tests")
def run_tests():
    return run_synthetic_tests(TEAM_DATA)