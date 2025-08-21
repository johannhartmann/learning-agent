"""Main entry point for the Learning Agent when run as a module."""

from dotenv import load_dotenv

from learning_agent.cli import app


# Load environment variables from .env file
load_dotenv()


if __name__ == "__main__":
    app()
