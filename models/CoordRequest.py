from pydantic import BaseModel

class CoordRequest(BaseModel):
    s_lat: float
    s_lon: float
    e_lat: float
    e_lon: float
    config: str
    mode: str
    passengers: int
    temp: float
    oil: float
    current_fuel: float