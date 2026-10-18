"""Small, dependency-free helpers for building file names from untrusted text.

Map names come from the beetlerank.com server (or from guildhall.txt, which the
speedometer writes from that same value), so they must never be able to escape
the ``logs`` / ``maps`` folders or produce names Windows cannot create.

``sanitize_map_name`` is the identity function for every normal map name
(letters, digits, spaces, accents and ordinary punctuation such as
``None, im free!``): the log/CSV file name of a legitimate map is unchanged.
"""

import re

# Characters Windows cannot have in a file name (plus control characters).
# Includes both path separators, so "a/b" or "..\\x" cannot traverse folders.
_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Device names reserved by Windows (reserved even with an extension, "CON.csv").
_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL"}
_RESERVED_NAMES |= {"COM%d" % i for i in range(1, 10)}
_RESERVED_NAMES |= {"LPT%d" % i for i in range(1, 10)}

DEFAULT_MAX_LEN = 100
_FALLBACK_NAME = "_"


def sanitize_map_name(name, max_len=DEFAULT_MAX_LEN):
    """Return ``name`` made safe to use as (part of) a file name.

    * Path separators and characters invalid on Windows (``< > : " / \\ | ? *``
      and control characters) are replaced with ``_``.
    * A name made only of dots/spaces (``.``, ``..``, ``...``) is replaced, so it
      can never mean "current/parent directory".
    * Windows reserved device names (``CON``, ``NUL``, ``COM1``...) get a ``_``
      prefix.
    * Length is capped to ``max_len`` characters.

    Names without any of those problems are returned exactly as given.
    """
    if name is None:
        return _FALLBACK_NAME
    text = str(name)
    text = _INVALID_CHARS.sub("_", text)
    if len(text) > max_len:
        text = text[:max_len]
    if not text.strip(" ."):
        return _FALLBACK_NAME
    if text.split(".", 1)[0].strip().upper() in _RESERVED_NAMES:
        text = "_" + text
    return text
