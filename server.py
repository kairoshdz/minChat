# socket lets programs connect over networks, select allows
# several clients to connect without using threads
import socket
import select
import time
import subprocess
import sys

HOST = "0.0.0.0"
PORT = 9000
BUFFER = 4096
HEARTBEAT_TIMEOUT = 60  # seconds before a silent client is dropped

# creates server, attaches to port, waits for connections
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen()

sockets = [server, sys.stdin]  # select() watches this list
clients = {}        # socket -> {"name": str, "last_seen": float}

print(f"Server listening on port {PORT}...")

# sends a message to every connected client except the one who sent it
def broadcast(message, exclude=None):
    for s in clients:
        if s is not exclude:
            try:
                s.sendall(message.encode())
            except:
                pass

# removes client and socket of client who left
def remove_client(sock):
    if sock in clients:
        name = clients[sock]["name"]
        print(f"{name} disconnected.")
        broadcast(f"{name} left the chat.\n", exclude=sock)
        del clients[sock]
    if sock in sockets:
        sockets.remove(sock)
    sock.close()

# loops through all clients and boots any that haven't sent a heartbeat in 60 seconds
def check_heartbeats():
    now = time.time()
    for sock in list(clients):  # list() so we can delete from clients mid-loop
        if now - clients[sock]["last_seen"] > HEARTBEAT_TIMEOUT:
            name = clients[sock]["name"]
            print(f"{name} timed out.")
            try:
                sock.sendall("You were disconnected for being idle.\n".encode())
            except:
                pass
            remove_client(sock)

# runs terminal commands like ping/netstat from server
def handle_command(command):
    parts = command.strip().split()
    cmd = parts[0]
    arg = parts[1] if len(parts) > 1 else ""

    if cmd == "/netstat":
        result = subprocess.run(["netstat", "-tn"], capture_output=True, text=True)
        print(result.stdout)

    elif cmd == "/ping":
        if not arg:
            print("Usage: /ping <host>")
        else:
            result = subprocess.run(["ping", "-c", "4", arg], capture_output=True, text=True)
            print(result.stdout)

    elif cmd == "/traceroute":
        if not arg:
            print("Usage: /traceroute <host>")
        else:
            result = subprocess.run(["traceroute", "-m", "15", arg], capture_output=True, text=True)
            print(result.stdout)

    elif cmd == "/list":
        if not clients:
            print("No users connected.")
        for sock, info in clients.items():
            elapsed = time.time() - info["last_seen"]
            print(f"  {info['name']}  —  last seen {elapsed:.0f}s ago")

    else:
        print(f"Unknown command: {cmd}")

# waits for new connection/new message
while True:
    
    
    check_heartbeats()

    # 5: if nothing happens for 5 seconds, stop waiting and loop
    # back so check_heartbeats() can run again. without it, select waits forever
    readable, _, _ = select.select(sockets, [], [], 5)

    for sock in readable:

        # if you typed something in the server terminal, handle it as a command
        if sock is sys.stdin:
            command = sys.stdin.readline().strip()
            if command:
                handle_command(command)


        # accepts client connection, asks username, stores information, watches socket
        elif sock is server:
            conn, addr = server.accept()
            conn.sendall(b"Enter your username: ")
            name = conn.recv(BUFFER).decode().strip()
            clients[conn] = {"name": name, "last_seen": time.time()}  # store name + join time
            sockets.append(conn)
            print(f"{name} connected from {addr[0]}")
            broadcast(f"{name} joined the chat.\n", exclude=conn)

        # user sends message, server reads and broadcasts (incl disconnecting)
        else:
            try:
                data = sock.recv(BUFFER)
                if data:
                    msg = data.decode().strip()
                    # if it's a heartbeat, just update their last_seen and don't broadcast
                    if msg == "[dadum]":
                        clients[sock]["last_seen"] = time.time()
                    else:
                        formatted = f"{clients[sock]['name']}: {msg}\n"
                        print(formatted, end="")
                        broadcast(formatted, exclude=sock)
                else:
                    raise ConnectionResetError
            except:
                remove_client(sock)