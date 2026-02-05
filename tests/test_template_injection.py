import unittest
from hlmagic.utils import templates

class TestTemplateInjection(unittest.TestCase):
    def test_plex_injection(self):
        mounts = ["/mnt/d/Movies", "/mnt/e/TV"]
        template = templates.get_service_template("plex", "nvidia", 1000, 1000, mounts=mounts)
        
        self.assertIn("- /mnt/d/Movies:/data/Movies", template)
        self.assertIn("- /mnt/e/TV:/data/TV", template)
        self.assertNotIn("<MEDIA_MOUNTS_GO_HERE>", template)

    def test_no_injection(self):
        template = templates.get_service_template("plex", "nvidia", 1000, 1000)
        self.assertIn("# <MEDIA_MOUNTS_GO_HERE>", template)

if __name__ == "__main__":
    unittest.main()
