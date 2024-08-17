from tests import assert_ok


def test_statistics(client, admin_header, lender_header):
    response = client.get("/statistics-ocp", headers=admin_header)
    assert_ok(response)

    response = client.get("/statistics-ocp/opt-in", headers=admin_header)
    assert_ok(response)

    response = client.get("/statistics-fi", headers=lender_header)
    assert_ok(response)
