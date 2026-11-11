"""Static guard: no shell execution or privilege escalation helpers in the code base."""

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "onion_desktop"
FORBIDDEN = [
    (re.compile(r"shell\s*=\s*True"), "shell=True"),
    (re.compile(r"\bos\.system\("), "os.system"),
    (re.compile(r"\bos\.popen\("), "os.popen"),
    (re.compile(r"[\"'](sudo|pkexec|gksu|kdesu)[\"']"), "privilege escalation helper"),
    (re.compile(r"(?<![.\w])(eval|exec)\("), "builtin eval/exec"),
]


def test_no_forbidden_constructs():
    offenders = []
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for rx, what in FORBIDDEN:
            if rx.search(text):
                offenders.append(f"{path.relative_to(SRC)}: {what}")
    assert offenders == []


def test_subprocess_only_in_allowed_modules():
    users = {p.relative_to(SRC).as_posix() for p in SRC.rglob("*.py") if "subprocess" in p.read_text()}
    assert users <= {"linux/lsblk_backend.py"}
