from executor.http.server.routers.proxy import remove_prefix


def test_remove_prefix():
    a = "abc/a.txt"
    assert remove_prefix(a, "abc/") == "a.txt"
    assert remove_prefix(a, "bcd/") == a
