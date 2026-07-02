/**
 * Proxy /api/* on Vercel to the Render backend.
 * Required because outputDirectory: "dashboard" deploys static files only —
 * root /api serverless functions are not included in that deploy mode.
 */

export const config = {
  matcher: ["/api/:path*"],
};

function backendBase() {
  return (process.env.API_BASE_URL || process.env.RENDER_API_URL || "")
    .trim()
    .replace(/\/$/, "");
}

export default async function middleware(request) {
  const url = new URL(request.url);

  if (url.pathname === "/api/health-proxy") {
    const configured = Boolean(backendBase());
    return Response.json({
      proxy: "ok",
      backend_configured: configured,
      hint: configured
        ? "Proxy ready. Try /api/overview on your Vercel domain."
        : "Set API_BASE_URL in Vercel → Settings → Environment Variables, then redeploy.",
    });
  }

  const base = backendBase();
  if (!base) {
    return Response.json(
      {
        error: "API_BASE_URL is not configured on Vercel",
        hint:
          "Vercel → Project → Settings → Environment Variables → API_BASE_URL = https://your-app.onrender.com",
      },
      { status: 500 },
    );
  }

  const subpath = url.pathname.replace(/^\/api\/?/, "");
  const target = `${base}/api/${subpath}${url.search}`;

  const headers = new Headers(request.headers);
  headers.delete("host");

  try {
    return await fetch(target, {
      method: request.method,
      headers,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
    });
  } catch (error) {
    return Response.json(
      {
        error: "Could not reach Render API",
        target,
        detail: error instanceof Error ? error.message : String(error),
      },
      { status: 502 },
    );
  }
}
