import socket


def _can_bind(host: str, port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


def pick_free_port(preferred: int = 5432, max_tries: int = 200) -> int:
    for port in range(preferred, preferred + max_tries):
        # Docker publishes on 0.0.0.0, so test that explicitly.
        if _can_bind("0.0.0.0", port) and _can_bind("127.0.0.1", port):
            return port
    raise RuntimeError(f"No free port found in {preferred}-{preferred + max_tries - 1}")
