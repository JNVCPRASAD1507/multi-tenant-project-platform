import { useEffect, useState, useRef, useCallback } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  List,
  ListItemButton,
  ListItemText,
  Avatar,
  Divider,
  InputAdornment,
  CircularProgress,
  Chip,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import SearchIcon from "@mui/icons-material/Search";
import api from "../api";
import { useAuthStore } from "../store";

export default function Chat() {
  const token = useAuthStore((s) => s.accessToken);
  const currentUser = useAuthStore((s) => s.user);

  const [rooms, setRooms] = useState([]);
  const [activeRoom, setActiveRoom] = useState(null);
  const [messages, setMessages] = useState([]);
  const [body, setBody] = useState("");
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);
  const wsRef = useRef(null);

  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

  const WS_URL = API_URL.replace(/^http:/, "ws:").replace(/^https:/, "wss:");

  const loadRooms = useCallback(async () => {
    try {
      const { data } = await api.get("/chat/rooms");
      setRooms(data.items || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRooms();
  }, [loadRooms]);

  const loadMessages = async (roomId) => {
    try {
      const { data } = await api.get(`/chat/rooms/${roomId}/messages`);
      setMessages(data.items || []);
      setTimeout(
        () => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }),
        50,
      );
    } catch (e) {
      console.error(e);
    }
  };

  const openRoom = async (room) => {
    setActiveRoom(room);

    await loadMessages(room.id);

    // Close previous WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    if (!token) {
      return;
    }

    const ws = new WebSocket(
      `${WS_URL}/api/v1/ws/chat/${room.id}?token=${token}`,
    );

    ws.onopen = () => {
      console.log(`Chat WebSocket connected: room ${room.id}`);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === "chat_message") {
          setMessages((prev) => {
            // Prevent duplicate messages
            const alreadyExists = prev.some((item) => item.id === msg.id);

            if (alreadyExists) {
              return prev;
            }

            return [...prev, msg];
          });

          setTimeout(() => {
            messagesEndRef.current?.scrollIntoView({
              behavior: "smooth",
            });
          }, 50);
        }
      } catch (error) {
        console.error("Failed to process WebSocket message:", error);
      }
    };

    ws.onerror = (error) => {
      console.error("Chat WebSocket error:", error);
    };

    ws.onclose = () => {
      console.log(`Chat WebSocket closed: room ${room.id}`);
    };

    wsRef.current = ws;
  };

  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const handleSearch = async (q) => {
    setSearch(q);
    if (q.trim().length < 2) {
      setSearchResults([]);
      return;
    }
    try {
      const { data } = await api.get(
        `/chat/users/search?q=${encodeURIComponent(q)}`,
      );
      setSearchResults(data || []);
    } catch {
      setSearchResults([]);
    }
  };

  const startChat = async (userId) => {
    try {
      const { data } = await api.post("/chat/rooms", {
        participant_user_id: userId,
      });
      setSearch("");
      setSearchResults([]);
      await loadRooms();
      openRoom(data);
    } catch (e) {
      alert(e.response?.data?.detail?.message || "Could not start chat");
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();

    const messageBody = body.trim();

    if (!messageBody || !activeRoom) {
      return;
    }

    setSending(true);

    try {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            body: messageBody,
          }),
        );

        setBody("");
      } else {
        const { data } = await api.post(
          `/chat/rooms/${activeRoom.id}/messages`,
          {
            body: messageBody,
          },
        );

        // REST response is already published
        // through Redis by the backend.
        //
        // Don't append manually here because
        // WebSocket may also deliver it.

        setBody("");
      }
    } catch (err) {
      alert(err.response?.data?.detail?.message || "Failed to send");
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" mt={8}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Chat
      </Typography>
      <Typography variant="body2" color="text.secondary" mb={2}>
        Message users across organizations. Project data stays isolated.
      </Typography>

      <Box
        display="flex"
        gap={2}
        sx={{ height: "calc(100vh - 200px)", minHeight: 480 }}
      >
        {/* Sidebar – rooms + search */}
        <Card sx={{ width: 300, display: "flex", flexDirection: "column" }}>
          <CardContent sx={{ pb: 1 }}>
            <TextField
              fullWidth
              size="small"
              placeholder="Search users…"
              value={search}
              onChange={(e) => handleSearch(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                ),
              }}
            />
            {searchResults.length > 0 && (
              <List dense sx={{ maxHeight: 160, overflow: "auto", mt: 1 }}>
                {searchResults.map((u) => (
                  <ListItemButton key={u.id} onClick={() => startChat(u.id)}>
                    <Avatar sx={{ width: 28, height: 28, mr: 1, fontSize: 12 }}>
                      {u.full_name?.[0]}
                    </Avatar>
                    <ListItemText
                      primary={u.full_name}
                      secondary={u.email}
                      primaryTypographyProps={{ fontSize: 14 }}
                      secondaryTypographyProps={{ fontSize: 11 }}
                    />
                  </ListItemButton>
                ))}
              </List>
            )}
          </CardContent>
          <Divider />
          <List sx={{ flex: 1, overflow: "auto" }}>
            {rooms.length === 0 && (
              <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
                No conversations yet. Search a user to start.
              </Typography>
            )}
            {rooms.map((room) => (
              <ListItemButton
                key={room.id}
                selected={activeRoom?.id === room.id}
                onClick={() => openRoom(room)}
              >
                <Avatar
                  sx={{
                    width: 32,
                    height: 32,
                    mr: 1.5,
                    bgcolor: "secondary.main",
                    fontSize: 13,
                  }}
                >
                  {(room.other_participant_name || room.name || "C")[0]}
                </Avatar>
                <ListItemText
                  primary={
                    room.other_participant_name ||
                    room.name ||
                    `Room #${room.id}`
                  }
                  primaryTypographyProps={{ fontSize: 14, noWrap: true }}
                />
              </ListItemButton>
            ))}
          </List>
        </Card>

        {/* Messages panel */}
        <Card sx={{ flex: 1, display: "flex", flexDirection: "column" }}>
          {!activeRoom ? (
            <Box
              flex={1}
              display="flex"
              alignItems="center"
              justifyContent="center"
            >
              <Typography color="text.secondary">
                Select a conversation
              </Typography>
            </Box>
          ) : (
            <>
              <Box
                sx={{ p: 2, borderBottom: "1px solid", borderColor: "divider" }}
              >
                <Typography fontWeight={600}>
                  {activeRoom.other_participant_name ||
                    activeRoom.name ||
                    `Room #${activeRoom.id}`}
                </Typography>
                <Chip
                  label="Cross-org"
                  size="small"
                  color="secondary"
                  sx={{ mt: 0.5 }}
                />
              </Box>

              <Box sx={{ flex: 1, overflow: "auto", p: 2 }}>
                {messages.map((m) => {
                  const isMine = m.sender_id === currentUser?.id;
                  return (
                    <Box
                      key={m.id}
                      sx={{
                        display: "flex",
                        justifyContent: isMine ? "flex-end" : "flex-start",
                        mb: 1.5,
                      }}
                    >
                      <Box
                        sx={{
                          maxWidth: "70%",
                          px: 1.5,
                          py: 1,
                          borderRadius: 2,
                          bgcolor: isMine
                            ? "primary.main"
                            : "background.default",
                          border: isMine ? "none" : "1px solid #334155",
                        }}
                      >
                        {!isMine && (
                          <Typography variant="caption" color="text.secondary">
                            {m.sender_name}
                          </Typography>
                        )}
                        <Typography variant="body2">{m.body}</Typography>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ display: "block", mt: 0.3 }}
                        >
                          {new Date(m.created_at).toLocaleTimeString()}
                        </Typography>
                      </Box>
                    </Box>
                  );
                })}
                <div ref={messagesEndRef} />
              </Box>

              <Box
                component="form"
                onSubmit={handleSend}
                sx={{
                  p: 2,
                  borderTop: "1px solid",
                  borderColor: "divider",
                  display: "flex",
                  gap: 1,
                }}
              >
                <TextField
                  fullWidth
                  size="small"
                  placeholder="Type a message…"
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  autoComplete="off"
                />
                <Button
                  type="submit"
                  variant="contained"
                  disabled={sending || !body.trim()}
                  endIcon={<SendIcon />}
                >
                  Send
                </Button>
              </Box>
            </>
          )}
        </Card>
      </Box>
    </Box>
  );
}
