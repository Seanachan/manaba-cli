import keyring
import pytest
from keyring.backends.fail import Keyring as FailKeyring

from manaba_cli.credentials import KEYRING_SERVICE, Credentials, load_credentials, store_password
from manaba_cli.errors import ManabaError
from tests.support import MemoryKeyring


def test_store_then_load(memory_keyring: MemoryKeyring) -> None:
    store_password("s0000000", "hunter2")

    assert memory_keyring.passwords == {(KEYRING_SERVICE, "s0000000"): "hunter2"}
    assert load_credentials("s0000000") == Credentials("s0000000", "hunter2")


def test_no_username_or_no_password_means_no_credentials() -> None:
    assert load_credentials(None) is None
    assert load_credentials("s0000000") is None


def test_repr_hides_password() -> None:
    assert "hunter2" not in repr(Credentials("s0000000", "hunter2"))


def test_missing_keyring_backend_is_a_clear_error() -> None:
    keyring.set_keyring(FailKeyring())

    with pytest.raises(ManabaError, match="keyring is not usable"):
        load_credentials("s0000000")
    with pytest.raises(ManabaError, match="keyring is not usable"):
        store_password("s0000000", "hunter2")
