from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate, MediaStreamTrack, sdp
from aiortc.contrib.media import MediaPlayer, MediaRecorder, MediaRelay


class Descriptor(BaseModel):
    type: str
    sdp: str


class Participant(BaseModel, arbitrary_types_allowed=True):
    socket: WebSocket
    conn: RTCPeerConnection
    online: bool = False
    videoTrack: MediaStreamTrack | None = None
    audioTrack: MediaStreamTrack | None = None

    async def renegotiate(self):
        offer = await self.conn.createOffer()
        await self.conn.setLocalDescription(offer)
        await self.socket.send_json({
            "type": self.conn.localDescription.type,
            "sdp": self._remove_extmap(self.conn.localDescription.sdp)
        })
    
    def _remove_extmap(self, offer: str):
        sdp = [line for line in offer.splitlines() if not line.startswith("a=extmap")]
        return "\r\n".join(sdp) + "\r\n"
    

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_methods="*",
    allow_credentials="*",
    allow_headers="*"
)

relay: MediaRelay = MediaRelay()
activeParticipants: dict[int, Participant] = dict()


@app.get("/")
async def get_code():
    with open("./static/index.html") as f:
        return HTMLResponse(f.read())
    

@app.get("/client.js")
async def get_code():
    with open("./static/client.js") as f:
        return PlainTextResponse(f.read())

 
@app.websocket("/join")
async def join_room(ws: WebSocket):
    global activeParticipants

    await ws.accept()

    uid = len(activeParticipants)
    user = Participant(socket=ws, conn=RTCPeerConnection())
    activeParticipants[uid] = user

    print(len(activeParticipants))
    
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
    
            await user.conn.addIceCandidate(RTCIceCandidate(
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
            offer = RTCSessionDescription(sdp=data["sdp"], type=data["type"])

            @user.conn.on('track')
            def on_track(track):
                @track.on("ended")
                async def on_ended():
                    print("Track is ended :(")
    
                global relay
                if track.kind == "audio":
                    user.audioTrack = track
                if track.kind == "video":
                    user.videoTrack = track

            @user.conn.on("connectionstatechange")
            async def on_connectionstatechange():
                global activeParticipants
                nonlocal user
    
                print(f"The connection changed its state to: {user.conn.connectionState}")
                
                if user.conn.connectionState == "connected" and not user.online:
                    print("Starting to send tracks")
                    for participant in activeParticipants.values():
                        print(participant)
                        if participant.audioTrack:
                            user.conn.addTrack(relay.subscribe(participant.audioTrack))
                        if participant.videoTrack:
                            user.conn.addTrack(relay.subscribe(participant.videoTrack))
                    await user.renegotiate()
                    user.online = True
            
            await user.conn.setRemoteDescription(offer)
            answer = await user.conn.createAnswer()
            await user.conn.setLocalDescription(answer)

            await ws.send_json({
                "type": user.conn.localDescription.type,
                "sdp": user.conn.localDescription.sdp
            })
