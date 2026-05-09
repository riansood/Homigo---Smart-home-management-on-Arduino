import serial
import requests
import psycopg2
import bcrypt
import getpass
import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# -------- CONFIG --------
PORT = 'COM6'
BAUD = 115200
DB_CONFIG = {
    'dbname': 'dab_di23242b_133',
    'user': 'dab_di23242b_133',
    'password': 'snCN+GM/3fkdyUkv',
    'host': 'bronto.ewi.utwente.nl',
    'port' : 5432
}
GOVEE_API_DEVICES = "https://developer-api.govee.com/v1/devices"
GOVEE_API_CONTROL = "https://developer-api.govee.com/v1/devices/control"

# Spotify credentials  add your own here
CLIENT_ID = '88373795bbba427891c32220d7a79192'
CLIENT_SECRET = 'f3f15780ce564b3eb9a5ed1898beda67'
REDIRECT_URI = 'http://127.0.0.1:8000/callback'
SPOTIFY_SCOPE = 'user-read-playback-state user-modify-playback-state user-read-currently-playing'

# -------- GLOBALS --------
API_KEY = None
EMAIL = None
DEVICES = {}  # Govee devices
SP = None     # Spotipy client
PLAYLISTS = {} # {'happy': playlist_uri, 'on': playlist_uri, 'house': playlist_uri}


# -------- DB & AUTH --------
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def prompt_login():
    global API_KEY, EMAIL, SP, PLAYLISTS

    while True:
        EMAIL = input("Enter email: ").strip()
        if EMAIL:
            break
        print("Email cannot be empty. Please enter a valid email.")

    conn = get_db_connection()
    cur = conn.cursor()

    sql = """
        SELECT "password", "salt", "lightAPI"
        FROM "homigo"."User"
        WHERE "EmailAddress" = CAST(%s AS VARCHAR);
    """
    cur.execute(sql, (EMAIL,))
    row = cur.fetchone()

    if not row:
        print("User not found.")
        exit(1)

    stored_pw, salt, api_key = row

    # Password retry loop
    max_attempts = 3
    attempts = 0
    while attempts < max_attempts:
        password = getpass.getpass("Enter password: ").encode('utf-8')
        hashed_pw = bcrypt.hashpw(password, salt.encode('utf-8')).decode('utf-8')

        if hashed_pw == stored_pw:
            API_KEY = api_key
            print("Login successful.\n")
            break
        else:
            attempts += 1
            print(f"Invalid password. Attempts remaining: {max_attempts - attempts}")
    else:
        print("Too many failed attempts. Exiting.")
        exit(1)

    cur.close()
    conn.close()

    # Initialize Spotify client after login
    SP = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SPOTIFY_SCOPE,
        open_browser=False
    ))

    # Fetch playlists for each scene from DB tables
    

def get_playlist_uri(url):
    """Convert playlist URL to Spotify URI"""
    if 'open.spotify.com' in url:
        parts = url.split('/')
        playlist_id = parts[-1].split('?')[0]
        return f"spotify:playlist:{playlist_id}"
    return url  # assume already URI


