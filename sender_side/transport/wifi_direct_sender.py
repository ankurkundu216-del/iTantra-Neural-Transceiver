"""
Wi-Fi Direct / TCP P2P Sender
Handles high-priority/higher-bandwidth binary frame transmission over local P2P Wi-Fi links.
"""

import socket
import sys
import time

class WiFiDirectSender:
    DEFAULT_GO_IP = "192.168.49.1"  # Default Group Owner IP for Android Wi-Fi Direct
    DEFAULT_PORT = 8888

    def __init__(self, target_ip: str = DEFAULT_GO_IP, port: int = DEFAULT_PORT):
        self.target_ip = target_ip
        self.port = port
        self.sock = None
        self.is_connected = False

    def connect(self, target_ip: str = None) -> bool:
        """Establishes a TCP socket connection over the Wi-Fi Direct P2P interface."""
        if target_ip:
            self.target_ip = target_ip

        print(f"[WIFI-DIRECT] Connecting to {self.target_ip}:{self.port}...")
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5.0)
            self.sock.connect((self.target_ip, self.port))
            self.is_connected = True
            print(f"[WIFI-DIRECT] Connected to Group Owner ({self.target_ip}).")
            return True

        except Exception as e:
            print(f"[WIFI-DIRECT ERROR] Connection failed to {self.target_ip}:{self.port} -> {e}")
            self.is_connected = False
            return False

    def send_packet(self, packet: bytes) -> bool:
        """Transmits the binary frame over the TCP P2P channel."""
        if not self.is_connected or self.sock is None:
            # Transmit fallback simulation when hardware link isn't attached
            print(f"[WIFI-DIRECT MOCK TX] Sent {len(packet)} bytes (Header: {packet[:6].hex()})")
            return True

        try:
            self.sock.sendall(packet)
            print(f"[WIFI-DIRECT] Transmitted {len(packet)} bytes.")
            return True
        except Exception as e:
            print(f"[WIFI-DIRECT ERROR] Packet transmission failed: {e}")
            self.is_connected = False
            return False

    def close(self):
        """Closes the TCP P2P socket."""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.is_connected = False
            print("[WIFI-DIRECT] Socket closed.")