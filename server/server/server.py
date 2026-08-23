#!/usr/bin/env python3
import asyncio
import json
import os
import uuid

from aiohttp import web, WSMsgType

PORT = 8000
BASE_DIR = os.path.join(os.path.dirname(__file__), "public")

# request_id -> {"lines": [...], "done": bool, "returncode": int|None, "subscribers": set[WebSocketResponse]}
EXECUTIONS: dict[str, dict] = {}


async def _broadcast(execution: dict, message: str):
    dead = []
    for sub in execution["subscribers"]:
        try:
            await sub.send_str(message)
        except ConnectionResetError:
            dead.append(sub)
    for sub in dead:
        execution["subscribers"].discard(sub)


async def _run_execution(request_id: str, query: str):
    execution = EXECUTIONS[request_id]
    cmd = ["python3", "rag6.py", "--model", "gpt-oss:20b", "--query", query, "--min", "30"]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=os.path.join(os.path.dirname(__file__), "../../"),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    async for raw_line in proc.stdout:
        line = raw_line.decode("utf-8", errors="replace")
        execution["lines"].append(line)
        await _broadcast(execution, line)

    stderr = await proc.stderr.read()
    if stderr:
        print(stderr.decode("utf-8", errors="replace"))

    await proc.wait()
    execution["done"] = True
    execution["returncode"] = proc.returncode
    await _broadcast(execution, json.dumps({"done": True, "returncode": proc.returncode}))

    # Keep finished executions around briefly so late subscribers can still fetch the buffer.
    async def _expire():
        await asyncio.sleep(300)
        EXECUTIONS.pop(request_id, None)
    asyncio.create_task(_expire())


async def websocket_execute(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse(heartbeat=30)
    await ws.prepare(request)

    async for msg in ws:
        if msg.type != WSMsgType.TEXT:
            continue
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError as e:
            await ws.send_json({"error": f"Invalid JSON: {e}"})
            continue

        if data.get("subscribe"):
            request_id = data["subscribe"]
            execution = EXECUTIONS.get(request_id)
            if execution is None:
                await ws.send_json({"error": "Unknown or expired request_id", "request_id": request_id})
                continue
            for line in execution["lines"]:
                await ws.send_str(line)
            if execution["done"]:
                await ws.send_json({"done": True, "returncode": execution["returncode"]})
            else:
                execution["subscribers"].add(ws)
            continue

        query = data.get("query", "")
        request_id = uuid.uuid4().hex
        EXECUTIONS[request_id] = {"lines": [], "done": False, "returncode": None, "subscribers": {ws}}
        await ws.send_json({"request_id": request_id})
        asyncio.create_task(_run_execution(request_id, query))

    return ws


def main():
    os.makedirs(BASE_DIR, exist_ok=True)
    app = web.Application()
    app.router.add_get("/ws/execute", websocket_execute)
    app.router.add_static("/", BASE_DIR, show_index=True)

    print(f"Serving HTTP + WS on port {PORT} (http://localhost:{PORT}/) ...")
    web.run_app(app, port=PORT)


if __name__ == "__main__":
    main()