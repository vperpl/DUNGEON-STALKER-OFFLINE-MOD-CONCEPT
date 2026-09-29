"""Loopback-only HTTP stub for Dungeon Stalkers.

The game's BigAccount/maingate client is pointed at
    http://127.0.0.1:8080/maingate   (see Engine.ini [BigAccount])
and it also probes port 80.

This logs every request line so we can read the API contract for free,
then answers with an empty 200 so the client fails fast instead of hanging.

    python stub.py [port ...]     default: 80 8080
"""

import socket
import sys
import threading
import time

LOG = "stub.log"


def log(msg):
    line = "%s %s" % (time.strftime("%H:%M:%S"), msg)
    print(line)
    with open(LOG, "a", encoding="utf-8", errors="replace") as f:
        f.write(line + "\n")


def handle(conn, addr, port):
    try:
        conn.settimeout(5.0)
        data = b""
        while b"\r\n\r\n" not in data and len(data) < 65536:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
        head = data.split(b"\r\n\r\n", 1)[0].decode("utf-8", "replace")
        if head:
            log("port %d <- %s" % (port, head.replace("\r\n", " | ")))
        body = b"{}"
        conn.sendall(
            b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
            b"Content-Length: %d\r\nConnection: close\r\n\r\n%s"
            % (len(body), body)
        )
    except Exception as e:
        log("port %d error: %r" % (port, e))
    finally:
        try:
            conn.close()
        except Exception:
            pass


def serve(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", port))
    s.listen(16)
    log("listening 127.0.0.1:%d (loopback only)" % port)
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle, args=(conn, addr, port), daemon=True).start()


def main():
    ports = [int(p) for p in sys.argv[1:]] or [80, 8080]
    for p in ports:
        try:
            threading.Thread(target=serve, args=(p,), daemon=True).start()
        except OSError as e:
            log("cannot bind %d: %r" % (p, e))
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
