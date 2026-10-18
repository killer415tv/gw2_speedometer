import pytest

from pathutils import sanitize_map_name

# Names of normal maps must come out byte-for-byte identical, so the log/CSV
# file name of a legitimate map never changes.
LEGIT_NAMES = [
    "Rata River",
    "None, im free!",
    "Beetle Fiesta 2",
    "Lion's Arch (night)",
    "Mapa_con_guiones-y-acentos áéíóú ñ",
    "Race [v2] #1 & more",
    "Map.With.Dots",
    "A" * 100,
    "Sunken Cove 100% 🏁",
    "con",  # lower-case word inside a longer name is fine below
    "Constantine",
    "NULL_ISLAND",
]


@pytest.mark.parametrize("name", [n for n in LEGIT_NAMES if n != "con"])
def test_legit_names_unchanged(name):
    assert sanitize_map_name(name) == name


def test_legit_name_used_in_log_filename_is_identical():
    name = "Rata River"
    assert sanitize_map_name(name) + "_log_" + "1760000000.123" + ".csv" == (
        name + "_log_" + "1760000000.123" + ".csv"
    )


@pytest.mark.parametrize(
    "evil",
    [
        "../../etc/passwd",
        "..\\..\\Windows\\System32\\evil",
        "/absolute/path",
        "C:\\Windows\\x",
        "a/b\\c",
        "..",
        ".",
        "...",
        "  ",
        "",
        None,
    ],
)
def test_no_separators_or_traversal(evil):
    out = sanitize_map_name(evil)
    assert "/" not in out and "\\" not in out
    assert out.strip(" .") != ""  # never "." / ".." / empty
    assert ":" not in out


@pytest.mark.parametrize("ch", list('<>:"/\\|?*') + ["\x00", "\x1f", "\n", "\t"])
def test_invalid_windows_chars_replaced(ch):
    assert sanitize_map_name("a" + ch + "b") == "a_b"


@pytest.mark.parametrize("name", ["CON", "nul", "COM1", "lpt9", "AUX", "PRN", "CON.txt"])
def test_reserved_device_names_prefixed(name):
    out = sanitize_map_name(name)
    assert out == "_" + name


def test_length_is_capped():
    assert len(sanitize_map_name("x" * 5000)) == 100
    assert len(sanitize_map_name("x" * 5000, max_len=20)) == 20


def test_result_stays_inside_logs_folder(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    for evil in ["../../x", "..\\..\\x", "/tmp/x", "a/../../b"]:
        p = (logs / (sanitize_map_name(evil) + "_log_1.csv")).resolve()
        assert p.parent == logs.resolve()
