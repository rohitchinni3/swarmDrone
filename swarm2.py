from supabase import create_client, Client
from dronekit import connect, VehicleMode, LocationGlobalRelative
import time
from threading import Thread

# Supabase credentials
SUPABASE_URL = "https://wwpozvjnhkreypawoeox.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind3cG96dmpuaGtyZXlwYXdvZW94Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjQ2NDcyMjAsImV4cCI6MjA0MDIyMzIyMH0.wARfqQNaLN5mt3K2QKjs82QP0Cav39PdBlc3GsrtUWw"

# Connect to Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Fetch latest status command from Supabase
def fetch_latest_status():
    response = supabase.table('status').select("status").order('id', desc=True).limit(1).execute()
    if response.data:
        latest_command = response.data[0]['status']
        print(f"Latest command from Supabase: {latest_command}")
        return latest_command
    else:
        print("No commands found in the database.")
        return None

# Fetch latest coordinates from Supabase
def fetch_latest_coordinates():
    response = supabase.table('coordinates').select("latitude, longitude").order('id', desc=True).limit(1).execute()
    if response.data:
        latest_entry = response.data[0]
        latitude = latest_entry['latitude']
        longitude = latest_entry['longitude']
        print(f"Latest coordinates fetched from Supabase: Latitude={latitude}, Longitude={longitude}")
        return latitude, longitude
    else:
        print("No coordinates found in the database.")
        return None, None

# Connect to the Vehicle
connection_string = '/dev/ttyACM0'
vehicle = connect(connection_string, baud=57600, wait_ready=True)

# Function to set vehicle mode with retry mechanism
def set_mode(vehicle, mode_name):
    vehicle.mode = VehicleMode(mode_name)
    for _ in range(5):  # Retry up to 5 times
        if vehicle.mode.name == mode_name:
            print(f"Mode set to {mode_name}")
            return True
        print(f"Attempting to set mode to {mode_name}...")
        time.sleep(1)
    print(f"Failed to set mode to {mode_name}")
    return False

# Function to arm and take off
def arm_and_takeoff(target_altitude):
    print("Performing pre-arm checks")
    while not vehicle.is_armable:
        print("Waiting for vehicle to initialize...")
        time.sleep(1)

    print("Arming vehicle")
    if not set_mode(vehicle, "GUIDED"):
        print("Failed to set GUIDED mode. Exiting.")
        return

    vehicle.arm()
    while not vehicle.armed:
        print("Waiting for arming...")
        time.sleep(1)

    print("Taking off!")
    vehicle.simple_takeoff(target_altitude)
    while True:
        print("Altitude:", vehicle.location.global_relative_frame.alt)
        if vehicle.location.global_relative_frame.alt >= target_altitude * 0.95:
            print("Reached target altitude")
            break
        time.sleep(1)

# Function to navigate to a specified location
def goto_location(lat, lon):
    print(f"Navigating to Latitude: {lat}, Longitude: {lon}")
    target_location = LocationGlobalRelative(lat, lon, vehicle.location.global_relative_frame.alt)
    vehicle.simple_goto(target_location)

# Function to hover
def hover():
    print("Drone hovering at the target location")

# Function to return to launch
def return_to_launch():
    print("Enabling RTL (Return to Launch)")
    set_mode(vehicle, "RTL")

# Main function to monitor commands and act accordingly
def monitor_and_execute():
    while True:
        # Fetch the latest command
        command = fetch_latest_status()
# 1 take off , 2 goto , 3 hover , 0 RTL from supabase 
        if command == 1:
            print("Command received: TAKEOFF")
            target_altitude = 15  # meters
            arm_and_takeoff(target_altitude)

        elif command == 2:
            print("Command received: GOTO")
            latitude, longitude = fetch_latest_coordinates()
            if latitude is not None and longitude is not None:
                goto_location(latitude, longitude)

        elif command == 3:
            print("Command received: HOVER")
            hover()

        elif command == 0:
            print("Command received: RTL")
            return_to_launch()

        # Check for new command every 5 seconds
        time.sleep(5)

# Start the monitoring and execution thread
monitor_thread = Thread(target=monitor_and_execute)
monitor_thread.start()
