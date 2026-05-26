import socket
import struct
import sys
import threading
import time
import os

# Standard RTSP Ports to scan
RTSP_PORTS = [554, 8554]
TIMEOUT = 0.5  # Seconds to wait for port check response
THREAD_LIMIT = 50  # Max concurrent scanning threads

class CameraDiscovery:
    def __init__(self):
        self.found_devices = []
        self.lock = threading.Lock()

    def get_local_ip_and_subnet(self):
        """Detect the local machine's IP address and generate the target subnet."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Connect to a dummy public IP to trigger routing and get the local IP
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        except Exception:
            local_ip = "127.0.0.1"
        finally:
            s.close()

        if local_ip == "127.0.0.1":
            return None, None

        # Split IP to get the subnet prefix (e.g. 192.168.1)
        parts = local_ip.split(".")
        subnet = f"{parts[0]}.{parts[1]}.{parts[2]}."
        return local_ip, subnet

    def check_rtsp_port(self, ip, port):
        """Attempt to open a TCP socket on an RTSP port to see if a camera is streaming."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        try:
            result = sock.connect_ex((ip, port))
            if result == 0:
                with self.lock:
                    self.found_devices.append({"ip": ip, "port": port})
                    print(f"📡 Discovered TCP port {port} OPEN at device: {ip}")
        except Exception:
            pass
        finally:
            sock.close()

    def scan_subnet(self, subnet):
        """Scan the entire subnet range (.1 to .254) for open RTSP ports using threads."""
        threads = []
        print(f"🔍 Starting active RTSP network scan on subnet {subnet}0/24...")
        
        for i in range(1, 255):
            ip = f"{subnet}{i}"
            for port in RTSP_PORTS:
                # Create a thread for each check to keep scanning extremely fast (under 3 seconds total)
                t = threading.Thread(target=self.check_rtsp_port, args=(ip, port))
                threads.append(t)
                t.start()

                # Cap active threads to avoid resource exhaustion
                if len(threads) >= THREAD_LIMIT:
                    for active_thread in threads:
                        active_thread.join()
                    threads = []

        # Join remaining threads
        for t in threads:
            t.join()

    def discover_onvif_multicast(self):
        """
        Broadcast WS-Discovery UDP multicast probe. 
        Most IP cameras will instantly broadcast their IP and configuration in response.
        """
        print("📨 Broadcasting ONVIF WS-Discovery probe to local network...")
        ws_discovery_probe = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<Envelope xmlns:dn="http://www.onvif.org/ver10/network/wsdl" xmlns="http://www.w3.org/2003/05/soap-envelope">'
            '<Header>'
            '<wsa:MessageID xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">uuid:949ef9e2-e19c-4cd1-9c3f-84610190111a</wsa:MessageID>'
            '<wsa:To xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">urn:schemas-xmlsoap-org:ws:2004:08:discovery</wsa:To>'
            '<wsa:Action xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</wsa:Action>'
            '</Header>'
            '<Body>'
            '<Probe xmlns="http://schemas.xmlsoap.org/ws/2005/04/discovery">'
            '<Types>dn:NetworkVideoTransmitter</Types>'
            '</Probe>'
            '</Body>'
            '</Envelope>'
        )

        multicast_address = "239.255.255.250"
        port = 3702

        # Create socket for UDP Multicast
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.settimeout(1.5)
        # Set TTL to 2 to stay on the local subnet
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

        try:
            sock.sendto(ws_discovery_probe.encode("utf-8"), (multicast_address, port))
            
            # Listen for responses
            while True:
                data, addr = sock.recvfrom(65507)
                ip = addr[0]
                print(f"🎥 ONVIF Device responded at IP: {ip}")
                with self.lock:
                    if not any(d["ip"] == ip for d in self.found_devices):
                        self.found_devices.append({"ip": ip, "port": 554, "onvif": True})
        except socket.timeout:
            pass
        except Exception as e:
            print(f"ONVIF discovery error: {e}")
        finally:
            sock.close()

    def test_camera_stream(self, ip, port):
        """Construct the RTSP URL with the user's credentials/path and validate it live using OpenCV."""
        ip = ip.strip()
        rtsp_url = f"rtsp://admin:20241030-1@{ip}:{port}/live/ch00_0"
        print(f"🧪 Testing RTSP stream connection: {rtsp_url}...")
        
        try:
            import cv2
            cap = cv2.VideoCapture(rtsp_url)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                if ret:
                    return True, rtsp_url
        except Exception as e:
            print(f"  [DEBUG] OpenCV verification failed for {rtsp_url}: {e}")
            
        # Try a standard fallback route
        fallback_url = f"rtsp://admin:20241030-1@{ip}:{port}/h264"
        print(f"🧪 Trying fallback RTSP stream connection: {fallback_url}...")
        try:
            import cv2
            cap = cv2.VideoCapture(fallback_url)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                if ret:
                    return True, fallback_url
        except Exception:
            pass
            
        return False, None


