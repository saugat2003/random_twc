"""
WebSocket consumers for text chat, matchmaking, and WebRTC signaling.
"""

import json
import uuid
import logging
from datetime import datetime

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

from .matchmaking import add_to_queue, remove_from_queue
from .models import ChatSession

logger = logging.getLogger(__name__)

# Track active connection count globally in memory
active_connections = set()



class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    Main consumer handling:
    - Matchmaking (finding a partner)
    - Text messaging
    - Typing indicators
    - WebRTC signaling (offer, answer, ICE candidates)
    - Skip / Next partner
    """

    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return

        self.room_group_name = None
        self.session_id = None
        self.partner_channel = None
        self.is_searching = False
        self.mode = "video" # "video" or "text"

        await self.accept()
        
        # Add to tracking set and broadcast new count
        active_connections.add(self.channel_name)
        await self._broadcast_online_count()

        await self.send_json({
            "type": "connection_established",
            "message": "Connected to Antigravity",
            "anonymous_id": str(self.user.anonymous_id),
        })

    async def disconnect(self, close_code):
        if not hasattr(self, "user") or not self.user.is_authenticated:
            return

        # Remove from matchmaking queue
        if self.is_searching:
            await remove_from_queue(self.channel_layer, self.user.id)

        # End active session
        if self.session_id:
            await self._end_session()

        # Notify partner
        if self.room_group_name:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "partner_disconnected",
                    "message": "Your partner has disconnected.",
                },
            )
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

        # Remove from tracking set and broadcast new count
        if self.channel_name in active_connections:
            active_connections.remove(self.channel_name)
        await self._broadcast_online_count()

    async def receive_json(self, content):
        msg_type = content.get("type", "")
        handler = {
            "find_partner": self.handle_find_partner,
            "cancel_search": self.handle_cancel_search,
            "chat_message": self.handle_chat_message,
            "typing": self.handle_typing,
            "stop_typing": self.handle_stop_typing,
            "skip_partner": self.handle_skip_partner,
            # WebRTC signaling
            "video_offer": self.handle_webrtc_signal,
            "video_answer": self.handle_webrtc_signal,
            "ice_candidate": self.handle_webrtc_signal,
            "toggle_video": self.handle_webrtc_signal,
            "toggle_audio": self.handle_webrtc_signal,
        }.get(msg_type)

        if handler:
            await handler(content)
        else:
            await self.send_json({"type": "error", "message": f"Unknown type: {msg_type}"})

    # ---------- Matchmaking ----------

    async def handle_find_partner(self, content):
        """Start searching for a partner."""
        # Leave any existing room
        if self.room_group_name:
            await self._leave_room()

        self.mode = content.get("mode", "video")
        if self.mode not in ("video", "text"):
            self.mode = "video"
            
        self.is_searching = True
        await self.send_json({"type": "searching", "message": f"Looking for a {self.mode} chat partner..."})

        match = await add_to_queue(self.channel_layer, self.user.id, self.channel_name, self.mode)

        if match:
            user1_id, ch1, user2_id, ch2 = match
            room_id = str(uuid.uuid4())
            room_name = f"chat_{room_id}"

            # Create session in DB
            session = await self._create_session(user1_id, user2_id)

            # Notify both users
            for uid, ch in [(user1_id, ch1), (user2_id, ch2)]:
                await self.channel_layer.send(ch, {
                    "type": "match_found",
                    "room_name": room_name,
                    "session_id": str(session.id),
                    "mode": self.mode,
                })

    async def handle_cancel_search(self, content):
        """Cancel matchmaking search."""
        self.is_searching = False
        await remove_from_queue(self.channel_layer, self.user.id, self.mode)
        await self.send_json({"type": "search_cancelled", "message": "Search cancelled."})

    async def match_found(self, event):
        """Handle match found event — join the room."""
        room_name = event["room_name"]
        session_id = event["session_id"]
        mode = event.get("mode", "video")

        self.room_group_name = room_name
        self.session_id = session_id
        self.mode = mode
        self.is_searching = False

        await self.channel_layer.group_add(room_name, self.channel_name)

        await self.send_json({
            "type": "matched",
            "message": f"You've been matched with someone for {mode} chat!",
            "session_id": session_id,
            "room": room_name,
            "mode": mode,
        })

    # ---------- Messaging ----------

    async def handle_chat_message(self, content):
        """Broadcast a text message to the room."""
        if not self.room_group_name:
            await self.send_json({"type": "error", "message": "Not in a chat room."})
            return

        message = content.get("message", "").strip()
        if not message:
            return

        # Rate limit: max 200 chars
        message = message[:500]

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message_broadcast",
                "message": message,
                "sender_channel": self.channel_name,
                "timestamp": timezone.now().isoformat(),
            },
        )

    async def chat_message_broadcast(self, event):
        """Receive a chat message from the group and send to client."""
        is_mine = event["sender_channel"] == self.channel_name
        await self.send_json({
            "type": "chat_message",
            "message": event["message"],
            "is_mine": is_mine,
            "timestamp": event["timestamp"],
        })

    # ---------- Typing Indicators ----------

    async def handle_typing(self, content):
        if self.room_group_name:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "typing_indicator",
                    "sender_channel": self.channel_name,
                    "is_typing": True,
                },
            )

    async def handle_stop_typing(self, content):
        if self.room_group_name:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "typing_indicator",
                    "sender_channel": self.channel_name,
                    "is_typing": False,
                },
            )

    async def typing_indicator(self, event):
        if event["sender_channel"] != self.channel_name:
            await self.send_json({
                "type": "typing",
                "is_typing": event["is_typing"],
            })

    # ---------- Skip / Next ----------

    async def handle_skip_partner(self, content):
        """Skip current partner and start searching again."""
        if self.room_group_name:
            # Notify partner
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "partner_skipped",
                    "skipper_channel": self.channel_name,
                },
            )
            await self._leave_room()

        # Auto-search for next partner passing previous mode
        content["mode"] = self.mode
        await self.handle_find_partner(content)

    async def partner_skipped(self, event):
        """Receive skip notification."""
        if event["skipper_channel"] != self.channel_name:
            await self.send_json({
                "type": "partner_left",
                "message": "Your partner has skipped. Finding a new partner...",
            })
            # Leave room
            if self.room_group_name:
                await self.channel_layer.group_discard(
                    self.room_group_name, self.channel_name
                )
                self.room_group_name = None
                self.session_id = None

    async def partner_disconnected(self, event):
        """Handle partner disconnect."""
        if self.room_group_name:
            await self.send_json({
                "type": "partner_left",
                "message": event["message"],
            })
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )
            self.room_group_name = None
            self.session_id = None

    # ---------- WebRTC Signaling ----------

    async def handle_webrtc_signal(self, content):
        """Forward WebRTC signals (offer, answer, ICE) to partner in the room."""
        if not self.room_group_name:
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "webrtc_signal_broadcast",
                "signal_type": content["type"],
                "data": content.get("data", {}),
                "sender_channel": self.channel_name,
            },
        )

    async def webrtc_signal_broadcast(self, event):
        """Receive WebRTC signal from the group and forward to client (not sender)."""
        if event["sender_channel"] != self.channel_name:
            await self.send_json({
                "type": event["signal_type"],
                "data": event["data"],
            })

    # ---------- Helpers ----------

    async def _leave_room(self):
        if self.room_group_name:
            await self._end_session()
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )
            self.room_group_name = None
            self.session_id = None

    @database_sync_to_async
    def _create_session(self, user1_id, user2_id):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user1 = User.objects.get(id=user1_id)
            user2 = User.objects.get(id=user2_id)
            return ChatSession.objects.create(user_one=user1, user_two=user2)
        except User.DoesNotExist:
            return ChatSession.objects.create()

    @database_sync_to_async
    def _end_session(self):
        if self.session_id:
            try:
                session = ChatSession.objects.get(id=self.session_id)
                session.status = "ended"
                session.ended_at = timezone.now()
                session.save(update_fields=["status", "ended_at"])
            except ChatSession.DoesNotExist:
                pass

    async def _broadcast_online_count(self):
        """Broadcasts active connection count manually to all currently connected channels."""
        # Simple iteration to send live count since we don't have a global broadcast group
        # In a Redis setup you'd create an "all_users" group. We use loop here for simplicity explicitly without Redis
        count = len(active_connections)
        for channel in list(active_connections):
            try:
                await self.channel_layer.send(channel, {
                    "type": "online_count_update",
                    "count": count
                })
            except Exception:
                pass

    async def online_count_update(self, event):
        """Handle incoming online count update and send to client"""
        await self.send_json({
            "type": "online_count",
            "count": event["count"]
        })
