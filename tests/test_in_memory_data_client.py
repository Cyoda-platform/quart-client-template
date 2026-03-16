from application.clients.data_client import data_client


def test_in_memory_client_create_and_query():
    # create a test run and case
    data_client.create_test_case("tc1", {"title":"t1","steps":[]})
    data_client.create_test_run("run1", {"test_case_refs":["tc1"]})

    run = data_client.get_test_run("run1")
    assert run is not None

    re_id = data_client.create_test_run_execution("run1", {"test_case_id":"tc1","status":"Queued"})
    assert re_id is not None

    se_id = data_client.create_step_execution(re_id, {"test_step_number":1,"action":"a","expected":"e"})
    assert se_id is not None

    steps = data_client.list_step_executions_for_run("run1")
    assert len(steps) == 1
