"""Version management for TokenPFS.

Versioning algorithm (X.X.X / SemVer):
  X.0.0 -> Global update (complete rewrite, breaking changes)
  0.X.0 -> Major update  (big new features)
  0.0.X -> Mini update   (small fixes / tweaks)
"""

VERSION_MAJOR = 1
VERSION_MINOR = 1
VERSION_PATCH = 2

APP_NAME = "TokenPFS"


def version_string() -> str:
    return f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"


def bump(kind: str) -> str:
    """Return the next version number without mutating the current one.

    kind: 'global' | 'major' | 'mini'
    """
    g, m, p = VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH
    if kind == "global":
        return f"{g + 1}.0.0"
    if kind == "major":
        return f"{g}.{m + 1}.0"
    if kind == "mini":
        return f"{g}.{m}.{p + 1}"
    raise ValueError(f"unknown bump kind: {kind!r}")
