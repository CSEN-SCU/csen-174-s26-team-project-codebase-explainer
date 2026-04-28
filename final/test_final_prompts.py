try:
    # Works when running pytest from the repository root.
    from prototypes.final.example_questions import get_example_questions
except ModuleNotFoundError:
    # Works when running pytest from inside prototypes/final.
    from example_questions import get_example_questions


# As a student, I see example questions so I know how to interact with the system.
def test_returns_example_questions():
    # Arrange
    repo_data = {}

    # Act
    examples = get_example_questions(repo_data)

    # Assert
    assert isinstance(examples, list)


# As a student, I see at least one example question so I know how to get started.
def test_example_questions_not_empty():
    # Arrange
    repo_data = {}

    # Act
    examples = get_example_questions(repo_data)

    # Assert
    assert len(examples) > 0
