import { Router } from "express";
import http from "http";

const router = Router();

// Proxy fingerprint requests to Python bot's internal web server (port 8082)
router.post("/fingerprint", async (req, res) => {
  try {
    const body = JSON.stringify(req.body);

    const result = await new Promise<{ status: number; data: string }>(
      (resolve, reject) => {
        const options = {
          hostname: "localhost",
          port: 8082,
          path: "/fingerprint",
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Content-Length": Buffer.byteLength(body),
          },
        };

        const proxyReq = http.request(options, (proxyRes) => {
          let data = "";
          proxyRes.on("data", (chunk) => (data += chunk));
          proxyRes.on("end", () =>
            resolve({ status: proxyRes.statusCode ?? 200, data })
          );
        });

        proxyReq.on("error", reject);
        proxyReq.write(body);
        proxyReq.end();
      }
    );

    res.status(result.status).set("Content-Type", "application/json").send(result.data);
  } catch (err) {
    res.status(503).json({ ok: false, reason: "bot_unavailable" });
  }
});

export default router;
