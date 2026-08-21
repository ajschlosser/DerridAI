#!/usr/bin/env python3
import http.server
import socketserver
import os
import json
import subprocess
import http

PORT = 8000
BASE_DIR = os.path.join(os.path.dirname(__file__), "public")

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_POST(self):
        """Handle POST requests for script execution.

        Expected JSON body format::

            {
                "script": "rag6.py",
                "args": ["--model", "gpt-oss:20b", "--query", "..."],
                "cwd": "/home/aaron/src/derrida"  // optional
            }

        The server will run the script using ``subprocess.run`` and
        capture stdout and stderr.  The output is returned as a JSON
        object containing ``stdout``, ``stderr`` and ``returncode``.
        """
        if self.path != "/api/execute":
            self.send_error(http.HTTPStatus.NOT_FOUND, "Endpoint not found")
            return

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self.send_error(http.HTTPStatus.BAD_REQUEST, "Empty request body")
            return
        try:
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))
        except Exception as e:
            self.send_error(http.HTTPStatus.BAD_REQUEST, f"Invalid JSON: {e}")
            return
        
        # Build command
        cmd = ["python3", "rag6.py", "--model", "gpt-oss:20b", "--query", data.get("query", ""), "--min", "15"]
        try:
            # Use Popen to stream output
            proc = subprocess.Popen(
                cmd,
                cwd='../../',
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            # Prepare chunked transfer encoding response
            self.send_response(http.HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()

            def _write_chunk(data: str):
                encoded = data.encode("utf-8")
                chunk = f"{len(encoded):X}\r\n".encode("utf-8") + encoded + b"\r\n"
                self.wfile.write(chunk)
                self.wfile.flush()

            # Stream stdout
            output_ready = False
            for line in proc.stdout:
                if output_ready:
                    _write_chunk(line)
                if "Loading existing vector store" in line:
                    _write_chunk("Gathering Derridean materials...")
                if "Raw keywords response" in line:
                    _write_chunk(" Pondering aporias...")
                if "points to the correct page." in line:
                    _write_chunk(" Asking Jackie for a response...")
                if "LLM finished generating response" in line:
                    _write_chunk(" Deferring meaning (this may take a minute)...")
                if "--- Answer from" in line:
                    _write_chunk("Received answer...!")
                    output_ready = True

            # Stream stderr with a prefix
            for line in proc.stderr:
                print(line, end='')
                #_write_chunk(f"[ERR] {line}")

            # Final zero-length chunk to signal end
            _write_chunk("")

            proc.wait()
        except subprocess.TimeoutExpired:
            self.send_error(http.HTTPStatus.REQUEST_TIMEOUT, "Script timed out")
        except Exception as e:
            self.send_error(http.HTTPStatus.INTERNAL_SERVER_ERROR, str(e))

if __name__ == "__main__":
    os.makedirs(BASE_DIR, exist_ok=True)
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving HTTP on port {PORT} (http://localhost:{PORT}/) ...")
        httpd.serve_forever()
