from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from aiortc import RTCPeerConnection, RTCSessionDescription
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

@app.post("/offer", response_model=Descriptor)
async def init_connection(desc: Descriptor):
    global host
    
    peer = RTCPeerConnection()
    if host is None:
        host = peer

    offer = RTCSessionDescription(sdp=desc.sdp, type=desc.type)

    @peer.on('track')
    def on_track(track):
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

    return Descriptor(
        type=peer.localDescription.type,
        sdp=peer.localDescription.sdp
    )

