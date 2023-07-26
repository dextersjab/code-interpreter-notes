import asyncio
import inspect
import json
import logging
import os
import sys
import time
import traceback
import urllib.parse
import uuid

import traitlets
from ace_client.ace_types.user_machine_types import *
from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from jupyter_client import AsyncKernelClient, AsyncKernelManager, AsyncMultiKernelManager
from pydantic import parse_obj_as

from . import routes, run_jupyter

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(name)s] %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d,%H:%M:%S",
    stream=sys.stdout,
)

os.chdir(os.path.expanduser("~"))

_MAX_UPLOAD_SIZE = 1024 * 1024 * 1024
_MAX_DOWNLOAD_TIME = 5 * 60.0
_DOWNLOAD_CHUNK_SIZE = 1024 * 1024       
_MAX_JUPYTER_MESSAGE_SIZE = 10 * 1024 * 1024
_MAX_KERNELS = 20

app = FastAPI()

jupyter_config = traitlets.config.get_config()
                                                                      
                                                                   
                       
                                                                      
                                                             
jupyter_config.KernelRestarter.restart_limit = 0
_MULTI_KERNEL_MANAGER = AsyncMultiKernelManager(config=jupyter_config)

_response_to_callback_from_kernel_futures: Dict[str, asyncio.Future] = {}

_timeout_at = {}
_timeout = {}
_timeout_task = None

_kernel_queue = None
_fill_kernel_queue_task = None
_first_kernel_started = False

_SELF_IDENTIFY_HEADER_KEY = "x-ace-self-identify"
_SELF_IDENTIFY_HEADER_KEY_BYTES = b"x-ace-self-identify"
_SELF_IDENTIFY_STR = os.getenv("ACE_SELF_IDENTIFY")
_SELF_IDENTIFY_BYTES = os.getenv("ACE_SELF_IDENTIFY").encode("utf-8")


                                                                                         
async def _kill_old_kernels():
    while True:
        await asyncio.sleep(2.0)
        for kernel_id in list(_timeout_at.keys()):
            if time.monotonic() > _timeout_at[kernel_id]:
                logger.info(
                    f"Killing kernel {kernel_id} due to timeout, {_timeout_at[kernel_id]}, {_timeout[kernel_id]}"
                )
                await _delete_kernel(kernel_id)


async def _fill_kernel_queue():
    global _first_kernel_started, _kernel_queue
    try:
                                                                         
                                                              
        _kernel_queue = asyncio.Queue(maxsize=1)
                                                                                    
                                                                                   
                                          
        kernel_id = None
        kernel_manager = None
        while True:
            logger.info("Create new kernel for pool: Preparing")
            if len(_timeout_at.keys()) >= _MAX_KERNELS:
                logger.info(f"Too many kernels ({_MAX_KERNELS}). Deleting oldest kernel.")
                sort_key = lambda kernel_id: _timeout_at[kernel_id]
                kernels_to_delete = sorted(_timeout_at.keys(), key=sort_key, reverse=True)[
                    _MAX_KERNELS - 1 :
                ]
                for kernel_id in kernels_to_delete:
                    logger.info(f"Deleting kernel {kernel_id}")
                    await _delete_kernel(kernel_id)

            logger.info(f"Create new kernel for pool: Making new kernel")
            start_time = time.monotonic()

            kernel_id = await _MULTI_KERNEL_MANAGER.start_kernel()
            kernel_manager = _MULTI_KERNEL_MANAGER.get_kernel(kernel_id)
            client = kernel_manager.client()
            client.start_channels()
            await client.wait_for_ready()
            client.stop_channels()
            del client

            end_time = time.monotonic()
            logger.info(
                f"Create new kernel for pool: Done making new kernel in {end_time - start_time:.3f} seconds"
            )
            logger.info(
                f"Create new kernel for pool: New kernel id {kernel_id} in {id(_kernel_queue)}"
            )

            _first_kernel_started = True
            await _kernel_queue.put(kernel_id)
    except Exception as e:
        logger.error(f"Error while filling queue: {e}", exc_info=True)
        raise


