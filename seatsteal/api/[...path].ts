/* eslint-env node */
import type { IncomingMessage, ServerResponse } from "http";

type ApiRequest = IncomingMessage & {
  body?: unknown;
};

const isVercelPreview = (): boolean => process.env.VERCEL_ENV === "preview";

const sanitizeBranchName = (branch: string): string =>
  branch.toLowerCase().replace(/[^a-z0-9-]/g, "-");

const getApiBaseUrl = (): string => {
  const branch = process.env.VERCEL_GIT_COMMIT_REF;

  if (isVercelPreview() && branch) {
    const sanitizedBranch = sanitizeBranchName(branch);
    return `https://seatsteal-backend-git-${sanitizedBranch}-seatsteal.vercel.app`;
  }

  return (
    process.env.API_BASE_URL || process.env.VITE_API_BASE_URL || "http://localhost:5000"
  );
};

const getVercelBypassSecret = (): string | undefined => {
  if (isVercelPreview()) {
    return process.env.VERCEL_AUTOMATION_BYPASS_SECRET;
  }

  return undefined;
};

const shouldIncludeBody = (method?: string): boolean => {
  if (!method) return false;
  return !["GET", "HEAD"].includes(method);
};

const readRequestBody = async (req: ApiRequest): Promise<Buffer | undefined> => {
  if (!shouldIncludeBody(req.method)) {
    return undefined;
  }

  if (req.body !== undefined) {
    if (typeof req.body === "string" || Buffer.isBuffer(req.body)) {
      return Buffer.isBuffer(req.body) ? req.body : Buffer.from(req.body);
    }

    return Buffer.from(JSON.stringify(req.body));
  }

  const chunks: Buffer[] = [];

  for await (const chunk of req) {
    chunks.push(typeof chunk === "string" ? Buffer.from(chunk) : chunk);
  }

  if (chunks.length === 0) {
    return undefined;
  }

  return Buffer.concat(chunks);
};

function buildForwardHeaders(
  headers: ApiRequest["headers"],
  bypassSecret?: string,
): Headers {
  const forwardHeaders = new Headers();

  Object.entries(headers).forEach(([key, value]) => {
    if (!value) return;

    if (Array.isArray(value)) {
      value.forEach((val) => forwardHeaders.append(key, val));
      return;
    }

    forwardHeaders.set(key, value);
  });

  if (bypassSecret) {
    forwardHeaders.set("x-vercel-protection-bypass", bypassSecret);
  }

  return forwardHeaders;
}

function forwardSetCookieHeaders(res: ServerResponse, response: Response) {
  const setCookieHeader = response.headers.get("set-cookie");

  if (!setCookieHeader) {
    return;
  }

  const existing = res.getHeader("set-cookie");

  if (existing) {
    const cookies = Array.isArray(existing)
      ? existing
      : [existing.toString()];
    res.setHeader("set-cookie", [...cookies, setCookieHeader]);
  } else {
    res.setHeader("set-cookie", setCookieHeader);
  }
}

export default async function handler(req: ApiRequest, res: ServerResponse) {
  try {
    const baseUrl = getApiBaseUrl();
    const targetUrl = new URL(req.url || "", baseUrl);

    const body = await readRequestBody(req);
    const bypassSecret = getVercelBypassSecret();
    const headers = buildForwardHeaders(req.headers, bypassSecret);

    const upstreamResponse = await fetch(targetUrl, {
      method: req.method,
      headers,
      body,
      redirect: "manual",
    });

    res.statusCode = upstreamResponse.status;
    upstreamResponse.headers.forEach((value, key) => {
      if (key.toLowerCase() === "set-cookie") {
        return;
      }

      res.setHeader(key, value);
    });

    forwardSetCookieHeaders(res, upstreamResponse);

    const responseBuffer = Buffer.from(await upstreamResponse.arrayBuffer());
    res.end(responseBuffer);
  } catch (error) {
    console.error("API proxy error", error);
    res.statusCode = 502;
    res.end("Upstream proxy error");
  }
}