# -------- Govee Control --------
def fetch_govee_devices():
    global DEVICES
    headers = { "Govee-API-Key": API_KEY }
    res = requests.get(GOVEE_API_DEVICES, headers=headers)
    if res.status_code != 200:
        print("Failed to fetch devices.")
        exit(1)

    for dev in res.json().get("data", {}).get("devices", []):
        DEVICES[dev["device"]] = dev["model"]

    print(f"Loaded {len(DEVICES)} Govee devices.\n")

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def set_scene(scene_name):
    print("entered set scene " + scene_name)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        sql = f"""
        SELECT "lightMAC", "lightColour"
        FROM "homigo"."{scene_name}"
        WHERE "emailAddress" = CAST(%s AS VARCHAR);
        """
        cur.execute(sql, (EMAIL,))
        rows = cur.fetchall()
    except Exception as e:
        print(f"DB error while loading scene '{scene_name}': {e}")
        return
    finally:
        cur.close()
        conn.close()

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        scene = scene_name
        cur.execute(f""" 
            SELECT "playlist" 
            FROM "homigo"."{scene}" 
            WHERE "emailAddress" = CAST(%s AS VARCHAR) 
            LIMIT 1;
        """, (EMAIL,))
        playlist_row = cur.fetchone()
        if playlist_row and playlist_row[0]:
            playlist_url = playlist_row[0]
            PLAYLISTS[scene] = get_playlist_uri(playlist_url)
            print(PLAYLISTS)
        else:
            print(f"No playlist found for scene '{scene}'.")
    except Exception as e:
        print(f"Error fetching playlist for scene '{scene}': {e}")

    cur.close()
    conn.close()


    headers = {
        "Govee-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    for mac, color in rows:
        model = DEVICES.get(mac)
        if not model:
            print(f"{mac} not in device list.")
            continue

        r, g, b = hex_to_rgb(color)
        payload = {
            "device": mac,
            "model": model,
            "cmd": {
                "name": "color",
                "value": { "r": r, "g": g, "b": b }
            }
        }

        res = requests.put(GOVEE_API_CONTROL, headers=headers, json=payload)
        print(f"{scene_name.title()} â†’ {mac} â†’ #{color} â†’ Status: {res.status_code}")

def turn_lights(on=True):
    state = "on" if on else "off"
    headers = {
        "Govee-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    for mac, model in DEVICES.items():
        payload = {
            "device": mac,
            "model": model,
            "cmd": {
                "name": "turn",
                "value": state
            }
        }
        res = requests.put(GOVEE_API_CONTROL, headers=headers, json=payload)
        print(f"Turned {state} â†’ {mac} â†’ Status: {res.status_code}")


# -------- Spotify Playback --------
def play_playlist(scene_name):
    print("trying to play the playlist")
    """Play the playlist corresponding to the scene on the first active Spotify device."""
    

    if scene_name not in PLAYLISTS:
        print(f"No playlist URI found for scene '{scene_name}'.")
        return
    
    playlist_uri = PLAYLISTS[scene_name]


    print(SP.devices())
    devices = SP.devices()
    if not devices['devices']:
        print("No active Spotify Connect devices found.")
        return
    print(devices)

    device = devices['devices'][0]
    print(device)
    device_id = device['id']
    print(f"Playing playlist '{scene_name}' on device: {device['name']}")

    # Transfer playback to this device if not active
    if not device['is_active']:
        SP.transfer_playback(device_id=device_id, force_play=False)

    SP.start_playback(device_id=device_id, context_uri=playlist_uri)
    print(f"Started playing playlist '{scene_name}'.")


# -------- Serial Listening --------
def homigo_received(ser):
    start = time.time()
    while time.time() - start < 6:
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
        except:
            continue

        

        if line.startswith("off:"):
            try:
                conf = float(line.split(":")[1].strip())
                if conf > 0.9:
                    print("Command: OFF")
                    turn_lights(False)
                    return
            except: pass

        elif any(line.startswith(scene + ":") for scene in ["happy", "house", "on"]):
            storeLine = line

            try:

                scene, conf = storeLine.split(":")

                conf = float(conf.strip())

                if conf > 0.85:
                    if scene == "house":
                        print(f"Command: Scene house")
                    
                        set_scene("house")
                        play_playlist("house")
                    elif scene == "on":
                        print(f"Command: Scene on")
                        set_scene("on")
                        play_playlist("on")
                    else:
                        print(f"Command: Scene happy")
                        set_scene("happy")
                        play_playlist("happy")

                    print(f"Command: Scene {scene}")

                    #set_scene(scene)

                    return

            except: pass


# -------- Main Program --------
def main():
    prompt_login()
    fetch_govee_devices()

    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
        print("Listening for Arduino... Say 'homigo' to activate.\n")

        while True:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                print(f"[Arduino] {line}")
                if line.startswith("homigo:"):
                    try:
                        conf = float(line.split(":")[1].strip())
                        if conf > 0.8:
                            print("\n" + "="*20)
                            print("HOMIGO ACTIVATED â€” Listening...")
                            print("="*20 + "\n")
                            homigo_received(ser)
                    except:
                        pass
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        ser.close()



if __name__ == "__main__":

    main()