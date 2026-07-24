"""Pydantic-модели для контентного бандла — структура данных, которую получает фронтенд."""

from datetime import datetime

from pydantic import BaseModel, Field


class TripConfig(BaseModel):
    name: str
    boat: str = "TBD"
    dates: str = "TBD"
    departure_date: str = ""


class Waypoint(BaseModel):
    name: str
    lat: float
    lng: float
    description: str = ""


class Route(BaseModel):
    waypoints: list[Waypoint] = Field(default_factory=list)


class ContentPage(BaseModel):
    filename: str
    title: str
    html_content: str
    raw_markdown: str
    template: str = ""
    structured_data: dict = Field(default_factory=dict)


class Section(BaseModel):
    id: str
    title: str
    icon: str
    tab: str
    pages: list[ContentPage] = Field(default_factory=list)


class ContentBundle(BaseModel):
    trip: TripConfig
    sections: list[Section] = Field(default_factory=list)
    route: Route = Field(default_factory=Route)
    content_hash: str = ""
    built_at: str = Field(default_factory=lambda: datetime.now().isoformat())
