from typing import Optional
from hlmagic.utils.hardware import GPUVendor

def get_gpu_section(vendor: str) -> str:
    """Returns the Docker Compose GPU configuration for the specific vendor."""
    if vendor == GPUVendor.NVIDIA.value:
        return """
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
"""
    elif vendor == GPUVendor.AMD.value:
        return """
    devices:
      - /dev/kfd:/dev/kfd
      - /dev/dri:/dev/dri
    environment:
      - HSA_OVERRIDE_GFX_VERSION=12.0.0
"""
    elif vendor == GPUVendor.INTEL.value:
        return """
    devices:
      - /dev/dri:/dev/dri
"""
    return ""

def get_service_template(service: str, gpu_vendor: str, puid: int, pgid: int, mounts: list[str] = None) -> str:
    """Generates a hardware-optimized Docker Compose template."""
    
    gpu_section = get_gpu_section(gpu_vendor)
    
    # Format mounts if provided
    mount_lines = ""
    if mounts:
        for m in mounts:
            # Simple sanitization to ensure it looks like a path
            if m.startswith("/"):
                # We map host path to /data/name in container
                folder_name = m.rstrip("/").split("/")[-1]
                mount_lines += f"      - {m}:/data/{folder_name}\n"

    templates = {
        "ollama": f"""version: '3.8'
services:
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    restart: always
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - PUID={puid}
      - PGID={pgid}
      - OLLAMA_KEEP_ALIVE=24h
{gpu_section}

volumes:
  ollama_data:
""",
        "plex": f"""version: '3.8'
services:
  plex:
    image: lscr.io/linuxserver/plex:latest
    container_name: plex
    network_mode: host
    environment:
      - PUID={puid}
      - PGID={pgid}
      - VERSION=docker
    volumes:
      - /opt/hlmagic/config/plex:/config
{mount_lines or "      # <MEDIA_MOUNTS_GO_HERE>"}
    restart: unless-stopped
{gpu_section}
""",
        "jellyfin": f"""version: '3.8'
services:
  jellyfin:
    image: lscr.io/linuxserver/jellyfin:latest
    container_name: jellyfin
    environment:
      - PUID={puid}
      - PGID={pgid}
      - TZ=Etc/UTC
    volumes:
      - /opt/hlmagic/config/jellyfin:/config
{mount_lines or "      # <MEDIA_MOUNTS_GO_HERE>"}
    ports:
      - "8096:8096"
    restart: unless-stopped
{gpu_section}
""",
        "sonarr": f"""version: '3.8'
services:
  sonarr:
    image: lscr.io/linuxserver/sonarr:latest
    container_name: sonarr
    environment:
      - PUID={puid}
      - PGID={pgid}
      - TZ=Etc/UTC
    volumes:
      - /opt/hlmagic/config/sonarr:/config
{mount_lines or "      # <MEDIA_MOUNTS_GO_HERE>"}
    ports:
      - "8989:8989"
    restart: unless-stopped
""",
        "radarr": f"""version: '3.8'
services:
  radarr:
    image: lscr.io/linuxserver/radarr:latest
    container_name: radarr
    environment:
      - PUID={puid}
      - PGID={pgid}
      - TZ=Etc/UTC
    volumes:
      - /opt/hlmagic/config/radarr:/config
{mount_lines or "      # <MEDIA_MOUNTS_GO_HERE>"}
    ports:
      - "7878:7878"
    restart: unless-stopped
""",
        "lidarr": f"""version: '3.8'
services:
  lidarr:
    image: lscr.io/linuxserver/lidarr:latest
    container_name: lidarr
    environment:
      - PUID={puid}
      - PGID={pgid}
      - TZ=Etc/UTC
    volumes:
      - /opt/hlmagic/config/lidarr:/config
{mount_lines or "      # <MEDIA_MOUNTS_GO_HERE>"}
    ports:
      - "8686:8686"
    restart: unless-stopped
""",
        "overseerr": f"""version: '3.8'
services:
  overseerr:
    image: sctx/overseerr:latest
    container_name: overseerr
    environment:
      - LOG_LEVEL=debug
      - TZ=Etc/UTC
      - PORT=5055
    volumes:
      - /opt/hlmagic/config/overseerr:/app/config
    ports:
      - "5055:5055"
    restart: unless-stopped
"""
    }
    
    return templates.get(service.lower(), "")