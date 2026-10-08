import { useState, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import {
  AppBar,
  Box,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  Avatar,
  Menu,
  MenuItem,
  Divider,
} from "@mui/material";

import DashboardIcon from "@mui/icons-material/Dashboard";
import FolderIcon from "@mui/icons-material/Folder";
import ViewKanbanIcon from "@mui/icons-material/ViewKanban";
import ChatIcon from "@mui/icons-material/Chat";
import MenuIcon from "@mui/icons-material/Menu";
import LogoutIcon from "@mui/icons-material/Logout";

import { useAuthStore } from "../store";

const DRAWER_WIDTH = 240;

const navItems = [
  {
    label: "Dashboard",
    path: "/",
    icon: <DashboardIcon />,
  },
  {
    label: "Projects",
    path: "/projects",
    icon: <FolderIcon />,
  },
  {
    label: "Task Board",
    path: "/org/1/project/1/board",
    icon: <ViewKanbanIcon />,
  },
  {
    label: "Chat",
    path: "/chat",
    icon: <ChatIcon />,
  },
];

export default function AppLayout({ children }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState(null);

  const { user, logout, accessToken } = useAuthStore();

  const location = useLocation();
  const navigate = useNavigate();

  // -------------------------------------------------
  // Notification WebSocket
  // -------------------------------------------------

  useEffect(() => {
    if (!accessToken) {
      return;
    }

    const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

    const WS_URL = API_URL.replace(/^http:/, "ws:").replace(/^https:/, "wss:");

    const ws = new WebSocket(
      `${WS_URL}/api/v1/ws/notifications?token=${accessToken}`,
    );

    ws.onopen = () => {
      console.log("Notification WebSocket connected");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        console.log("Notification received:", data);

        if (data.type === "notification") {
          // Temporary test
          alert(data.title);
        }
      } catch (error) {
        console.error("Notification WebSocket message error:", error);
      }
    };

    ws.onerror = (error) => {
      console.error("Notification WebSocket error:", error);
    };

    ws.onclose = () => {
      console.log("Notification WebSocket disconnected");
    };

    // Close WebSocket when component unmounts
    // or accessToken changes.
    return () => {
      ws.close();
    };
  }, [accessToken]);

  // -------------------------------------------------
  // Logout
  // -------------------------------------------------

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  // -------------------------------------------------
  // Sidebar
  // -------------------------------------------------

  const drawer = (
    <Box>
      <Toolbar>
        <Typography
          variant="h6"
          noWrap
          sx={{
            fontWeight: 700,
            color: "primary.main",
          }}
        >
          ProjectHub
        </Typography>
      </Toolbar>

      <Divider />

      <List>
        {navItems.map((item) => (
          <ListItemButton
            key={item.path}
            component={Link}
            to={item.path}
            selected={location.pathname === item.path}
            onClick={() => setMobileOpen(false)}
          >
            <ListItemIcon
              sx={{
                color: "inherit",
              }}
            >
              {item.icon}
            </ListItemIcon>

            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>
    </Box>
  );

  // -------------------------------------------------
  // UI
  // -------------------------------------------------

  return (
    <Box
      sx={{
        display: "flex",
        minHeight: "100vh",
      }}
    >
      <AppBar
        position="fixed"
        sx={{
          zIndex: (t) => t.zIndex.drawer + 1,
          background: "#020617",
          borderBottom: "1px solid #1e293b",
        }}
        elevation={0}
      >
        <Toolbar>
          {/* Mobile menu */}

          <IconButton
            color="inherit"
            edge="start"
            onClick={() => setMobileOpen(!mobileOpen)}
            sx={{
              mr: 2,
              display: {
                sm: "none",
              },
            }}
          >
            <MenuIcon />
          </IconButton>

          {/* Header title */}

          <Typography
            variant="h6"
            noWrap
            sx={{
              flexGrow: 1,
              display: {
                xs: "none",
                sm: "block",
              },
            }}
          >
            Multi-Tenant Project Platform
          </Typography>

          {/* User menu */}

          <IconButton onClick={(e) => setAnchorEl(e.currentTarget)}>
            <Avatar
              sx={{
                width: 36,
                height: 36,
                bgcolor: "primary.main",
                fontSize: 14,
              }}
            >
              {(user?.full_name || user?.email || "U")[0].toUpperCase()}
            </Avatar>
          </IconButton>

          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={() => setAnchorEl(null)}
          >
            <MenuItem disabled>
              <Typography variant="body2">
                {user?.full_name || user?.email}
              </Typography>
            </MenuItem>

            <Divider />

            <MenuItem onClick={handleLogout}>
              <ListItemIcon>
                <LogoutIcon fontSize="small" />
              </ListItemIcon>
              Logout
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      {/* Sidebar */}

      <Box
        component="nav"
        sx={{
          width: {
            sm: DRAWER_WIDTH,
          },
          flexShrink: {
            sm: 0,
          },
        }}
      >
        {/* Mobile drawer */}

        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{
            keepMounted: true,
          }}
          sx={{
            display: {
              xs: "block",
              sm: "none",
            },
            "& .MuiDrawer-paper": {
              width: DRAWER_WIDTH,
              background: "#020617",
            },
          }}
        >
          {drawer}
        </Drawer>

        {/* Desktop drawer */}

        <Drawer
          variant="permanent"
          sx={{
            display: {
              xs: "none",
              sm: "block",
            },
            "& .MuiDrawer-paper": {
              width: DRAWER_WIDTH,
              background: "#020617",
              borderRight: "1px solid #1e293b",
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      {/* Main content */}

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: {
            sm: `calc(100% - ${DRAWER_WIDTH}px)`,
          },
          mt: 8,
        }}
      >
        {children}
      </Box>
    </Box>
  );
}
