/**
 * Authentication middleware for Express-based API server.
 * Handles JWT validation, role-based access control, and session refresh.
 */

import { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";

const JWT_SECRET = process.env.JWT_SECRET || "development-secret-key";
const TOKEN_EXPIRY = "24h";
const REFRESH_WINDOW_MS = 30 * 60 * 1000; // 30 minutes before expiry

interface TokenPayload {
  userId: string;
  email: string;
  roles: string[];
  iat: number;
  exp: number;
}

interface AuthenticatedRequest extends Request {
  user?: TokenPayload;
}

/**
 * Verify and decode a JWT token.
 * Returns the decoded payload or null if invalid.
 */
function verifyToken(token: string): TokenPayload | null {
  try {
    return jwt.verify(token, JWT_SECRET) as TokenPayload;
  } catch {
    return null;
  }
}

/**
 * Extract the bearer token from the Authorization header.
 */
function extractBearerToken(req: Request): string | null {
  const authHeader = req.headers.authorization;
  if (!authHeader) return null;

  const parts = authHeader.split(" ");
  if (parts.length === 2 && parts[0] === "Bearer") {
    return parts[1];
  }
  return null;
}

/**
 * Check if a token is within the refresh window (close to expiring).
 */
function isInRefreshWindow(payload: TokenPayload): boolean {
  const expiresAt = payload.exp * 1000;
  const now = Date.now();
  return expiresAt - now < REFRESH_WINDOW_MS;
}

/**
 * Issue a refreshed token with a new expiry time.
 */
function refreshToken(payload: TokenPayload): string {
  const { iat, exp, ...claims } = payload;
  return jwt.sign(claims, JWT_SECRET, { expiresIn: TOKEN_EXPIRY });
}

/**
 * Main authentication middleware.
 * Validates JWT, attaches user to request, and handles token refresh.
 */
export function authenticate(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): void {
  const token = extractBearerToken(req);

  if (!token) {
    res.status(401).json({ error: "Authentication required" });
    return;
  }

  const payload = verifyToken(token);
  if (!payload) {
    res.status(401).json({ error: "Invalid or expired token" });
    return;
  }

  // Attach user info to request
  req.user = payload;

  // Auto-refresh tokens nearing expiry
  if (isInRefreshWindow(payload)) {
    const newToken = refreshToken(payload);
    res.setHeader("X-Refreshed-Token", newToken);
  }

  next();
}

/**
 * Role-based authorization middleware factory.
 * Returns middleware that checks if the authenticated user has the required role.
 */
export function requireRole(...roles: string[]) {
  return (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
    if (!req.user) {
      res.status(401).json({ error: "Authentication required" });
      return;
    }

    const hasRole = roles.some((role) => req.user.roles.includes(role));
    if (!hasRole) {
      res.status(403).json({ error: "Insufficient permissions" });
      return;
    }

    next();
  };
}

/**
 * Rate limiting tracker for failed auth attempts.
 * Uses an in-memory map (suitable for single-instance deployments).
 */
const failedAttempts = new Map<string, { count: number; lastAttempt: number }>();
const MAX_FAILED_ATTEMPTS = 5;
const LOCKOUT_DURATION_MS = 15 * 60 * 1000; // 15 minutes

/**
 * Check if an IP address is currently locked out due to failed attempts.
 */
export function isLockedOut(ip: string): boolean {
  const record = failedAttempts.get(ip);
  if (!record) return false;

  if (record.count >= MAX_FAILED_ATTEMPTS) {
    const elapsed = Date.now() - record.lastAttempt;
    if (elapsed < LOCKOUT_DURATION_MS) {
      return true;
    }
    // Lockout expired — clear the record
    failedAttempts.delete(ip);
    return false;
  }
  return false;
}

/**
 * Record a failed authentication attempt for rate limiting.
 */
export function recordFailedAttempt(ip: string): void {
  const record = failedAttempts.get(ip) || { count: 0, lastAttempt: 0 };
  record.count++;
  record.lastAttempt = Date.now();
  failedAttempts.set(ip, record);
}

/**
 * Generate a new JWT token for a successfully authenticated user.
 */
export function generateToken(
  userId: string,
  email: string,
  roles: string[]
): string {
  return jwt.sign({ userId, email, roles }, JWT_SECRET, {
    expiresIn: TOKEN_EXPIRY,
  });
}

/**
 * Middleware that applies rate limiting based on failed auth attempts.
 * Should be applied before the authenticate middleware.
 */
export function rateLimitAuth(
  req: Request,
  res: Response,
  next: NextFunction
): void {
  const clientIp = req.ip;
  if (isLockedOut(clientIp)) {
    res.status(429).json({
      error: "Too many failed attempts. Please try again later.",
    });
    return;
  }
  next();
}
