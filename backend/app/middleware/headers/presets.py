PRESETS = {
    "strict": {
        "Content-Security-Policy": "default-src 'self';",
        "X-Frame-Options": "DENY",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "accelerometer=(), autoplay=(), camera=(self), clipboard-read=(self), clipboard-write=(self), cross-origin-isolated=(), display-capture=(), encrypted-media=(), fullscreen=(), gamepad=(), geolocation=(), gyroscope=(), hid=(), idle-detection=(), interest-cohort=(), keyboard-map=(), magnetometer=(), microphone=(), midi=(), payment=(), picture-in-picture=(), publickey-credentials-get=(), screen-wake-lock=(), serial=(), sync-xhr=(), unload=(), usb=(), web-share=(), xr-spatial-tracking=()",
        "X-DNS-Prefetch-Control": "off",
        "Expect-CT": "max-age=86400, enforce",
        "Origin-Agent-Cluster": "?1",
        "Cross-Origin-Embedder-Policy": "require-corp",
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Resource-Policy": "same-origin",
        "X-Permitted-Cross-Domain-Policies": "none",
        "Cache-Control": "private, max-age=3600",
    },
    "relaxed": {
        "Content-Security-Policy": "default-src *;",
        "X-Frame-Options": "SAMEORIGIN",
        "Strict-Transport-Security": "max-age=86400",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    },
    "none": {},
}

# clear site data only add to logout         "Clear-Site-Data": "\"cache\",\"cookies\",\"storage\"",