async def _delete_kernel(kernel_id):
    kernel_ids = _MULTI_KERNEL_MANAGER.list_kernel_ids()
    if kernel_id in kernel_ids:
        kernel_manager = _MULTI_KERNEL_MANAGER.get_kernel(str(kernel_id))
        await kernel_manager.shutdown_kernel()
        _MULTI_KERNEL_MANAGER.remove_kernel(str(kernel_id))
    del _timeout_at[kernel_id]
    del _timeout[kernel_id]


@app.on_event("startup")
async def startup():
    global _timeout_task, _fill_kernel_queue_task
    _timeout_task = asyncio.create_task(_kill_old_kernels())
    _fill_kernel_queue_task = asyncio.create_task(_fill_kernel_queue())


@app.on_event("shutdown")
async def shutdown():
    _timeout_task.cancel()                
    _fill_kernel_queue_task.cancel()                


async def _SEND_CALLBACK_REQUEST(call: MethodCall):
    raise NotImplementedError()


def _is_from_localhost(request: Request) -> bool:
    return request.client.host == "127.0.0.1"


async def _forward_callback_from_kernel(call: MethodCall, request: Request):
    if not _is_from_localhost(request):
        raise HTTPException(status_code=403, detail="Forbidden")

    logger.info(f"Forwarding callback request from kernel. {call}")
    _response_to_callback_from_kernel_futures[call.request_id] = asyncio.Future()
    await _SEND_CALLBACK_REQUEST(call)

    response = await _response_to_callback_from_kernel_futures[call.request_id]
    logger.info(f"Forwarding callback response to kernel: {call.request_id}.")
    del _response_to_callback_from_kernel_futures[call.request_id]
    return JSONResponse({"value": response})


app.include_router(routes.get_api_router(_forward_callback_from_kernel), prefix="")


def _respond_to_callback_from_kernel(response: MethodCallReturnValue):
    logger.info("Received callback response.")
    _response_to_callback_from_kernel_futures[response.request_id].set_result(response.value)


@app.get("/check_liveness")
async def check_liveness():
    code = "print(f'{400+56}')\n100+23\n"
    logger.info("Health check: running...")
    start_time = time.monotonic()
    kernel_id = await _create_kernel(timeout=30.0)
    kernel_manager = _MULTI_KERNEL_MANAGER.get_kernel(kernel_id)
    assert isinstance(kernel_manager, AsyncKernelManager)
    try:
        execute_result, error_stacktrace, stream_text = await run_jupyter.async_run_code(
            kernel_manager, code, shutdown_kernel=False
        )
        status_code = 200
        status = "live"
        if error_stacktrace is not None:
            status_code = 500
            status = "error"
        elif execute_result != {"text/plain": "123"} or stream_text != "456\n":
            status_code = 500
            status = "unexpected_result"
        result = {
            "execute_result": execute_result,
            "stream_text": stream_text,
            "error_stacktrace": error_stacktrace,
            "status": status,
        }
    finally:
        await _delete_kernel(kernel_id)
    end_time = time.monotonic()
    logger.info(f"Health check took {end_time - start_time} seconds and returned {result}")
    return JSONResponse(content=result, status_code=status_code)


@app.get("/check_startup")
async def check_startup():
    if not _first_kernel_started:
        logger.info("Failed health check")
        return JSONResponse(
            content={"status": "failed", "reason": "kernel queue is not initialized"},
            status_code=500,
        )
    logger.info("Passed health check")
    return JSONResponse(content={"status": "started"})


