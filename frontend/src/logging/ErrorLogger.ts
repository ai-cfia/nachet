import axios from "axios";
import { v7 as uuidv7 } from "uuid";

interface LogEntry {
  level: "ERROR" | "WARNING" | "INFO" | "DEBUG";
  message: string;
  errorType?: string;
  stackTrace?: string;
  url?: string;
  timestamp?: string;
  userAgent?: string;
  extra?: Record<string, any>;
}

type TokenProvider = () => Promise<string | null>;

class ErrorLogger {
  private apiEndpoint: string;
  private sessionId: string;
  private correlationId: string | null = null;
  private tokenProvider: TokenProvider | null = null;

  constructor(tokenProvider?: TokenProvider) {
    this.apiEndpoint = `${import.meta.env.VITE_LOG_API_URL || "http://localhost:8080"}`;
    this.sessionId = this.generateSessionId();
    this.tokenProvider = tokenProvider || null;
  }

  public setTokenProvider(tokenProvider: TokenProvider): void {
    this.tokenProvider = tokenProvider;
  }

  private generateSessionId(): string {
    // Use UUIDv7 for time-ordered session IDs
    return uuidv7();
  }

  private generateCorrelationId(): string {
    // Use UUIDv7 for time-ordered correlation IDs
    return uuidv7();
  }

  public setCorrelationId(id: string): void {
    this.correlationId = id;
  }

  public getSessionId(): string {
    return this.sessionId;
  }

  public getCorrelationId(): string {
    if (!this.correlationId) {
      this.correlationId = this.generateCorrelationId();
    }
    return this.correlationId;
  }

  private async sendLog(entry: LogEntry): Promise<void> {
    try {
      const logData = {
        ...entry,
        url: entry.url || window.location.href,
        timestamp: entry.timestamp || new Date().toISOString(),
        userAgent: navigator.userAgent,
      };

      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        "X-Session-ID": this.sessionId,
        "X-Correlation-ID": this.getCorrelationId(),
      };

      // Try to get access token if token provider is available
      if (this.tokenProvider) {
        try {
          const token = await this.tokenProvider();
          if (token) {
            headers["Authorization"] = `Bearer ${token}`;
          }
        } catch (tokenError) {
          // Log token acquisition failure but continue without auth
          console.warn(
            "Failed to acquire token for logs endpoint:",
            tokenError,
          );
        }
      }

      await axios.post(this.apiEndpoint, logData, {
        headers,
        withCredentials: true,
      });
    } catch (error) {
      // Fallback to console if logging endpoint fails
      console.error("Failed to send log to server:", error);
      console.error("Original log entry:", entry);
    }
  }

  public async logError(
    message: string,
    error?: Error,
    extra?: Record<string, any>,
  ): Promise<void> {
    const entry: LogEntry = {
      level: "ERROR",
      message,
      errorType: error?.name || "UnknownError",
      stackTrace: error?.stack,
      extra,
    };

    // Always log to console for debugging
    console.error(message, error, extra);

    // Send to backend
    await this.sendLog(entry);
  }

  public async logWarning(
    message: string,
    extra?: Record<string, any>,
  ): Promise<void> {
    const entry: LogEntry = {
      level: "WARNING",
      message,
      extra,
    };

    console.warn(message, extra);
    await this.sendLog(entry);
  }

  public async logInfo(
    message: string,
    extra?: Record<string, any>,
  ): Promise<void> {
    const entry: LogEntry = {
      level: "INFO",
      message,
      extra,
    };

    console.info(message, extra);
    await this.sendLog(entry);
  }

  public async logApiError(
    endpoint: string,
    status: number,
    statusText: string,
    data?: any,
    correlationId?: string,
  ): Promise<void> {
    const entry: LogEntry = {
      level: "ERROR",
      message: `API Error: ${endpoint} returned ${status} ${statusText}`,
      errorType: "APIError",
      extra: {
        endpoint,
        status,
        statusText,
        responseData: data,
        correlationId: correlationId || this.getCorrelationId(),
      },
    };

    await this.sendLog(entry);
  }

  // Log unhandled promise rejections
  public setupGlobalHandlers(): void {
    window.addEventListener("unhandledrejection", (event) => {
      this.logError(
        `Unhandled Promise Rejection: ${event.reason}`,
        event.reason instanceof Error
          ? event.reason
          : new Error(String(event.reason)),
        { promise: event.promise },
      );
    });

    window.addEventListener("error", (event) => {
      this.logError(`Uncaught Error: ${event.message}`, event.error, {
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
      });
    });
  }
}

// Create singleton instance
const errorLogger = new ErrorLogger();

// Setup global handlers
if (typeof window !== "undefined") {
  errorLogger.setupGlobalHandlers();
}

export default errorLogger;
