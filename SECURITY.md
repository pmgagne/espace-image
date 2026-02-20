# Security Considerations

## Deployment Model

**This application is designed for internal-network-only deployment.**

It has **NO built-in authentication or authorization** and is intended for use on a trusted internal network.

### Current Deployment (Internal Network)

✅ **Recommended**: Deploy on a trusted internal network (home network, private office network)

- No internet exposure
- Access restricted to devices on the same network
- Suitable for personal/family use

### Future LAN Deployment (If Needed)

If you need to expose this to a broader LAN or remote access:

**Option A: Reverse Proxy with HTTP Basic Auth** (Recommended)

Use nginx, Apache, or Caddy:

```nginx
server {
    listen 80;
    server_name espace-image.local;

    location /admin {
        auth_basic "Admin Area";
        auth_basic_user_file /etc/nginx/.htpasswd;
        proxy_pass http://localhost:8000/admin;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
    }
}
```

Create password file: `htpasswd -c /etc/nginx/.htpasswd admin`

#### Option B: VPN Access

Provide remote access via VPN (Tailscale, WireGuard, etc.) while keeping the app on internal network.

## Security Features

The application implements defense-in-depth security:

- **Security headers**: X-Content-Type-Options, X-Frame-Options, Referrer-Policy, X-XSS-Protection
- **File upload validation**: Restricted to image extensions (.jpg, .jpeg, .png, .heic, .heif) with magic byte validation
- **XSS protection**: HTML escaping in alarm rendering to prevent malicious calendar summaries
- **Path traversal protection**: Canonical path validation in image serving
- **SSRF protection**: URL scheme validation for calendar sources (only http, https, webcal allowed)
- **Rate limiting**: External API calls (Open-Meteo, Nominatim) are rate-limited
- **UTC time storage**: All timestamps in UTC to prevent timezone manipulation
- **SQLModel ORM**: Parameterized queries prevent SQL injection
- **Input validation**: UID format validation, coordinate validation (including NaN/Infinity checks)
- **Debug endpoint protection**: Debug routes only accessible when WEBAPP_DEBUG=true
- **Error message sanitization**: Sensitive information masked in displayed error messages
- **Race condition handling**: Proper error handling in concurrent sync operations

## Known Limitations

1. **No authentication** - Acceptable for internal-network deployment
2. **No CSRF tokens** - Would be needed if cookie-based auth is added
3. **Image validation scope** - Extension + magic byte checking; no deep content scan
4. **Single-user/family focused** - Not designed for multi-tenant scenarios
5. **In-memory rate limiting** - Per-process only (use Redis for multi-worker)

## Configuration

See [.env.example](.env.example) for all configuration options.

## Threat Model

**Assumed trusted environment:**

- All users on the network are trusted
- Network is isolated from the internet (or behind firewall)
- Physical security of the hosting device

**Out of scope:**

- Protection against malicious LAN users
- DDoS protection
- Multi-tenant isolation

**If threat model changes** (e.g., internet exposure), implement authentication via reverse proxy.
