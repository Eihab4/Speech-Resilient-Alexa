import sqlite3

import pytest

from messages import ErrorMessage
from people.passwords import check_password, hash_password
from support import base_url, http, sign_up


def account(url, path, body=None, token=None, method="POST"):
    return http(f"{base_url(url)}{path}", method, body, token)


def test_creating_an_account_signs_in_and_keeps_the_name(server):
    url = server()

    status, session = account(url, "/signup", {"username": "Rana_H", "name": "Rana", "password": "secret1"})
    me = account(url, "/me", token=session["token"], method="GET")

    assert status == 201
    assert session["username"] == "rana_h"
    assert session["name"] == "Rana"
    assert me == (200, {"username": "rana_h", "name": "Rana", "wait_seconds": 2})


def test_a_username_belongs_to_one_account(server):
    url = server()
    sign_up(url, "rana_h")

    assert account(url, "/signup", {"username": "RANA_H", "name": "Rana", "password": "secret1"}) == (
        409,
        {"error": ErrorMessage.USERNAME_TAKEN},
    )


@pytest.mark.parametrize(
    ("body", "error"),
    [
        ({"username": "ra", "name": "Rana", "password": "secret1"}, ErrorMessage.USERNAME_INVALID),
        ({"username": "rana h", "name": "Rana", "password": "secret1"}, ErrorMessage.USERNAME_INVALID),
        ({"username": "rana_h", "name": " ", "password": "secret1"}, ErrorMessage.NAME_MISSING),
        ({"username": "rana_h", "name": "Rana", "password": "12345"}, ErrorMessage.PASSWORD_TOO_SHORT),
        ({}, ErrorMessage.USERNAME_INVALID),
    ],
)
def test_a_bad_sign_up_says_what_is_wrong(server, body, error):
    assert account(server(), "/signup", body) == (400, {"error": error})


def test_signing_in_gives_a_new_session(server):
    url = server()
    sign_up(url, "rana_h", "Rana", "secret1")

    status, session = account(url, "/signin", {"username": "Rana_H", "password": "secret1"})

    assert status == 200
    assert session["name"] == "Rana"
    assert account(url, "/me", token=session["token"], method="GET")[0] == 200


@pytest.mark.parametrize(
    "body", [{"username": "rana_h", "password": "wrong!!"}, {"username": "nobody", "password": "x"}]
)
def test_a_wrong_username_or_password_gets_the_same_answer(server, body):
    url = server()
    sign_up(url, "rana_h", "Rana", "secret1")

    assert account(url, "/signin", body) == (401, {"error": ErrorMessage.SIGN_IN_FAILED})


def test_signing_out_ends_only_that_session(server):
    url = server()
    first = sign_up(url, "rana_h", "Rana", "secret1")
    _, second = account(url, "/signin", {"username": "rana_h", "password": "secret1"})

    assert account(url, "/signout", token=first)[0] == 204
    assert account(url, "/me", token=first, method="GET") == (401, {"error": ErrorMessage.NOT_SIGNED_IN})
    assert account(url, "/me", token=second["token"], method="GET")[0] == 200


@pytest.mark.parametrize(
    ("method", "path"),
    [("GET", "/profile"), ("PUT", "/profile"), ("GET", "/helpers"), ("POST", "/helpers"), ("DELETE", "/helpers/h_1")],
)
@pytest.mark.parametrize("token", [None, "made-up"])
def test_the_setup_needs_a_signed_in_account(server, method, path, token):
    assert account(server(), path, {"name": "Sara"}, token, method) == (401, {"error": ErrorMessage.NOT_SIGNED_IN})


def test_the_password_is_never_stored_as_typed(server, tmp_path):
    sign_up(server(), "rana_h", "Rana", "secret1")

    with sqlite3.connect(tmp_path / "memory.db") as db:
        [(stored,)] = db.execute("SELECT password_hash FROM accounts").fetchall()
        [(session,)] = db.execute("SELECT token_hash FROM sessions").fetchall()

    assert stored.startswith("scrypt$")
    assert "secret1" not in stored
    assert len(session) == 64


def test_a_password_matches_only_itself():
    stored = hash_password("secret1")

    assert check_password("secret1", stored)
    assert not check_password("secret2", stored)
    assert not check_password("secret1", "not a hash")
    assert hash_password("secret1") != stored
