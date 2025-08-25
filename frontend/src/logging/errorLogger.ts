import axios from "axios";

interface LogEntry {
  level: "ERROR" | "WARNING" | "INFO" | "DEBUG";
  message: string;
  error_type?: string;
  stack_trace?: string;
  url?: string;
  timestamp?: string;
  user_agent?: string;
  extra?: Record<string, any>;
}

class ErrorLogger {
  private apiEndpoint: string;
  private sessionId: string;
  private correlationId: string | null = null;

  constructor() {
    this.apiEndpoint = `${import.meta.env.VITE_API_URL || "http://localhost:8080"}/api/logs`;
    this.sessionId = this.generateSessionId();
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateCorrelationId(): string {
    return `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
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
        user_agent: navigator.userAgent,
      };

      await axios.post(this.apiEndpoint, logData, {
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": this.sessionId,
          "X-Correlation-ID": this.getCorrelationId(),
        },
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
      error_type: error?.name || "UnknownError",
      stack_trace: error?.stack,
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
      error_type: "APIError",
      extra: {
        endpoint,
        status,
        statusText,
        response_data: data,
        correlation_id: correlationId || this.getCorrelationId(),
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
