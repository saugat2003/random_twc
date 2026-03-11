/**
 * Antigravity — Chat Room JavaScript
 *
 * Handles WebRTC video/audio streams, text messaging via WebSocket,
 * and UI interactions for the chat room.
 */

const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${window.location.host}/ws/chat/`;
let ws;

// WebRTC State
let localStream = null;
let peerConnection = null;
const configuration = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' }
    ]
};

// UI Elements
const remoteVideo = document.getElementById('remote-video');
const localVideo = document.getElementById('local-video');
const videoGrid = document.getElementById('video-grid');
const localVideoWrapper = document.getElementById('local-video-wrapper');
const remotePlaceholder = document.getElementById('remote-placeholder');
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const partnerStatus = document.getElementById('partner-status');
const typingIndicator = document.getElementById('typing-indicator');

let isPartnerConnected = false;
let typingTimeout = null;
const chatMode = sessionStorage.getItem('ag_mode') || 'video';

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    // 1. Get media access
    await initializeMedia();

    // 2. Connect WebSocket
    connectWebSocket();

    // Safety check for skipping logic
    window.addEventListener('beforeunload', () => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'skip_partner', mode: chatMode }));
        }
    });
});

// ---------- WebSocket & Signaling ----------

function connectWebSocket() {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('[Chat] WebSocket connected');
        addSystemMessage("Connected to Antigravity server.");
        // Re-join match if redirected silently
        ws.send(JSON.stringify({ type: 'find_partner' }));
    };

    ws.onmessage = async (event) => {
        const data = JSON.parse(event.data);
        await handleMessage(data);
    };

    ws.onclose = (event) => {
        console.log('[Chat] WebSocket closed', event);
        setPartnerStatus("Disconnected", "var(--error)");
    };
}

async function handleMessage(data) {
    switch (data.type) {
        case 'matched':
            console.log('[Chat] Matched');
            sessionStorage.setItem('ag_session_id', data.session_id);
            setPartnerStatus("Connected", "var(--neon-green)");
            chatMessages.innerHTML = '';
            addSystemMessage("You're now chatting with a stranger. Say hi!");
            isPartnerConnected = true;
            if (chatMode !== 'text') { // Only setup peer connection if not in text-only mode
                setupPeerConnection();
            }
            break;

        case 'chat_message':
            appendMessage(data.message, data.is_mine);
            typingIndicator.classList.remove('visible');
            break;

        case 'typing':
            if (data.is_typing) {
                typingIndicator.classList.add('visible');
                chatMessages.scrollTop = chatMessages.scrollHeight;
            } else {
                typingIndicator.classList.remove('visible');
            }
            break;

        case 'partner_left':
            isPartnerConnected = false;
            setPartnerStatus("Stranger left", "var(--error)");
            addSystemMessage("Stranger has disconnected. Finding a new partner...");
            cleanupRTC();
            break;

        // --- WebRTC Signaling ---
        case 'video_offer':
            if (chatMode === 'text') return; // Ignore video offers in text-only mode
            if (!peerConnection) setupPeerConnection();
            await peerConnection.setRemoteDescription(new RTCSessionDescription(data.data));
            const answer = await peerConnection.createAnswer();
            await peerConnection.setLocalDescription(answer);
            ws.send(JSON.stringify({ type: 'video_answer', data: peerConnection.localDescription }));
            break;

        case 'video_answer':
            if (chatMode === 'text') return; // Ignore video answers in text-only mode
            await peerConnection.setRemoteDescription(new RTCSessionDescription(data.data));
            break;

        case 'ice_candidate':
            if (chatMode === 'text') return; // Ignore ICE candidates in text-only mode
            if (peerConnection) {
                try {
                    await peerConnection.addIceCandidate(new RTCIceCandidate(data.data));
                } catch (e) {
                    console.warn('[Chat] Error adding ICE candidate', e);
                }
            }
            break;
    }
}

// ---------- WebRTC ----------

async function initializeMedia() {
    if (chatMode === 'text') {
        // Text-only mode: Hide video section, expand chat sidebar
        const videoSection = document.querySelector('.video-section');
        const chatSidebar = document.querySelector('.chat-sidebar');
        if (videoSection) videoSection.style.display = 'none';
        if (chatSidebar) chatSidebar.style.width = '100%';
        return; // Skip WebRTC signaling and media gathering
    }

    try {
        localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        localVideo.srcObject = localStream;
        localVideoWrapper.style.display = 'block';
        videoGrid.classList.add('dual');
    } catch (err) {
        console.error('[Chat] Error accessing media devices:', err);
        addSystemMessage("Camera/Microphone access denied or unavailable.");
    }
}

function setupPeerConnection() {
    peerConnection = new RTCPeerConnection(configuration);

    // Add local stream tracks
    if (localStream) {
        localStream.getTracks().forEach(track => {
            peerConnection.addTrack(track, localStream);
        });
    }

    // Handle incoming stream
    peerConnection.ontrack = (event) => {
        console.log('[Chat] Remote stream received');
        remoteVideo.srcObject = event.streams[0];
        remotePlaceholder.style.display = 'none';
    };

    // Handle ICE candidates
    peerConnection.onicecandidate = (event) => {
        if (event.candidate) {
            ws.send(JSON.stringify({ type: 'ice_candidate', data: event.candidate }));
        }
    };

    // Negotiate (Caller creates offer)
    peerConnection.onnegotiationneeded = async () => {
        try {
            const offer = await peerConnection.createOffer();
            await peerConnection.setLocalDescription(offer);
            ws.send(JSON.stringify({ type: 'video_offer', data: peerConnection.localDescription }));
        } catch (err) {
            console.error('[Chat] Negotiation error:', err);
        }
    };
}

function cleanupRTC() {
    if (peerConnection) {
        peerConnection.close();
        peerConnection = null;
    }
    remoteVideo.srcObject = null;
    remotePlaceholder.style.display = 'flex';
}

// ---------- UI Interaction ----------

function setPartnerStatus(text, color) {
    partnerStatus.innerHTML = `<span class="status-dot" style="background: ${color}"></span><span>${text}</span>`;
}

function addSystemMessage(text) {
    const div = document.createElement('div');
    div.className = 'system-message';
    div.textContent = text;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendMessage(text, isMine) {
    const div = document.createElement('div');
    div.className = `message ${isMine ? 'sent' : 'received'}`;

    const txt = document.createElement('div');
    txt.textContent = text;
    div.appendChild(txt);

    const time = document.createElement('div');
    time.className = 'message-time';
    const d = new Date();
    time.textContent = d.getHours() + ':' + d.getMinutes().toString().padStart(2, '0');
    div.appendChild(time);

    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function sendMessage() {
    const text = chatInput.value.trim();
    if (text && ws && isPartnerConnected) {
        ws.send(JSON.stringify({ type: 'chat_message', message: text }));
        chatInput.value = '';
        ws.send(JSON.stringify({ type: 'stop_typing' }));
    }
}

// Enter to send
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

// Typing detection
chatInput.addEventListener('input', () => {
    if (!isPartnerConnected) return;

    ws.send(JSON.stringify({ type: 'typing' }));

    clearTimeout(typingTimeout);
    typingTimeout = setTimeout(() => {
        ws.send(JSON.stringify({ type: 'stop_typing' }));
    }, 1500);
});

// Video Controls
async function toggleCamera() {
    const btn = document.getElementById('toggle-camera');
    if (!localStream) return;

    const videoTrack = localStream.getVideoTracks()[0];
    
    // If the track exists and is active, stop it to kill the hardware
    if (videoTrack && videoTrack.readyState === 'live') {
        videoTrack.stop(); // Stops the hardware
        btn.classList.remove('active');
        btn.style.opacity = '0.7';
        localVideoWrapper.style.opacity = '0.3';
    } else {
        // Track is stopped or doesn't exist, we must re-request camera
        try {
            const newStream = await navigator.mediaDevices.getUserMedia({ video: true });
            const newVideoTrack = newStream.getVideoTracks()[0];
            
            if (videoTrack) {
                localStream.removeTrack(videoTrack);
            }
            localStream.addTrack(newVideoTrack);
            localVideo.srcObject = localStream; // Refresh local view
            
            // Replace the track on the active WebRTC connection
            if (peerConnection) {
                const sender = peerConnection.getSenders().find(s => s.track && s.track.kind === 'video');
                if (sender) {
                    sender.replaceTrack(newVideoTrack);
                }
            }
            
            btn.classList.add('active');
            btn.style.opacity = '1';
            localVideoWrapper.style.opacity = '1';
        } catch (err) {
            console.error('[Chat] Could not restart camera hardware', err);
            addSystemMessage("Could not access camera.");
        }
    }
}

async function toggleMic() {
    const btn = document.getElementById('toggle-mic');
    if (!localStream) return;

    const audioTrack = localStream.getAudioTracks()[0];
    
    // If track exists and active, stop it
    if (audioTrack && audioTrack.readyState === 'live') {
        audioTrack.stop(); // Stops hardware mic tracking
        btn.classList.remove('active');
        btn.style.opacity = '0.7';
        btn.classList.add('danger');
    } else {
        // Turn back on
        try {
            const newStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const newAudioTrack = newStream.getAudioTracks()[0];
            
            if (audioTrack) {
                localStream.removeTrack(audioTrack);
            }
            localStream.addTrack(newAudioTrack);
            
            // Replace track in active WebRTC connection
            if (peerConnection) {
                const sender = peerConnection.getSenders().find(s => s.track && s.track.kind === 'audio');
                if (sender) {
                    sender.replaceTrack(newAudioTrack);
                }
            }
            
            btn.classList.add('active');
            btn.style.opacity = '1';
            btn.classList.remove('danger');
        } catch (err) {
            console.error('[Chat] Could not restart mic hardware', err);
            addSystemMessage("Could not access microphone.");
        }
    }
}

// Settings default active state for controls
if (chatMode !== 'text') { // Only set active state if video controls are relevant
    document.getElementById('toggle-camera').classList.add('active');
    document.getElementById('toggle-mic').classList.add('active');
}


// Skip Partner
function skipPartner() {
    if (ws) {
        ws.send(JSON.stringify({ type: 'skip_partner', mode: chatMode }));
        cleanupRTC();
        chatMessages.innerHTML = '';
        setPartnerStatus("Searching...", "var(--warning)");
        isPartnerConnected = false;
    }
}

// ---------- Reporting System ----------

function openReportModal() {
    document.getElementById('report-modal').classList.add('active');
}

function closeReportModal() {
    document.getElementById('report-modal').classList.remove('active');
}

async function submitReport() {
    const reason = document.querySelector('input[name="report-reason"]:checked').value;
    const desc = document.getElementById('report-description').value;
    const sessionId = sessionStorage.getItem('ag_session_id');
    const roomName = sessionStorage.getItem('ag_room');

    if (!sessionId || !roomName) {
        window.location.href = '/chat/lobby/';
        return;
    }

    try {
        const response = await fetch('/moderation/report/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                reason: reason,
                description: desc,
                session_id: sessionId
            })
        });

        if (response.ok) {
            // Automatically skip partner after reporting
            skipPartner();
            closeReportModal();
            // Show toast visually (you'd normally pipe this into django messages or js alerts)
            alert("Report submitted successfully. You have been disconnected from the user.");
        }
    } catch (e) {
        console.error(e);
        alert("Error submitting report.");
    }
}

// Utils
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
