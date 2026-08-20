from apps.core.tasks import ping


class TestPingTask:
    def test_ping_task_runs_synchronously_and_returns_pong(self):
        assert ping.run() == "pong"
