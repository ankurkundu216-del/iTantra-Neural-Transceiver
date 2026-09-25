"""
Bluetooth RFCOMM / SPP Socket Receiver Server
Listens for inbound sender connections over Bluetooth and streams binary frames.
"""

import socket
import struct
import threading
import time
from typing import Callable, Optional

MAGIC_BYTE = 0x49  # 'I' for iTantra


class BluetoothReceiver:
    def __init__(
        self,
        port: int = 1,
        host: str = "",
        on_frame_received: Optional[Callable[[bytes], None]] = None
    ):
        """
        Initializes the RFCOMM Bluetooth listener.
        
        Args:
            port: RFCOMM channel port (default: 1).
            host: Bind MAC address (empty string for local default adapter).
            on_frame_received: Callback function invoked with raw frame bytes.
        """
        self.port = port
        self.host = host
        self.on_frame_received = on_frame_received
        self.server_sock = None
        self.is_running = False
        self._listen_thread = None

    def _recv_exact(self, conn: socket.socket, length: int) -> Optional[bytes]:
        """Ensures exact N bytes are read from the streaming socket buffer."""
        buf = bytearray()
        while len(buf) < length:
            try:
                chunk = conn.recv(length - len(buf))
                if not chunk:
                    return None  # Socket disconnected
                buf.extend(chunk)
            except (socket.timeout, ConnectionResetError):
                return None
        return bytes(buf)

    def _client_handler(self, client_sock: socket.socket, client_info: tuple) -> None:
        print(f"📡 [BT Receiver] Peer connected: {client_info}")
        client_sock.settimeout(10.0)

        try:
            while self.is_running:
                # 1. Read 6-byte header
                header_bytes = self._recv_exact(client_sock, 6)
                if not header_bytes:
                    break

                magic, priority, lang, payload_len, checksum = struct.unpack('>BBBHB', header_bytes)

                # Frame sync guard
                if magic != MAGIC_BYTE:
                    print(f"⚠️ [BT Receiver] Out-of-sync byte detected: {hex(magic)}. Dropping byte.")
                    continue

                # 2. Read exact payload length
                payload_bytes = self._recv_exact(client_sock, payload_len)
                if not payload_bytes:
                    break

                full_frame = header_bytes + payload_bytes

                # 3. Dispatch full frame to receiver pipeline callback
                if self.on_frame_received:
                    self.on_frame_received(full_frame)

        except Exception as e:
            print(f"⚠️ [BT Receiver] Client stream exception: {e}")
        finally:
            client_sock.close()
            print(f"📡 [BT Receiver] Peer disconnected: {client_info}")

    def start(self) -> None:
        """Starts the Bluetooth listener server thread."""
        self.is_running = True
        self._listen_thread = threading.Thread(target=self._server_loop, daemon=True)
        self._listen_thread.start()

    def _server_loop(self) -> None:
        try:
            # Check for native Python Bluetooth RFCOMM socket support
            if hasattr(socket, "AF_BLUETOOTH"):
                self.server_sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
                self.server_sock.bind((self.host, self.port))
            else:
                # Fallback to standard TCP socket for development/simulations
                print("[BT Receiver] Native AF_BLUETOOTH unavailable. Running TCP simulation fallback on port 8889.")
                self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_sock.bind(("0.0.0.0", 8889))

            self.server_sock.listen(1)
            print(f"📡 [BT Receiver] Server listening for incoming transmissions on channel/port {self.port}...")

            while self.is_running:
                try:
                    client_sock, client_info = self.server_sock.accept()
                    client_thread = threading.Thread(
                        target=self._client_handler, args=(client_sock, client_info), daemon=True
                    )
                    client_thread.start()
                except OSError:
                    break  # Server socket closed

        except Exception as e:
            print(f"❌ [BT Receiver] Server initialization failed: {e}")

    def stop(self) -> None:
        """Stops the server socket and closes connections."""
        self.is_running = False
        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
        print("📡 [BT Receiver] Stopped listening.")


if __name__ == "__main__":
    def print_callback(raw_frame: bytes):
        print(f"[BT Receiver Test Callback] Received raw binary frame ({len(raw_frame)} bytes)")

    receiver = BluetoothReceiver(on_frame_received=print_callback)
    receiver.start()
    time.sleep(2)
    receiver.stop()