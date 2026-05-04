import asyncio
import json
import os
import ssl
import subprocess
import websockets

WS_URL = os.environ.get("VLM_WS_URL", "wss://127.0.0.1:8090/ws")
ROS_DOMAIN_ID = os.environ.get("ROS_DOMAIN_ID", "0")
RMW = os.environ.get("RMW_IMPLEMENTATION", "rmw_fastrtps_cpp")

def ros2_call(service: str, srv_type: str, payload: str, timeout_s: int = 3) -> int:
    """
    Call ROS2 service via dockerized CLI.
    Returns process return code. Does NOT print noisy 'response:' output.
    """
    cmd = [
        "docker", "run", "--rm", "--net=host",
        "-e", f"ROS_DOMAIN_ID={ROS_DOMAIN_ID}",
        "-e", f"RMW_IMPLEMENTATION={RMW}",
        "ros:humble", "bash", "-lc",
        f"source /opt/ros/humble/setup.bash && timeout {timeout_s} "
        f"ros2 service call {service} {srv_type} '{payload}'"
        f" >/dev/null 2>&1"
    ]
    p = subprocess.run(cmd)
    return p.returncode

def do_trot():
    print("[bridge] TROT")
    ros2_call("/puppy_control/set_running", "std_srvs/srv/SetBool", "{data: true}")
    ros2_call("/puppy_control/set_mark_time", "std_srvs/srv/SetBool", "{data: true}")

def do_stop():
    print("[bridge] STOP")
    ros2_call("/puppy_control/set_mark_time", "std_srvs/srv/SetBool", "{data: false}")
    ros2_call("/puppy_control/set_running", "std_srvs/srv/SetBool", "{data: false}")

async def main():
    # TLS: accept self-signed certs
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    print(f"[bridge] WS_URL={WS_URL}")
    print(f"[bridge] ROS_DOMAIN_ID={ROS_DOMAIN_ID} RMW={RMW}")
    print("[bridge] Press Ctrl+C to exit cleanly.")

    last = None

    try:
        async with websockets.connect(WS_URL, ssl=ssl_ctx) as ws:
            async for msg in ws:
                try:
                    data = json.loads(msg)
                except Exception:
                    continue
                if data.get("type") != "vlm_response":
                    continue

                text = (data.get("text") or "").strip().upper()

                # Safety default STOP
                intent = "STOP"
                if "TROT" in text:
                    intent = "TROT"
                elif "STOP" in text:
                    intent = "STOP"

                if intent == last:
                    continue
                last = intent

                if intent == "TROT":
                    do_trot()
                else:
                    do_stop()

    except asyncio.CancelledError:
        # Normal during shutdown; swallow it for clean exit.
        pass

def run():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Clean exit, no traceback.
        print("\n[bridge] Exit.")

if __name__ == "__main__":
    run()
