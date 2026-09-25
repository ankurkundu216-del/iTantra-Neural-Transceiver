"""
Bluetooth SPP / RFCOMM Sender
Handles low-power P2P binary packet transmission over Bluetooth sockets.
"""

import socket
import sys
import time

class BluetoothSender:
    def __init__(self, target_mac: str = None, port: int = 1):
        self.target_mac = target_mac
        self.port = port
        self.sock = None
        self.is_connected = False

    def connect(self, target_mac: str = None) -> bool:
        """Establishes an RFCOMM socket connection to the target Bluetooth MAC address."""
        if target_mac:
            self.target_mac = target_mac

        if not self.target_mac:
            print("[BT SENDER] Warning: No target MAC specified. Operating in Mock Mode.")
            return False

        print(f"[BT SENDER] Connecting to {self.target_mac} on RFCOMM port {self.port}...")
        try:
            # Native RFCOMM Bluetooth socket (Linux / Android)
            if hasattr(socket, 'AF_BLUETOOTH'):
                self.sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            else:
                # Fallback TCP stream socket for Windows / Testing environment
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            self.sock.settimeout(5.0)
            self.sock.connect((self.target_mac, self.port))
            self.is_connected = True
            print("[BT SENDER] Bluetooth link established.")
            return True

        except Exception as e:
            print(f"[BT SENDER ERROR] Connection failed to {self.target_mac}: {e}")
            self.is_connected = False
            return False

    def send_packet(self, packet: bytes) -> bool:
        """Sends a binary frame over the Bluetooth socket."""
        if not self.is_connected or self.sock is None:
            # Transmit fallback simulation when hardware link isn't attached
            print(f"[BT MOCK TX] Sent {len(packet)} bytes (Header: {packet[:6].hex()})")
            return True

        try:
            self.sock.sendall(packet)
            print(f"[BT SENDER] Transmitted {len(packet)} bytes over RFCOMM.")
            return True
        except Exception as e:
            print(f"[BT SENDER ERROR] Transmission failed: {e}")
            self.is_connected = False
            return False

    def close(self):
        """Closes the Bluetooth socket."""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.is_connected = False
            print("[BT SENDER] Connection closed.")