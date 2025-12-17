import { useEffect, useRef, useState, useCallback } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { WebLinksAddon } from "@xterm/addon-web-links";
import "@xterm/xterm/css/xterm.css";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ArrowUp,
  ArrowDown,
  CornerDownLeft,
  Play,
  RefreshCw,
  Square,
  Terminal as TerminalIcon,
} from "lucide-react";
import { config } from "@/lib/config";
import { supabase } from "@/lib/supabase";

export function TerminalClient() {
  const terminalRef = useRef<HTMLDivElement>(null);
  const terminal = useRef<Terminal | null>(null);
  const fitAddon = useRef<FitAddon | null>(null);
  const ws = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getWebSocketUrl = useCallback(async () => {
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session?.access_token) {
      throw new Error("Not authenticated");
    }

    // Convert HTTP URL to WebSocket URL
    let wsBaseUrl = config.api.baseUrl
      .replace("https://", "wss://")
      .replace("http://", "ws://");

    let wsUrl = `${wsBaseUrl}/api/admin/terminal?token=${encodeURIComponent(session.access_token)}`;

    // Add Vercel bypass secret if present
    if (config.api.vercelBypassSecret) {
      wsUrl += `&x-vercel-protection-bypass=${config.api.vercelBypassSecret}`;
    }

    return wsUrl;
  }, []);

  const connect = useCallback(async () => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setIsConnecting(true);
    setError(null);

    try {
      const wsUrl = await getWebSocketUrl();

      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        setIsConnected(true);
        setIsConnecting(false);
        terminal.current?.focus();
      };

      ws.current.onmessage = (event) => {
        if (event.data instanceof Blob) {
          event.data.text().then((text: string) => {
            terminal.current?.write(text);
          });
        } else if (typeof event.data === "string") {
          terminal.current?.write(event.data);
        } else if (event.data instanceof ArrayBuffer) {
          const decoder = new TextDecoder();
          terminal.current?.write(decoder.decode(event.data));
        }
      };

      ws.current.onclose = (event) => {
        setIsConnected(false);
        setIsConnecting(false);
        if (event.code === 4001) {
          setError("Unauthorized - admin access required");
        } else if (event.code !== 1000) {
          setError(`Connection closed (code: ${event.code})`);
        }
      };

      ws.current.onerror = () => {
        setIsConnected(false);
        setIsConnecting(false);
        setError("WebSocket connection failed");
      };
    } catch (err) {
      setIsConnecting(false);
      setError(err instanceof Error ? err.message : "Failed to connect");
    }
  }, [getWebSocketUrl]);

  const disconnect = useCallback(() => {
    if (ws.current) {
      ws.current.close(1000, "User disconnected");
      ws.current = null;
    }
    setIsConnected(false);
  }, []);

  const sendInput = useCallback((input: string) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(input);
    }
  }, []);

  const sendResize = useCallback((rows: number, cols: number) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: "resize", rows, cols }));
    }
  }, []);

  // Initialize terminal
  useEffect(() => {
    if (!terminalRef.current || terminal.current) return;

    terminal.current = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      theme: {
        background: "#1e1e2e",
        foreground: "#cdd6f4",
        cursor: "#f5e0dc",
        cursorAccent: "#1e1e2e",
        black: "#45475a",
        red: "#f38ba8",
        green: "#a6e3a1",
        yellow: "#f9e2af",
        blue: "#89b4fa",
        magenta: "#f5c2e7",
        cyan: "#94e2d5",
        white: "#bac2de",
        brightBlack: "#585b70",
        brightRed: "#f38ba8",
        brightGreen: "#a6e3a1",
        brightYellow: "#f9e2af",
        brightBlue: "#89b4fa",
        brightMagenta: "#f5c2e7",
        brightCyan: "#94e2d5",
        brightWhite: "#a6adc8",
      },
      scrollback: 10000,
      convertEol: true,
    });

    fitAddon.current = new FitAddon();
    terminal.current.loadAddon(fitAddon.current);
    terminal.current.loadAddon(new WebLinksAddon());

    terminal.current.open(terminalRef.current);
    fitAddon.current.fit();

    // Handle terminal input
    terminal.current.onData((data) => {
      sendInput(data);
    });

    // Handle resize
    const handleResize = () => {
      if (fitAddon.current && terminal.current) {
        fitAddon.current.fit();
        sendResize(terminal.current.rows, terminal.current.cols);
      }
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      terminal.current?.dispose();
      terminal.current = null;
      disconnect();
    };
  }, [sendInput, sendResize, disconnect]);

  // Auto-connect on mount
  useEffect(() => {
    connect();
  }, [connect]);

  // Send up arrow
  const sendUp = useCallback(() => {
    sendInput("\x1b[A");
  }, [sendInput]);

  // Send down arrow
  const sendDown = useCallback(() => {
    sendInput("\x1b[B");
  }, [sendInput]);

  // Send enter
  const sendEnter = useCallback(() => {
    sendInput("\r");
  }, [sendInput]);

  // Send manage.sh command
  const sendManageCommand = useCallback(() => {
    sendInput("./manage.sh\r");
  }, [sendInput]);

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Terminal
        </h1>
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
              isConnected
                ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                : isConnecting
                  ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400"
                  : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
            }`}
          >
            {isConnected
              ? "Connected"
              : isConnecting
                ? "Connecting..."
                : "Disconnected"}
          </span>
          {isConnected ? (
            <Button variant="outline" size="sm" onClick={disconnect}>
              <Square className="h-4 w-4 mr-2" />
              Disconnect
            </Button>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={connect}
              disabled={isConnecting}
            >
              <RefreshCw
                className={`h-4 w-4 mr-2 ${isConnecting ? "animate-spin" : ""}`}
              />
              {isConnecting ? "Connecting..." : "Reconnect"}
            </Button>
          )}
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
        </div>
      )}

      {/* Mobile control buttons */}
      <Card>
        <CardHeader className="py-3">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <TerminalIcon className="h-4 w-4" />
            Navigation Controls
          </CardTitle>
        </CardHeader>
        <CardContent className="py-3">
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="lg"
              onClick={sendUp}
              disabled={!isConnected}
              className="flex-1 min-w-[80px]"
            >
              <ArrowUp className="h-5 w-5 mr-1" />
              Up
            </Button>
            <Button
              variant="outline"
              size="lg"
              onClick={sendDown}
              disabled={!isConnected}
              className="flex-1 min-w-[80px]"
            >
              <ArrowDown className="h-5 w-5 mr-1" />
              Down
            </Button>
            <Button
              variant="default"
              size="lg"
              onClick={sendEnter}
              disabled={!isConnected}
              className="flex-1 min-w-[80px]"
            >
              <CornerDownLeft className="h-5 w-5 mr-1" />
              Enter
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Terminal container */}
      <Card className="overflow-hidden">
        <CardContent className="p-0">
          <div
            ref={terminalRef}
            className="w-full"
            style={{ height: "calc(100vh - 380px)", minHeight: "300px" }}
          />
        </CardContent>
      </Card>

      {/* Quick command button */}
      <Card>
        <CardContent className="py-3">
          <Button
            variant="default"
            size="lg"
            onClick={sendManageCommand}
            disabled={!isConnected}
            className="w-full"
          >
            <Play className="h-5 w-5 mr-2" />
            Run ./manage.sh
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
