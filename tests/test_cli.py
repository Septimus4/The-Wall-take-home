"""Tests for the simulator CLI module."""

import sys
from unittest.mock import Mock, patch

from services.simulator.cli import main


class TestSimulatorCLI:
    """Test cases for the simulator CLI."""

    @patch("services.simulator.cli.uvicorn.run")
    @patch("services.simulator.cli.SimulatorConfig")
    def test_main_with_default_args(self, mock_config, mock_uvicorn_run):
        """Test main function with default arguments."""
        # Setup mock config
        mock_config_instance = Mock()
        mock_config_instance.version = "1.0.0"
        mock_config_instance.environment = "development"
        mock_config_instance.kafka_config.bootstrap_servers = "localhost:9092"
        mock_config.return_value = mock_config_instance

        # Mock sys.argv to simulate default arguments
        with patch.object(sys, "argv", ["cli.py"]):
            main()

        # Verify SimulatorConfig was instantiated
        mock_config.assert_called_once()

        # Verify uvicorn.run was called with correct defaults
        mock_uvicorn_run.assert_called_once_with(
            "services.simulator.main:app",
            host="0.0.0.0",
            port=9000,
            reload=False,
            log_level="info",
            workers=1,
        )

    @patch("services.simulator.cli.uvicorn.run")
    @patch("services.simulator.cli.SimulatorConfig")
    def test_main_with_custom_args(self, mock_config, mock_uvicorn_run):
        """Test main function with custom arguments."""
        # Setup mock config
        mock_config_instance = Mock()
        mock_config_instance.version = "1.0.0"
        mock_config_instance.environment = "production"
        mock_config_instance.kafka_config.bootstrap_servers = "prod-kafka:9092"
        mock_config.return_value = mock_config_instance

        # Mock sys.argv to simulate custom arguments
        with patch.object(
            sys,
            "argv",
            [
                "cli.py",
                "--host",
                "127.0.0.1",
                "--port",
                "8080",
                "--reload",
                "--log-level",
                "debug",
                "--workers",
                "4",
            ],
        ):
            main()

        # Verify uvicorn.run was called with custom args
        mock_uvicorn_run.assert_called_once_with(
            "services.simulator.main:app",
            host="127.0.0.1",
            port=8080,
            reload=True,
            log_level="debug",
            workers=1,  # Should be 1 when reload=True
        )

    @patch("services.simulator.cli.uvicorn.run")
    @patch("services.simulator.cli.SimulatorConfig")
    @patch("services.simulator.cli.logging.basicConfig")
    def test_logging_configuration(
        self, mock_logging_config, mock_config, mock_uvicorn_run
    ):
        """Test that logging is configured correctly."""
        # Setup mock config
        mock_config_instance = Mock()
        mock_config_instance.version = "1.0.0"
        mock_config_instance.environment = "development"
        mock_config_instance.kafka_config.bootstrap_servers = "localhost:9092"
        mock_config.return_value = mock_config_instance

        # Mock sys.argv with debug log level
        with patch.object(sys, "argv", ["cli.py", "--log-level", "debug"]):
            main()

        # Verify logging was configured
        import logging

        mock_logging_config.assert_called_once_with(level=logging.DEBUG)

    @patch("services.simulator.cli.uvicorn.run")
    @patch("services.simulator.cli.SimulatorConfig")
    def test_workers_with_reload(self, mock_config, mock_uvicorn_run):
        """Test that workers is set to 1 when reload is enabled."""
        # Setup mock config
        mock_config_instance = Mock()
        mock_config_instance.version = "1.0.0"
        mock_config_instance.environment = "development"
        mock_config_instance.kafka_config.bootstrap_servers = "localhost:9092"
        mock_config.return_value = mock_config_instance

        # Mock sys.argv with reload and multiple workers
        with patch.object(sys, "argv", ["cli.py", "--reload", "--workers", "4"]):
            main()

        # Verify workers is set to 1 when reload is enabled
        args, kwargs = mock_uvicorn_run.call_args
        assert kwargs["workers"] == 1

    @patch("services.simulator.cli.uvicorn.run")
    @patch("services.simulator.cli.SimulatorConfig")
    def test_workers_without_reload(self, mock_config, mock_uvicorn_run):
        """Test that workers setting is preserved when reload is disabled."""
        # Setup mock config
        mock_config_instance = Mock()
        mock_config_instance.version = "1.0.0"
        mock_config_instance.environment = "development"
        mock_config_instance.kafka_config.bootstrap_servers = "localhost:9092"
        mock_config.return_value = mock_config_instance

        # Mock sys.argv with multiple workers but no reload
        with patch.object(sys, "argv", ["cli.py", "--workers", "4"]):
            main()

        # Verify workers is preserved when reload is disabled
        args, kwargs = mock_uvicorn_run.call_args
        assert kwargs["workers"] == 4

    @patch("services.simulator.cli.argparse.ArgumentParser.parse_args")
    def test_argument_parser_setup(self, mock_parse_args):
        """Test that argument parser is set up correctly."""
        # Create a mock args object with expected attributes
        mock_args = Mock()
        mock_args.host = "0.0.0.0"
        mock_args.port = 9000
        mock_args.reload = False
        mock_args.log_level = "info"
        mock_args.workers = 1
        mock_parse_args.return_value = mock_args

        # Mock other dependencies to prevent actual execution
        with patch("services.simulator.cli.uvicorn.run"), patch(
            "services.simulator.cli.SimulatorConfig"
        ), patch("services.simulator.cli.logging.basicConfig"):
            main()

        # Verify parse_args was called
        mock_parse_args.assert_called_once()

    def test_cli_as_script(self):
        """Test CLI when run as a script."""
        # Test the if __name__ == "__main__" block
        import services.simulator.cli as cli_module

        # Mock the main function to verify it's called
        with patch.object(cli_module, "main"), open(
            cli_module.__file__, encoding="utf-8"
        ) as f:
            # Execute the module-level code
            exec(compile(f.read(), cli_module.__file__, "exec"))
            # Note: This test verifies the structure exists but doesn't actually call main()
            # to avoid side effects
