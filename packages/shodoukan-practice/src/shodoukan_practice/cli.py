"""Maintenance commands for the practice database.

    python -m shodoukan_practice.cli analyze-sentences
    shodoukan-practice-admin analyze-sentences

Reads `PRACTICE_DATABASE_URL` from the environment, like the API. Each
command runs in one transaction, committed when it finishes.
"""

import argparse

from sqlalchemy.orm import Session

from .application.commands import AnalyzeSentences
from .infrastructure.db.connection import create_db_engine
from .infrastructure.morphology import SudachiMorphologyGateway
from .infrastructure.repositories import (
    SqlAlchemyPracticeEntryRepository,
    SqlAlchemyPracticeSentenceRepository,
)


def analyze_sentences() -> None:
    """Complete every user's sentences with the analyzer (`AnalyzeSentences`)."""
    with Session(create_db_engine()) as session:
        result = AnalyzeSentences(
            SqlAlchemyPracticeSentenceRepository(session),
            SqlAlchemyPracticeEntryRepository(session),
            SudachiMorphologyGateway(),
        ).execute()
        session.commit()
    print(
        f"{result.sentences} sentences of {result.users} users: "
        f"{result.analyzed} gaps analyzed, {result.marked} linked words found, "
        f"{result.unmarked} still without a gap"
    )


COMMANDS = {"analyze-sentences": analyze_sentences}


def main() -> None:
    parser = argparse.ArgumentParser(prog="shodoukan-practice-admin")
    parser.add_argument("command", choices=sorted(COMMANDS))
    COMMANDS[parser.parse_args().command]()


if __name__ == "__main__":
    main()
