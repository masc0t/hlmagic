import pytest
from hlmagic.utils.tools import _validate_service_name, _validate_compose_content, SecurityViolation

def test_validate_service_name_valid():
    # Should not raise exception
    _validate_service_name("plex")
    _validate_service_name("sonarr-1")
    _validate_service_name("my_service")

def test_validate_service_name_invalid():
    with pytest.raises(SecurityViolation):
        _validate_service_name("plex; rm -rf /")
    with pytest.raises(SecurityViolation):
        _validate_service_name("../hidden")
    with pytest.raises(SecurityViolation):
        _validate_service_name("space name")

def test_validate_compose_content_safe():
    safe_content = """
version: '3'
services:
  web:
    image: nginx
    volumes:
      - /opt/hlmagic/config:/config
"""
    # Should not raise
    _validate_compose_content(safe_content)

def test_validate_compose_content_dangerous_mount():
    dangerous_content = """
version: '3'
services:
  web:
    image: nginx
    volumes:
      - /etc:/etc
"""
    with pytest.raises(SecurityViolation, match="Dangerous volume mount detected"):
        _validate_compose_content(dangerous_content)

def test_validate_compose_content_privileged():
    privileged_content = """
version: '3'
services:
  web:
    image: nginx
    privileged: true
"""
    with pytest.raises(SecurityViolation, match="Privileged mode is currently restricted"):
        _validate_compose_content(privileged_content)