def main():
    print("==================================================")
    print("    IP Camera Automated Verification & Sync       ")
    print("==================================================\n")
    
    discovery = CameraDiscovery()
    local_ip, subnet = discovery.get_local_ip_and_subnet()

    if not subnet:
        print("❌ Could not determine local IP. Make sure you are connected to Wi-Fi or Ethernet.")
        sys.exit(1)

    print(f"💻 Your Laptop IP: {local_ip}")
    print(f"🌐 Target Subnet:  {subnet}x\n")

    # 1. Run ONVIF multicast (broad, instant capture)
    discovery.discover_onvif_multicast()

    # 2. Run Port Scan (failsafe, catches any streaming server)
    discovery.scan_subnet(subnet)

    print("\n==================================================")
    print("                 SCAN SUMMARY                     ")
    print("==================================================")
    
    working_camera = None
    
    if discovery.found_devices:
        print(f"Success: Found {len(discovery.found_devices)} potential device(s) on subnet.")
        print("Starting automatic stream validation using your credentials...\n")
        
        checked_ips = set()
        for dev in discovery.found_devices:
            ip = dev["ip"]
            port = dev["port"]
            if ip in checked_ips:
                continue
            checked_ips.add(ip)
            
            success, validated_url = discovery.test_camera_stream(ip, port)
            if success:
                working_camera = {
                    "ip": ip,
                    "port": port,
                    "url": validated_url
                }
                break  # Find the first functional camera feed
                
        if working_camera:
            w_ip = working_camera["ip"]
            w_url = working_camera["url"]
            
            # Giant colored success banner for Viva!
            print("\n" + "=" * 62)
            print("\033[92m\033[1m🎉 SUCCESS: LIVE CAMERA AUTOMATICALLY FOUND & DECODED! 🎉\033[0m")
            print("=" * 62)
            print(f"🎥 Active Camera IP:  \033[94m{w_ip}\033[0m")
            print(f"🔗 Video Access URL:  \033[92m{w_url}\033[0m")
            print("=" * 62)
            
            # Automatically update Supabase database!
            print("\n📬 Syncing live connection with your Camus Database...")
            synced = False
            
            # Method A: Local API PUT Update
            try:
                import requests
                api_url = "http://localhost:8000/api/sources"
                res = requests.get(api_url, timeout=2)
                if res.status_code == 200:
                    sources = res.json()
                    stream_sources = [s for s in sources if s.get("mode") == "stream"]
                    if stream_sources:
                        target = stream_sources[0]
                        payload = {
                            "title": target.get("title"),
                            "description": target.get("description"),
                            "mode": "stream",
                            "streamUrl": w_url
                        }
                        put_res = requests.put(f"{api_url}/{target.get('id')}", json=payload, timeout=3)
                        if put_res.status_code == 200:
                            print(f"\033[92m[AUTO-SYNC] Successfully synced via Camus API! Camera '{target.get('title')}' is now live.\033[0m")
                            synced = True
            except Exception:
                pass
                
            # Method B: Direct Supabase Repository Update Fallback
            if not synced:
                try:
                    # Append backend dir to path just in case
                    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                    from source_repository import SourceRepository
                    from dotenv import load_dotenv
                    load_dotenv()
                    
                    repo = SourceRepository()
                    sources = repo.list_sources()
                    stream_sources = [s for s in sources if s.get("mode") == "stream"]
                    if stream_sources:
                        target = stream_sources[0]
                        repo.update_source(
                            source_id=target.get("id"),
                            title=target.get("title"),
                            description=target.get("description"),
                            mode="stream",
                            stream_url=w_url
                        )
                        print(f"\033[92m[AUTO-SYNC] Successfully updated '{target.get('title')}' directly in Supabase!\033[0m")
                        synced = True
                except Exception as e:
                    print(f"\033[91m[WARN] Database update skipped/failed: {e}\033[0m")
            
            if synced:
                print(f"\n\033[1;92m🚀 VIVA READY! Your frontend React dashboard is now connected to the live stream.\033[0m")
        else:
            print("\n❌ Validated scan completed: Found devices, but none decoded successfully.")
            print("Please ensure the camera credentials (admin / 20241030-1) are correct.")
    else:
        print("\n❌ No active camera devices detected on the network.")
        print("Please check that both your laptop and camera are connected to the same subnet.")
    print("==================================================\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
