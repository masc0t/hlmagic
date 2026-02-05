import pytest
from hlmagic.utils.templates import get_service_template, get_gpu_section
from hlmagic.utils.hardware import GPUVendor

def test_gpu_section_nvidia():
    section = get_gpu_section(GPUVendor.NVIDIA.value)
    assert "driver: nvidia" in section
    assert "capabilities: [gpu]" in section

def test_gpu_section_amd():
    section = get_gpu_section(GPUVendor.AMD.value)
    assert "/dev/kfd" in section
    assert "HSA_OVERRIDE_GFX_VERSION" in section

def test_gpu_section_intel():
    section = get_gpu_section(GPUVendor.INTEL.value)
    assert "/dev/dri" in section
    assert "driver: nvidia" not in section

def test_service_template_ollama_nvidia():
    template = get_service_template("ollama", GPUVendor.NVIDIA.value, 1000, 1000)
    assert "image: ollama/ollama:latest" in template
    assert "driver: nvidia" in template
    assert "PUID=1000" in template

def test_service_template_plex_amd():
    template = get_service_template("plex", GPUVendor.AMD.value, 1000, 1000)
    assert "image: lscr.io/linuxserver/plex:latest" in template
    assert "/dev/kfd" in template
    assert "PGID=1000" in template

def test_invalid_service():
    template = get_service_template("nonexistent", "nvidia", 1000, 1000)
    assert template == ""
