from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
from aiortc.contrib.media import MediaPlayer, MediaRecorder, MediaRelay

class Descriptor(BaseModel):
    type: str
    sdp: str


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_methods="*",
    allow_credentials="*",
    allow_headers="*"
)

host = None
host_audio = None
host_video = None
relay: MediaRelay = MediaRelay()

@app.get("/")
async def get_code():
    with open("./static/index.html") as f:
        return HTMLResponse(f.read())
    
@app.websocket("/join")
async def join_room(ws: WebSocket):
    global host
    await ws.accept()
    
    while True:
        data = await ws.receive_json()
        if data["type"] == "message":
            print(data["message"])
            await ws.send_json({"type": "message", "message": "I printed that shit!"})

        elif data["type"] == "candidate":
            payload = data["candidate"]
            candidate = payload["candidate"].split(" ")
            
            if payload["candidate"] == "":
                continue
    
            await peer.addIceCandidate(RTCIceCandidate(
                foundation=candidate[0],
                component=candidate[1],
                priority=candidate[3],
                ip=candidate[4],
                port=candidate[5],
                protocol=candidate[7],
                type=candidate[7],
                sdpMid=payload["sdpMid"],
                sdpMLineIndex=payload["sdpMLineIndex"]
            ))

        elif data["type"] == "offer":
            peer = RTCPeerConnection()
            if host is None:
                host = peer

            offer = RTCSessionDescription(sdp=data["sdp"], type=data["type"])

            @peer.on('track')
            def on_track(track):
                global relay 
    
                global host_audio, host_video
                if track.kind == "audio":
                    if peer == host:
                        host_audio = track
                        peer.addTrack(relay.subscribe(host_audio))
                    else:
                        print("Fuck off")
                        peer.addTrack(relay.subscribe(host_audio))
                    
                if track.kind == "video":
                    if peer == host:
                        host_video = track
                        peer.addTrack(relay.subscribe(host_video))
                    else:
                        peer.addTrack(relay.subscribe(host_video))

                @track.on("ended")
                async def on_ended():
                    print("Track is ended :(")

            @peer.on("connectionstatechange")
            async def on_connectionstatechange():
                print(f"The connection changed it state to: {peer.connectionState}")
            
            await peer.setRemoteDescription(offer)

            answer = await peer.createAnswer()
            await peer.setLocalDescription(answer)

            await ws.send_json({
                "type": peer.localDescription.type,
                "sdp": peer.localDescription.sdp
            })
