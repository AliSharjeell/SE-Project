#!/usr/bin/env python3
"""
AI-Driven Autonomous Infrastructure Manager
Main entry point for the simulation.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from orchestrator import InfrastructureOrchestrator


def setup_logging(level: str = "INFO"):
    """Configure logging for the application."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AI-Driven Autonomous Infrastructure Manager"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/config.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--scenario",
        type=str,
        choices=["normal", "spike", "ramp", "sine_wave"],
        help="Traffic scenario to simulate"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        help="Number of simulation iterations"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Launch the Streamlit dashboard after simulation"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    logger.info("Starting AI-Driven Infrastructure Manager")

    # Initialize orchestrator
    try:
        orchestrator = InfrastructureOrchestrator(config_path=args.config)

        # Override config with CLI args if provided
        if args.scenario:
            orchestrator.config["orchestrator"]["simulation"]["scenario"] = args.scenario
        if args.iterations:
            orchestrator.config["orchestrator"]["simulation"]["max_iterations"] = args.iterations

        orchestrator.initialize()
        logger.info("System initialized successfully")

        # Run simulation
        with orchestrator:
            orchestrator.start()
            logger.info("Simulation completed")

        # Display final status
        status = orchestrator.get_system_status()
        logger.info(f"Final system status: {status}")

        # Launch dashboard if requested
        if args.dashboard:
            logger.info("Launching dashboard...")
            import subprocess
            subprocess.run([
                sys.executable, "-m", "streamlit", "run",
                "src/dashboard/app.py", "--server.port", "8501"
            ])

    except Exception as e:
        logger.error(f"Error during execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()