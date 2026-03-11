/**
 * Antigravity — Lobby Page JavaScript
 *
 * Handles WebSocket connection for matchmaking.
 * When a match is found, redirects to the chat room.
 */

let ws = null;
let isSearching = false;
let currentMode = 'video';

const startTextBtn = document.getElementById('start-chat-text-btn');
const startVideoBtn = document.getElementById('start-chat-video-btn');
const cancelBtn = document.getElementById('cancel-search-btn');
const lobbyStatus = document.getElementById('lobby-status');
const statusText = document.getElementById('status-text');
const lobbyTitle = document.getElementById('lobby-title');
const lobbySubtitle = document.getElementById('lobby-subtitle');

// Video elements
const localVideoPreview = document.getElementById('local-video-preview');
let localPreviewStream = null;
let isVideoMuted = false;
let isAudioMuted = false;

async function startLocalVideoPreview() {
    try {
        localPreviewStream = await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: true
        });
        if (localVideoPreview) {
            localVideoPreview.srcObject = localPreviewStream;
        }
    } catch (err) {
        console.error('[Lobby] Error accessing media devices.', err);
    }
}

function stopLocalVideoPreview() {
    if (localPreviewStream) {
        localPreviewStream.getTracks().forEach(track => track.stop());
    }
}

async function toggleCameraPreview() {
    const btn = document.getElementById('toggle-camera-preview');
    if (!localPreviewStream) return;

    const videoTrack = localPreviewStream.getVideoTracks()[0];
    
    if (videoTrack && videoTrack.readyState === 'live') {
        videoTrack.stop();
        btn.classList.remove('active');
        btn.style.opacity = '0.7';
        isVideoMuted = true;
    } else {
        try {
            const newStream = await navigator.mediaDevices.getUserMedia({ video: true });
            const newVideoTrack = newStream.getVideoTracks()[0];
            
            if (videoTrack) {
                localPreviewStream.removeTrack(videoTrack);
            }
            localPreviewStream.addTrack(newVideoTrack);
            localVideoPreview.srcObject = localPreviewStream; // Refresh local view
            
            btn.classList.add('active');
            btn.style.opacity = '1';
            isVideoMuted = false;
        } catch (err) {
            console.error('[Lobby] Could not restart camera hardware', err);
        }
    }
}

async function toggleMicPreview() {
    const btn = document.getElementById('toggle-mic-preview');
    if (!localPreviewStream) return;

    const audioTrack = localPreviewStream.getAudioTracks()[0];
    
    if (audioTrack && audioTrack.readyState === 'live') {
        audioTrack.stop();
        btn.classList.remove('active');
        btn.style.opacity = '0.7';
        isAudioMuted = true;
    } else {
        try {
            const newStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const newAudioTrack = newStream.getAudioTracks()[0];
            
            if (audioTrack) {
                localPreviewStream.removeTrack(audioTrack);
            }
            localPreviewStream.addTrack(newAudioTrack);
            
            btn.classList.add('active');
            btn.style.opacity = '1';
            isAudioMuted = false;
        } catch (err) {
            console.error('[Lobby] Could not restart mic hardware', err);
        }
    }
}

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/chat/`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('[Lobby] WebSocket connected');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleMessage(data);
    };

    ws.onclose = (event) => {
        console.log('[Lobby] WebSocket closed:', event.code);
        // Reconnect after a delay if not intentional
        if (isSearching) {
            setTimeout(connectWebSocket, 2000);
        }
    };

    ws.onerror = (error) => {
        console.error('[Lobby] WebSocket error:', error);
    };
}

function handleMessage(data) {
    switch (data.type) {
        case 'connection_established':
            console.log('[Lobby] Connected as:', data.anonymous_id);
            break;

        case 'searching':
            updateUI('searching');
            break;

        case 'matched':
            // Store session info and redirect to chat room
            sessionStorage.setItem('ag_session_id', data.session_id);
            sessionStorage.setItem('ag_room', data.room);
            sessionStorage.setItem('ag_mode', data.mode || 'video');
            window.location.href = '/chat/room/';
            break;

        case 'search_cancelled':
            updateUI('idle');
            break;

        case 'online_count':
            const countEl = document.getElementById('online-count');
            if (countEl) countEl.innerText = data.count;
            break;

        case 'error':
            console.error('[Lobby] Error:', data.message);
            updateUI('idle');
            break;
    }
}

function startSearching(mode) {
    if (mode) currentMode = mode;
    isSearching = true;

    if (!ws || ws.readyState !== WebSocket.OPEN) {
        connectWebSocket();
        // Wait for connection then send
        const waitForOpen = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                clearInterval(waitForOpen);
                ws.send(JSON.stringify({ type: 'find_partner', mode: currentMode }));
            }
        }, 100);
    } else {
        ws.send(JSON.stringify({ type: 'find_partner', mode: currentMode }));
    }

    updateUI('searching');
}

function cancelSearch() {
    isSearching = false;
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'cancel_search' }));
    }
    updateUI('idle');
}

function updateUI(state) {
    if (state === 'searching') {
        if (startTextBtn) startTextBtn.style.display = 'none';
        if (startVideoBtn) startVideoBtn.style.display = 'none';
        cancelBtn.style.display = 'inline-flex';
        lobbyStatus.style.display = 'flex';
        lobbyTitle.textContent = 'Searching...';
        lobbySubtitle.textContent = `Hang tight, finding a ${currentMode} match...`;
        statusText.textContent = `Looking for ${currentMode} partner...`;
    } else {
        if (startTextBtn) startTextBtn.style.display = 'inline-flex';
        if (startVideoBtn) startVideoBtn.style.display = 'inline-flex';
        cancelBtn.style.display = 'none';
        lobbyStatus.style.display = 'none';
        lobbyTitle.textContent = 'Ready to Chat?';
        lobbySubtitle.textContent = "You'll be matched with a random student anonymously";
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    connectWebSocket();
    startLocalVideoPreview();
});

// Cleanup when leaning page
window.addEventListener('beforeunload', () => {
    stopLocalVideoPreview();
});
