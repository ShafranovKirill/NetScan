"""Validate an optional release tag before spending time on installer builds."""
import importlib.metadata
import os
import re
import subprocess
from pathlib import Path


def release_tag(version, ref, requested, sha, resolve_tag):
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?", version):
        raise ValueError("Unsupported project version; use a three-part release version")
    tag = ref.removeprefix("refs/tags/") if ref.startswith("refs/tags/") else ""
    if requested:
        requested_tag = "v" + requested.removeprefix("v")
        if tag and requested_tag != tag:
            raise ValueError("Requested version disagrees with pushed tag")
        tag = requested_tag
    if not tag:
        return ""
    if tag != "v" + version:
        raise ValueError("Release tag must match the version in pyproject.toml")
    if resolve_tag(tag) != sha:
        raise ValueError("Release tag must already exist and point to the checked-out commit")
    return tag


def main():
    version = importlib.metadata.version("netscan-desktop")

    def resolve(tag):
        try:
            return subprocess.check_output(
                ["git", "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}"],
                text=True, stderr=subprocess.DEVNULL,
            ).strip()
        except subprocess.CalledProcessError:
            return ""

    tag = release_tag(version, os.getenv("GITHUB_REF", ""),
                      os.getenv("REQUESTED_VERSION", "").strip(),
                      os.getenv("GITHUB_SHA", ""), resolve)
    output = f"version={version}\nrelease_tag={tag}\n"
    if os.getenv("GITHUB_OUTPUT"):
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as stream:
            stream.write(output)
    print(output, end="")


if __name__ == "__main__":
    main()
