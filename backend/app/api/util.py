from fastapi import APIRouter, Request

router = APIRouter(prefix="/util", tags=["util"])


def _extract_client_ip(request: Request) -> str:
    # Respect common proxy/CDN headers first
    headers = request.headers
    # Cloudflare
    ip = headers.get("cf-connecting-ip") or headers.get("CF-Connecting-IP")
    if ip:
        return ip
    # Standard reverse proxy header (may contain a list)
    xff = headers.get("x-forwarded-for") or headers.get("X-Forwarded-For")
    if xff:
        # Take the first IP in the list (original client)
        return xff.split(",")[0].strip()
    # Nginx/Heroku style
    ip = headers.get("x-real-ip") or headers.get("X-Real-IP")
    if ip:
        return ip
    # Fallback to connection peer
    return (request.client and request.client.host) or "unknown"


@router.get("/ip")
async def get_ip(request: Request):
    """Return the caller's public IP address as seen by the server."""
    ip = _extract_client_ip(request)
    return {"ip": ip}
