import { type ChildProcess, spawn } from "node:child_process";
import { createServer } from "node:net";

export async function pickPort(): Promise<number> {
  return await new Promise<number>((res, rej) => {
    const srv = createServer();
    srv.unref();
    srv.on("error", rej);
    srv.listen(0, "127.0.0.1", () => {
      const port = (srv.address() as { port: number }).port;
      srv.close(() => res(port));
    });
  });
}

export interface EphemeralSurreal {
  url: string;
  stop: () => Promise<void>;
}

export async function startSurreal(): Promise<EphemeralSurreal> {
  const port = await pickPort();
  const proc: ChildProcess = spawn(
    "surreal",
    [
      "start",
      "--user",
      "root",
      "--pass",
      "root",
      "--bind",
      `127.0.0.1:${port}`,
      "memory",
    ],
    { stdio: "ignore" },
  );

  const url = `ws://127.0.0.1:${port}/rpc`;
  const httpUrl = `http://127.0.0.1:${port}/health`;
  const deadline = Date.now() + 10000;
  while (Date.now() < deadline) {
    try {
      const resp = await fetch(httpUrl);
      if (resp.ok) break;
    } catch {
      // not ready
    }
    await new Promise((r) => setTimeout(r, 100));
  }

  return {
    url,
    stop: async () => {
      proc.kill("SIGTERM");
      await new Promise<void>((r) => proc.on("close", () => r()));
    },
  };
}
