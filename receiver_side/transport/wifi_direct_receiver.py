"""
Wi-Fi Direct High-Bandwidth Socket Receiver
Acts as TCP socket server accepting real-time binary audio/text frames over P2P Wi-Fi.
"""

import socket
import struct
import threading
import time
from typing import Callable, Optional

MAGIC_BYTE = 0x49  # 'I' for iTantra


class WiFiDirectReceiver:
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 9999,
        on_frame_received: Optional[Callable[[bytes], None]] = None
    ):
        """
        Initializes the Wi-Fi Direct TCP Server Listener.
        
        Args:
            host: Listening interface IP (default "0.0.0.0").
            port: Network port (default 9999).
            on_frame_received: Callback for received binary payload frames.
        """
        self.host = host
        self.port = port
        self.on_frame_received = on_frame_received
        self.server_sock = None
        self.is_running = False
        self._listen_thread = None

    def _recv_exact(self, conn: socket.socket, length: int) -> Optional[bytes]:
        """Guarantees complete byte assembly over TCP stream fragments."""
        buf = bytearray()
        while len(buf) < length:
            try:
                chunk = conn.recv(length - len(buf))
                if not chunk:
                    return None
                buf.extend(chunk)
            except (socket.timeout, ConnectionResetError):
                return None
        return bytes(buf)

    def _handle_client(self, conn: socket.socket, addr: tuple) -> None:
        print(f"📶 [Wi-Fi Direct Receiver] Sender connected from {addr[0]}:{addr[1]}")
        conn.settimeout(8.0)

        try:
            while self.is_running:
                # 1. Inspect 6-byte header frame
                header_bytes = self._recv_exact(conn, 6)
                if not header_bytes:
                    break

                magic, priority, lang, payload_len, checksum = struct.unpack('>BBBHB', header_bytes)

                if magic != MAGIC_BYTE:
                    print(f"⚠️ [Wi-Fi Direct] Corrupted Magic Byte ({hex(magic)}). Resyncing stream...")
                    continue

                # 2. Ingest payload
                payload_bytes = self._recv_exact(conn, payload_len)
                if not payload_bytes:
                    break

                full_frame = header_bytes + payload_bytes

                # 3. Fire receiver pipeline callback
                if self.on_frame_received:
                    self.on_frame_received(full_frame)

        except Exception as e:
            print(f"⚠️ [Wi-Fi Direct Receiver] Socket stream error: {e}")
        finally:
            conn.close()
            print(f"📶 [Wi-Fi Direct Receiver] Sender disconnected: {addr[0]}:{addr[1]}")

    def start(self) -> None:
        """Spawns background TCP server listener thread."""
        self.is_running = True
        self._listen_thread = threading.Thread(target=self._server_loop, daemon=True)
        self._listen_thread.start()

    def _server_loop(self) -> None:
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind((self.host, self.port))
            self.server_sock.listen(5)
            print(f"📶 [Wi-Fi Direct Receiver] TCP Listening on {self.host}:{self.port}...")

            while self.is_running:
                try:
                    conn, addr = self.server_sock.accept()
                    client_thread = threading.Thread(
                        target=self._handle_client, args=(conn, addr), daemon=True
                    )
                    client_thread.start()
                except OSError:
                    break  # Server closed

        except Exception as e:
            print(f"❌ [Wi-Fi Direct Receiver] Failed to bind TCP server: {e}")

    def stop(self) -> None:
        """Shuts down receiver server."""
        self.is_running = False
        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
        print("📶 [Wi-Fi Direct Receiver] Server stopped.")


if __name__ == "__main__":
    def frame_handler(frame: bytes):
        print(f"[Wi-Fi Direct Test Callback] Stream frame received ({len(frame)} bytes)")

    wf_receiver = WiFiDirectReceiver(port=9999, on_frame_received=frame_handler)
    wf_receiver.start()
    time.sleep(2)
    wf_receiver.stop()