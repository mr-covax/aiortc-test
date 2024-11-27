const peer = new RTCPeerConnection();
const socket = new WebSocket("/join");

peer.onicecandidate = async (event) => {
    if (event.candidate) {
        request = {type: "candidate", candidate: event.candidate};
        await socket.send(JSON.stringify(request));
    }
};

peer.ontrack = (evt) => {
    if (evt.track.kind == 'video') {
        console.log("peer: track: got video")
        document.getElementById('videoSink').srcObject = evt.streams[0];
    }
    else {
        console.log("peer: track: got audio")
    }
};

peer.onconnectionstatechange = function () {
    console.log("connection: ", peer.connectionState)
};

socket.onopen = () => {
    console.log("websocket: initialized");
}

socket.onmessage = async (event) => {
    const struct = JSON.parse(event.data);
    console.log("websocket: onmessage: received type", struct.type);
    
    if (struct.type == "offer") {
        console.log(struct.sdp);
        await peer.setRemoteDescription(struct);
        const answer = peer.createAnswer();
        await peer.setLocalDescription(answer);
        
        await socket.send(JSON.stringify({
            type: peer.localDescription.type,
            sdp: peer.localDescription.sdp
        }));

    }
    else if (struct.type == "answer") {
        await peer.setRemoteDescription(struct);
    }
    else if (struct.type == "message") {
        console.log("Got message: ", struct.message);
    }
}

async function prepare() {
    stream = await navigator.mediaDevices.getUserMedia({audio: true, video: true});
    stream.getTracks().forEach(track => peer.addTrack(track, stream));
    
    offer = peer.createOffer();
    await peer.setLocalDescription(offer);
    
    const offerRequest = {
        type: peer.localDescription.type,
        sdp: peer.localDescription.sdp
    };
    
    await socket.send(JSON.stringify(offerRequest));
}

prepare();