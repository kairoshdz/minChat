import socket
import threading
import time

GREEN = "\033[92m"
RESET = "\033[0m"

HOST = "34.41.146.111"
PORT = 9000

# create socket, connect to server
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))

# wait for "Enter your username: "
prompt = client.recv(4096).decode()
username = input(prompt)
client.sendall(username.encode())

# constantly listens for messages
def receive():
    while True:
        try:
            msg = client.recv(4096).decode()
            print(f"{GREEN}{msg}{RESET}", end="")
        except:
            print("Disconnected from server.")
            break

# sends "[dadum]" as a heartneat to the server every 30 seconds so we don't get dropped
def heartbeat():
    while True:
        time.sleep(30)
        try:
            client.sendall("[dadum]".encode())
        except:
            break

# run in background
threading.Thread(target=receive, daemon=True).start()
threading.Thread(target=heartbeat, daemon=True).start()  # run heartbeat in background too

# sends messages to server
while True:
    try:
        msg = input()
        client.sendall(msg.encode())
    except KeyboardInterrupt:
        client.close()
        break