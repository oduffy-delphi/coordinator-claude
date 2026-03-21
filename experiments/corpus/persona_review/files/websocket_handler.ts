/**
 * WebSocket connection manager for real-time notification delivery.
 * Handles connection lifecycle, heartbeats, room-based broadcasting,
 * and graceful reconnection.
 */

interface ClientConnection {
  id: string;
  socket: WebSocket;
  rooms: Set<string>;
  lastHeartbeat: number;
  metadata: Record<string, unknown>;
  heartbeatTimer?: ReturnType<typeof setInterval>;
}

interface BroadcastMessage {
  type: string;
  payload: unknown;
  timestamp: number;
  sender?: string;
}

const HEARTBEAT_INTERVAL_MS = 30_000;
const HEARTBEAT_TIMEOUT_MS = 45_000;
const MAX_CONNECTIONS_PER_ROOM = 10_000;

class ConnectionManager {
  private connections = new Map<string, ClientConnection>();
  private rooms = new Map<string, Set<string>>();
  private messageHandlers = new Map<string, (conn: ClientConnection, data: unknown) => void>();

  /**
   * Register a new client connection.
   */
  connect(id: string, socket: WebSocket, metadata: Record<string, unknown> = {}): ClientConnection {
    if (this.connections.has(id)) {
      this.disconnect(id);
    }

    const conn: ClientConnection = {
      id,
      socket,
      rooms: new Set(),
      lastHeartbeat: Date.now(),
      metadata,
    };

    // Set up heartbeat monitoring
    conn.heartbeatTimer = setInterval(() => {
      const elapsed = Date.now() - conn.lastHeartbeat;
      if (elapsed > HEARTBEAT_TIMEOUT_MS) {
        console.warn(`Client ${id} heartbeat timeout, disconnecting`);
        this.disconnect(id);
      } else {
        this.send(id, { type: "ping", payload: null, timestamp: Date.now() });
      }
    }, HEARTBEAT_INTERVAL_MS);

    socket.onmessage = (event) => this.handleMessage(conn, event);
    socket.onclose = () => this.handleClose(conn);

    this.connections.set(id, conn);
    return conn;
  }

  /**
   * Disconnect a client and clean up all associated state.
   */
  disconnect(id: string): void {
    const conn = this.connections.get(id);
    if (!conn) return;

    // Leave all rooms
    for (const room of conn.rooms) {
      this.leaveRoom(id, room);
    }

    try {
      conn.socket.close();
    } catch {
      // Socket may already be closed
    }

    this.connections.delete(id);
  }

  /**
   * Join a client to a named room for targeted broadcasting.
   */
  joinRoom(clientId: string, room: string): boolean {
    const conn = this.connections.get(clientId);
    if (!conn) return false;

    let roomMembers = this.rooms.get(room);
    if (!roomMembers) {
      roomMembers = new Set();
      this.rooms.set(room, roomMembers);
    }

    if (roomMembers.size >= MAX_CONNECTIONS_PER_ROOM) {
      return false;
    }

    roomMembers.add(clientId);
    conn.rooms.add(room);
    return true;
  }

  /**
   * Remove a client from a room.
   */
  leaveRoom(clientId: string, room: string): void {
    const conn = this.connections.get(clientId);
    if (conn) {
      conn.rooms.delete(room);
    }

    const roomMembers = this.rooms.get(room);
    if (roomMembers) {
      roomMembers.delete(clientId);
      if (roomMembers.size === 0) {
        this.rooms.delete(room);
      }
    }
  }

  /**
   * Send a message to a specific client by ID.
   */
  send(clientId: string, message: BroadcastMessage): boolean {
    const conn = this.connections.get(clientId);
    if (!conn || conn.socket.readyState !== WebSocket.OPEN) {
      return false;
    }

    conn.socket.send(JSON.stringify(message));
    return true;
  }

  /**
   * Broadcast a message to all clients in a room.
   * Optionally exclude a sender to avoid echo.
   */
  broadcastToRoom(
    room: string,
    message: BroadcastMessage,
    excludeSender?: string
  ): number {
    const roomMembers = this.rooms.get(room);
    if (!roomMembers) return 0;

    let sent = 0;
    for (const clientId of roomMembers) {
      if (clientId === excludeSender) continue;
      if (this.send(clientId, message)) {
        sent++;
      }
    }
    return sent;
  }

  /**
   * Broadcast a message to ALL connected clients.
   */
  broadcastAll(message: BroadcastMessage): number {
    let sent = 0;
    const allConnections = Array.from(this.connections.values());
    for (const conn of allConnections) {
      const serialized = JSON.stringify(message);
      if (conn.socket.readyState === WebSocket.OPEN) {
        conn.socket.send(serialized);
        sent++;
      }
    }
    return sent;
  }

  /**
   * Register a handler for a specific message type.
   */
  on(type: string, handler: (conn: ClientConnection, data: unknown) => void): void {
    this.messageHandlers.set(type, handler);
  }

  /**
   * Handle an incoming WebSocket message.
   */
  private handleMessage(conn: ClientConnection, event: MessageEvent): void {
    let parsed: { type: string; data?: unknown };
    try {
      parsed = JSON.parse(event.data as string);
    } catch {
      console.warn(`Invalid JSON from client ${conn.id}`);
      return;
    }

    if (parsed.type === "pong") {
      conn.lastHeartbeat = Date.now();
      return;
    }

    const handler = this.messageHandlers.get(parsed.type);
    if (handler) {
      handler(conn, parsed.data);
    }
  }

  /**
   * Handle WebSocket close event.
   */
  private handleClose(conn: ClientConnection): void {
    // Remove from all rooms
    for (const room of conn.rooms) {
      const roomMembers = this.rooms.get(room);
      if (roomMembers) {
        roomMembers.delete(conn.id);
        if (roomMembers.size === 0) {
          this.rooms.delete(room);
        }
      }
    }
    this.connections.delete(conn.id);
  }

  /**
   * Get the number of active connections.
   */
  get connectionCount(): number {
    return this.connections.size;
  }

  /**
   * Get the number of clients in a specific room.
   */
  getRoomSize(room: string): number {
    return this.rooms.get(room)?.size ?? 0;
  }

  /**
   * List all rooms and their member counts.
   */
  listRooms(): Array<{ room: string; members: number }> {
    return Array.from(this.rooms.entries()).map(([room, members]) => ({
      room,
      members: members.size,
    }));
  }
}

export { ConnectionManager };
export type { ClientConnection, BroadcastMessage };
