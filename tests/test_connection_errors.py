import sys
import time

import pytest


if sys.platform == "win32":
    server_closed_message = (
        "[WinError 10054] An existing connection was forcibly closed by the remote host"
    )
else:
    server_closed_message = "Server closed the connection!"


@pytest.mark.skipif(
    sys.platform == "win32", reason="fails github actions and I don't know why"
)
def test_quitting_while_disconnected(alice, hircd, monkeypatch, wait_until):
    hircd.stop()
    wait_until(
        lambda: ("Error while receiving: " + server_closed_message) in alice.text()
    )
    assert alice.get_current_view().channel_name == "#autojoin"

    start = time.monotonic()
    alice.get_server_views()[0].core.quit()
    alice.get_server_views()[0].core.wait_for_threads_to_stop()
    end = time.monotonic()
    assert end - start < 0.5  # on my computer, typically 0.08 or so


def test_server_dies(alice, hircd, monkeypatch, wait_until):
    monkeypatch.setattr("mantaray.backend.RECONNECT_SECONDS", 2)

    hircd.stop()
    wait_until(lambda: "Cannot connect (reconnecting in 2sec):" in alice.text())

    lines = alice.text().splitlines()
    assert lines[-4].endswith("Error while receiving: " + server_closed_message)
    assert lines[-3].endswith("Disconnected.")
    assert lines[-2].endswith("Connecting to localhost port 6667...")
    assert "Cannot connect (reconnecting in 2sec):" in lines[-1]
    if sys.platform == "win32":
        assert lines[-1].endswith(
            "No connection could be made because the target machine actively refused it"
        )
    else:
        assert lines[-1].endswith("Connection refused")

    hircd.start()
    wait_until(lambda: alice.text().endswith("Connecting to localhost port 6667...\n"))
    connecting_end = len(alice.text())
    wait_until(
        lambda: "The topic of #autojoin is: No topic" in alice.text()[connecting_end:]
    )
    assert alice.get_current_view().userlist.get_nicks() == ("Alice", "Bob")


def test_order_bug(alice, mocker, monkeypatch, wait_until):
    server_view = alice.get_server_views()[0]
    server_view.core.apply_config_and_reconnect(server_view.get_current_config())
    wait_until(
        lambda: "Disconnected." in alice.text() and "Connecting to" in alice.text()
    )
    assert alice.text().index("Disconnected.") < alice.text().index("Connecting to")
