/**
 * Netlify Function — Replicate API proxy.
 *
 * Why this exists: Replicate's API doesn't include CORS headers, so browsers
 * block direct calls from web pages with a "Failed to fetch" error. This
 * function sits on the Cosmos Netlify deployment and forwards requests on
 * behalf of the browser, returning the response with permissive CORS headers.
 *
 * Security:
 *  - The caller passes their own Replicate token in the X-Replicate-Token
 *    header. The function does NOT store or have its own token — there's
 *    no secret here. If someone else discovers this endpoint, they can only
 *    use it with their own (paid) Replicate account.
 *  - Whitelisted to api.replicate.com only — can't be used as a generic
 *    open proxy.
 *
 * Usage (from the browser):
 *   fetch('/.netlify/functions/replicate-proxy?path=/v1/models/.../predictions', {
 *     method: 'POST',
 *     headers: {
 *       'X-Replicate-Token': 'r8_...',
 *       'Content-Type': 'application/json',
 *       'Prefer': 'wait=60'
 *     },
 *     body: JSON.stringify({ input: { prompt: '...' } })
 *   })
 */

const REPLICATE_BASE = 'https://api.replicate.com';

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, X-Replicate-Token, Prefer',
  'Access-Control-Max-Age': '86400',
};

exports.handler = async (event) => {
  // CORS preflight
  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers: CORS_HEADERS, body: '' };
  }

  // Extract caller's Replicate token (headers are lowercased by Netlify)
  const token =
    event.headers['x-replicate-token'] ||
    event.headers['X-Replicate-Token'];
  if (!token) {
    return {
      statusCode: 401,
      headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: 'Missing X-Replicate-Token header' }),
    };
  }

  // Path to forward to — must start with /v1/ to limit scope
  const path = (event.queryStringParameters || {}).path || '';
  if (!path.startsWith('/v1/')) {
    return {
      statusCode: 400,
      headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: 'path must start with /v1/' }),
    };
  }

  const upstreamUrl = REPLICATE_BASE + path;
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  const prefer = event.headers['prefer'] || event.headers['Prefer'];
  if (prefer) headers['Prefer'] = prefer;

  try {
    const upstream = await fetch(upstreamUrl, {
      method: event.httpMethod,
      headers,
      body: event.httpMethod === 'GET' ? undefined : (event.body || undefined),
    });
    const text = await upstream.text();
    return {
      statusCode: upstream.status,
      headers: {
        ...CORS_HEADERS,
        'Content-Type': upstream.headers.get('content-type') || 'application/json',
      },
      body: text,
    };
  } catch (err) {
    return {
      statusCode: 502,
      headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: 'Proxy fetch failed: ' + err.message }),
    };
  }
};
