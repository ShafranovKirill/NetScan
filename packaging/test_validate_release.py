import unittest
from validate_release import release_tag


class ReleaseValidationTests(unittest.TestCase):
    def test_branch_build_does_not_publish(self):
        self.assertEqual(release_tag("0.2.0", "refs/heads/develop", "", "abc", lambda _: "abc"), "")

    def test_tag_build_publishes_matching_commit(self):
        self.assertEqual(release_tag("0.2.0", "refs/tags/v0.2.0", "", "abc", lambda _: "abc"), "v0.2.0")

    def test_manual_version_accepts_optional_v(self):
        for requested in ("0.2.0", "v0.2.0"):
            self.assertEqual(release_tag("0.2.0", "refs/heads/develop", requested, "abc", lambda _: "abc"), "v0.2.0")

    def test_rejects_mismatched_version(self):
        with self.assertRaises(ValueError):
            release_tag("0.2.0", "refs/tags/v0.1.0", "", "abc", lambda _: "abc")

    def test_rejects_missing_or_other_commit(self):
        for result in ("", "different"):
            with self.assertRaises(ValueError):
                release_tag("0.2.0", "refs/heads/develop", "0.2.0", "abc", lambda _: result)

    def test_rejects_conflicting_manual_tag(self):
        with self.assertRaises(ValueError):
            release_tag("0.2.0", "refs/tags/v0.2.0", "0.3.0", "abc", lambda _: "abc")


if __name__ == "__main__":
    unittest.main()