@app.post("/upload")
async def upload(upload_request: str = Form(), file: UploadFile = File()):
    logger.info("Upload request")
    request = parse_obj_as(UploadFileRequest, json.loads(upload_request))
    try:
        total_size = 0
        with open(request.destination, "wb") as f:
            while chunk := file.file.read():
                total_size += len(chunk)
                if total_size > _MAX_UPLOAD_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File too large",
                    )
                f.write(chunk)
    except Exception:
        try:
            os.remove(request.destination)
        except Exception as e:
            logger.exception(f"Error while removing file: {request.destination}", exc_info=e)
        raise

    logger.info(f"Upload request complete. {upload_request}")
    return JSONResponse(content={})


@app.get("/download/{path:path}")
async def download(path: str):
    path = urllib.parse.unquote(path)
    if not os.path.isfile(path):
        raise HTTPException(404, f"File not found: {path}")

    logger.info(f"Download request. {path}")

    def iterfile():
        with open(path, "rb") as f:
            while chunk := f.read(_DOWNLOAD_CHUNK_SIZE):
                yield chunk

    return StreamingResponse(
        iterfile(),
        headers={"Content-Length": f"{os.path.getsize(path)}"},
        media_type="application/octet-stream",
    )


@app.get("/check_file/{path:path}")
async def check_file(path: str):
    path = "/" + urllib.parse.unquote(path)
    logger.info(f"Check file request. {path}")
    exists = os.path.isfile(path)
    size = os.path.getsize(path) if exists else 0
    return CheckFileResponse(exists=exists, size=size, too_large=False)


@app.get("/kernel/{kernel_id}")
async def kernel_state(kernel_id: str):
    logger.info(f"Get kernel state request. {kernel_id}")
    if kernel_id not in _timeout_at:
        time_remaining_ms = 0.0
    else:
        time_remaining_ms = max(0.0, _timeout_at[kernel_id] - time.monotonic()) * 1000.0

    return GetKernelStateResponse(time_remaining_ms=time_remaining_ms)


async def _create_kernel(timeout: float):
    assert _kernel_queue is not None, "Queue should be initialized once health checks pass."
    kernel_id = await _kernel_queue.get()
    _timeout[kernel_id] = timeout
    _timeout_at[kernel_id] = time.monotonic() + timeout
    return kernel_id


@app.post("/kernel")
async def create_kernel(create_kernel_request: CreateKernelRequest):
    logger.info(f"Create kernel request. {create_kernel_request}")
    timeout = create_kernel_request.timeout
    kernel_id = await _create_kernel(timeout=timeout)
    logger.info(f"Got kernel id from queue. {create_kernel_request}")
    return CreateKernelResponse(kernel_id=kernel_id)


