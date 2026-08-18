"""HTML-страницы (дашборд)."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent.parent  # app/
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    # Starlette 1.x: request передаётся первым аргументом, в контекст добавится сам.
    return templates.TemplateResponse(request, "index.html")


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    from app import auth

    if not auth.is_admin(request):
        return templates.TemplateResponse(request, "login.html")
    return templates.TemplateResponse(request, "settings.html")
