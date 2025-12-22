import websockets

ws = websockets.connect("ws://localhost:8081")
print(ws)