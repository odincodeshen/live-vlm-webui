import ssl
import asyncio
import json
import os
import subprocess
import websockets

WS_URL = os.environ.get("VLM_WS_URL", "ws://127.0.0.1:8090/ws")
ROS_DOMAIN_ID = os.environ.get("ROS_DOMAIN_ID", "0")
RMW = os.environ.get("RMW_IMPLEMENTATION", "rmw_fastrtps_cpp")

def ros2_call(service: str, srv_type: str, payload: str, timeout_s: int = 3) -> str:
    cmd = [
        "docker", "run", "--rm", "--net=host",
        "-e", f"ROS_DOMAIN_ID={ROS_DOMAIN_ID}",
        "-e", f"RMW_IMPLEMENTATION={RMW}",
        "ros:humble", "bash", "-lc",
        f"source /opt/ros/humble/setup.bash && timeout {timeout_s} "
        f"ros2 service call {service} {srv_type} '{payload}'"
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return (p.stdout + "\n" + p.stderr).strip()

def do_trot():
    print("[bridge] -> TROT")
    print(ros2_call("/puppy_control/set_running", "std_srvs/srv/SetBool", "{data: true}"))
    print(ros2_call("/puppy_control/set_mark_time", "std_srvs/srv/SetBool", "{data: true}"))

def do_stop():
    print("[bridge] -> STOP")
    print(ros2_call("/puppy_control/set_mark_time", "std_srvs/srv/SetBool", "{data: false}"))
    print(ros2_call("/puppy_control/set_running", "std_srvs/srv/SetBool", "{data: false}"))

async def main():
    print(f"[bridge] WS_URL={WS_URL}")
    print(f"[bridge] ROS_DOMAIN_ID={ROS_DOMAIN_ID} RMW={RMW}")
    last = None  # prevent spamming same command continuously

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    async with websockets.connect(WS_URL, ssl=ssl_ctx) as ws:
        async for msg in ws:
###            print("[ws]", msg[:200])
            # live-vlm-webui websocket messages are JSON; we look for type=vlm_response and read text
            try:
                data = json.loads(msg)
            except Exception:
                continue
            if data.get("type") != "vlm_response":
                continue

            text = (data.get("text") or "").strip().upper()

            # Extract intent word robustly
            intent = "STOP"
            if "TROT" in text:
                intent = "TROT"
            elif "STOP" in text:
                intent = "STOP"

            # Default STOP for safety
            if intent == last:
                continue
            last = intent

            if intent == "TROT":
                do_trot()
            else:
                do_stop()

if __name__ == "__main__":
    asyncio.run(main())