@app.websocket("/channel")
async def channel(websocket: WebSocket):
    async def send_callback_request(call: MethodCall):
        await websocket.send_text(call.json())

    logger.info("Setting global forward function.")
    global _SEND_CALLBACK_REQUEST
    _SEND_CALLBACK_REQUEST = send_callback_request

    await websocket.accept(headers=[(_SELF_IDENTIFY_HEADER_KEY_BYTES, _SELF_IDENTIFY_BYTES)])

    clients: Dict[str, AsyncKernelClient] = {}
                                      
                                                               
                                                                             
                                                           
                                                                                
                                         
     
                                                                  
    recv_from_api_server = asyncio.create_task(websocket.receive_text())
    recv_from_jupyter = None
    try:
        while True:
            logger.info(f"Waiting for message. {recv_from_api_server}, {recv_from_jupyter}")
            done, _ = await asyncio.wait(
                [task for task in [recv_from_api_server, recv_from_jupyter] if task is not None],
                return_when=asyncio.FIRST_COMPLETED,
            )
            logger.info(f"Got messages for {done}.")
            if recv_from_api_server in done:
                done_future = recv_from_api_server
                recv_from_api_server = asyncio.create_task(websocket.receive_text())
                request = parse_obj_as(UserMachineRequest, json.loads(done_future.result()))
                logger.info(f"Received message from API server. {request}")
                if isinstance(request, RegisterActivityRequest):
                    logger.info(f"Registering activity. {request}")
                    _timeout_at[request.kernel_id] = time.monotonic() + _timeout[request.kernel_id]
                elif isinstance(request, MethodCallReturnValue):
                    _respond_to_callback_from_kernel(request)
                elif isinstance(request, MethodCall):

                    async def run(request: UserMachineRequest):
                        try:
                            object_reference = request.object_reference
                            if object_reference.type == "multi_kernel_manager":
                                referenced_object = _MULTI_KERNEL_MANAGER
                            elif object_reference.type == "kernel_manager":
                                referenced_object = _MULTI_KERNEL_MANAGER.get_kernel(
                                    object_reference.id
                                )
                            elif object_reference.type == "client":
                                referenced_object = clients[object_reference.id]
                            else:
                                raise Exception(
                                    f"Unknown object reference type: {object_reference.type}"
                                )
                            qualified_method = f"{object_reference.type}.{request.method}"
                            logger.info(
                                f"Method call: {qualified_method} args: {request.args} kwargs: {request.kwargs}"
                            )
                            value = getattr(referenced_object, request.method)(
                                *request.args, **request.kwargs
                            )
                            if inspect.isawaitable(value):
                                value = await value
                            return (request.request_id, value, None)
                        except Exception as e:
                            return (request.request_id, None, e)

                    assert recv_from_jupyter is None
                    recv_from_jupyter = asyncio.create_task(run(request))
            if recv_from_jupyter in done:
                done_future = recv_from_jupyter
                recv_from_jupyter = None
                request_id, value, e = done_future.result()
                if e is None:
                    logger.info(f"Received result from Jupyter. {value}")
                    if isinstance(value, AsyncKernelClient):
                        client_id = str(uuid.uuid4())
                        clients[client_id] = value
                        result = MethodCallObjectReferenceReturnValue(
                            request_id=request_id,
                            object_reference=ObjectReference(type="client", id=client_id),
                        )
                    elif isinstance(value, AsyncKernelManager):
                        result = MethodCallObjectReferenceReturnValue(
                            request_id=request_id,
                            object_reference=ObjectReference(
                                type="kernel_manager", id=value.kernel_id
                            ),
                        )
                    else:
                        result = MethodCallReturnValue(request_id=request_id, value=value)
                else:
                    logger.info(f"Received result from Jupyter. Exception: {value}")
                    result = MethodCallException(
                        request_id=request_id,
                        type=type(e).__name__,
                        value=str(e),
                        traceback=traceback.format_tb(e.__traceback__),
                    )
                                                                                         
                    del e

                                           
                message = result.json()
                logger.info(f"Sending response: {type(result)}, {len(message)}")
                if len(message) > _MAX_JUPYTER_MESSAGE_SIZE:
                    logger.error(f"Response too large: {len(message)}")
                    e = UserMachineResponseTooLarge(
                        f"Message of type {type(result)} is too large: {len(message)}"
                    )
                    message = MethodCallException(
                        request_id=result.request_id,
                        type=type(e).__name__,
                        value=str(e),
                        traceback=traceback.format_tb(e.__traceback__),
                    ).json()

                await websocket.send_text(message)
                logger.info("Response sent.")
    except WebSocketDisconnect as e:
        if e.code == 1000:
            logger.info("Client WebSocket connection closed normally")
        else:
            logger.exception(f"Client WebSocket connection closed with code {e.code}")
        for client in clients.values():
            client.stop_channels()
        logger.info("All clients stopped.")
        return


@app.middleware("http")
async def add_self_identify_header(request: Request, call_next):
                                                                                                  
    if _is_from_localhost(request):
                                                                                                  
        return await call_next(request)
    try:
        response = await call_next(request)
    except Exception:
                                                                                     
                                                                                      
                                                                                 
                                    
        traceback.print_exc()
        return PlainTextResponse(
            "Internal server error",
            status_code=500,
            headers={_SELF_IDENTIFY_HEADER_KEY: _SELF_IDENTIFY_STR},
        )
    response.headers[_SELF_IDENTIFY_HEADER_KEY] = _SELF_IDENTIFY_STR
    return response
