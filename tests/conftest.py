"""tests/conftest.py — ensures repo root is on path for all sub-packages."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---- slow-test marking (ledger addendum 45) -------------------------------------------------
# tests/slow_tests.txt lists, one per line, the test functions that take more than a few seconds
# (measured; regenerate with tools/update_slow_tests_v1.py). They get the `slow` marker here, so
#   python3 -m pytest tests/vm -m "not slow"     is the quick run, and
#   python3 -m pytest tests/vm                   is still the full run.
# A name is a function's node id without any [parameters]. A name that no longer matches is harmless.
def _slow_names():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "slow_tests.txt")
    try:
        with open(p) as f:
            return {ln.strip() for ln in f if ln.strip() and not ln.startswith("#")}
    except OSError:
        return set()


def pytest_collection_modifyitems(config, items):
    import pytest
    slow = _slow_names()
    for item in items:
        if item.nodeid.split("[")[0] in slow:
            item.add_marker(pytest.mark.slow)


# ---- timing log, on demand (ledger addendum 45) ---------------------------------------------
#   python3 -m pytest tests/vm -q --log-durations=durations.log        (add  -n 2  for speed)
#   python3 tools/update_slow_tests_v1.py durations.log                rebuilds tests/slow_tests.txt
# Each finished test is appended to the file at once, so stopping a long run early still leaves usable data.
_DURLOG = [None]


def pytest_addoption(parser):
    parser.addoption("--log-durations", action="store", default=None, metavar="FILE",
                     help="append '<seconds>s <setup|call|teardown> <node id>' for every test to FILE as it finishes")


def pytest_configure(config):
    # under xdist only the controller writes (the workers also see each report, which would double every line)
    _DURLOG[0] = None if hasattr(config, "workerinput") else config.getoption("--log-durations", default=None)


def pytest_runtest_logreport(report):
    if _DURLOG[0] and report.when in ("setup", "call", "teardown"):
        with open(_DURLOG[0], "a") as f:
            f.write("%.2fs %s %s\n" % (report.duration, report.when, report.nodeid))
