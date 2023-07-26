from typing import Callable

from ace_client.ace_types.user_machine_types import MethodCall
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse


def get_api_router(send_callback: Callable[[MethodCall, Request], JSONResponse]):
    return APIRouter()
