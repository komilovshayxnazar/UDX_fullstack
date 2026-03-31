import subprocess
import os

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def test_adb_connection():
    print("Checking for connected Android devices...")
    stdout, stderr, code = run_command("adb devices")
    if code == 0 and "device" in stdout.split("\n")[-2]: # Basic check for at least one device
        print("✅ Device connected")
        print(stdout)
    else:
        print("❌ No device found or adb not in PATH")
        print(stderr)

def test_app_installed():
    print("\nChecking if UDX app is installed...")
    package_name = "com.udx.app"
    stdout, stderr, code = run_command(f"adb shell pm list packages {package_name}")
    if package_name in stdout:
        print(f"✅ App {package_name} is installed")
    else:
        print(f"❌ App {package_name} NOT found on device")

def test_app_is_running():
    print("\nChecking if UDX app is currently running...")
    package_name = "com.udx.app"
    stdout, stderr, code = run_command(f"adb shell pidof {package_name}")
    if stdout:
        print(f"✅ App {package_name} is running with PID: {stdout}")
    else:
        print(f"❌ App {package_name} is NOT running")

if __name__ == "__main__":
    test_adb_connection()
    test_app_installed()
    test_app_is_running()
