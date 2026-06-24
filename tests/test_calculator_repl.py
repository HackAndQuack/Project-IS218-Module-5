from unittest.mock import patch

import pytest

from app.calculator_repl import calculator_repl
from app.operations import OperationFactory


@pytest.fixture(autouse=True)
def isolated_calculator_dirs(tmp_path, monkeypatch):
    """Redirect the REPL's default Calculator() to a temp dir instead of the real project tree."""
    monkeypatch.setenv('CALCULATOR_LOG_DIR', str(tmp_path / 'logs'))
    monkeypatch.setenv('CALCULATOR_LOG_FILE', str(tmp_path / 'logs' / 'calculator.log'))
    monkeypatch.setenv('CALCULATOR_HISTORY_DIR', str(tmp_path / 'history'))
    monkeypatch.setenv('CALCULATOR_HISTORY_FILE', str(tmp_path / 'history' / 'calculator_history.csv'))


def run_repl(inputs):
    with patch('builtins.input', side_effect=inputs), patch('builtins.print') as mock_print:
        calculator_repl()
    return mock_print


def test_repl_exit_saves_history():
    mock_print = run_repl(['exit'])
    mock_print.assert_any_call("History saved successfully.")
    mock_print.assert_any_call("Goodbye!")


def test_repl_exit_save_failure_warns():
    with patch('app.calculator.Calculator.save_history', side_effect=Exception("disk full")):
        mock_print = run_repl(['exit'])
    mock_print.assert_any_call("Warning: Could not save history: disk full")


def test_repl_help():
    mock_print = run_repl(['help', 'exit'])
    mock_print.assert_any_call("\nAvailable commands:")


def test_repl_unknown_command():
    mock_print = run_repl(['frobnicate', 'exit'])
    mock_print.assert_any_call("Unknown command: 'frobnicate'. Type 'help' for available commands.")


def test_repl_history_empty():
    mock_print = run_repl(['history', 'exit'])
    mock_print.assert_any_call("No calculations in history")


def test_repl_history_with_entries():
    mock_print = run_repl(['add', '2', '3', 'history', 'exit'])
    mock_print.assert_any_call("\nCalculation History:")
    mock_print.assert_any_call("1. Addition(2, 3) = 5")


def test_repl_clear():
    mock_print = run_repl(['add', '2', '3', 'clear', 'exit'])
    mock_print.assert_any_call("History cleared")


def test_repl_undo_success():
    mock_print = run_repl(['add', '2', '3', 'undo', 'exit'])
    mock_print.assert_any_call("Operation undone")


def test_repl_undo_nothing_to_undo():
    mock_print = run_repl(['undo', 'exit'])
    mock_print.assert_any_call("Nothing to undo")


def test_repl_redo_success():
    mock_print = run_repl(['add', '2', '3', 'undo', 'redo', 'exit'])
    mock_print.assert_any_call("Operation redone")


def test_repl_redo_nothing_to_redo():
    mock_print = run_repl(['redo', 'exit'])
    mock_print.assert_any_call("Nothing to redo")


def test_repl_save_success():
    mock_print = run_repl(['save', 'exit'])
    mock_print.assert_any_call("History saved successfully")


def test_repl_save_error():
    with patch('app.calculator.Calculator.save_history', side_effect=Exception("disk full")):
        mock_print = run_repl(['save', 'exit'])
    mock_print.assert_any_call("Error saving history: disk full")


def test_repl_load_success():
    mock_print = run_repl(['load', 'exit'])
    mock_print.assert_any_call("History loaded successfully")


def test_repl_load_error():
    with patch('app.calculator.Calculator.load_history', side_effect=Exception("corrupt file")):
        mock_print = run_repl(['load', 'exit'])
    mock_print.assert_any_call("Error loading history: corrupt file")


@pytest.mark.parametrize("command,a,b,expected", [
    ('add', '2', '3', '5'),
    ('subtract', '5', '2', '3'),
    ('multiply', '4', '3', '12'),
    ('divide', '10', '2', '5'),
    ('power', '2', '3', '8'),
    ('root', '16', '2', '4'),
])
def test_repl_operations(command, a, b, expected):
    mock_print = run_repl([command, a, b, 'exit'])
    mock_print.assert_any_call(f"\nResult: {expected}")


def test_repl_cancel_on_first_number():
    mock_print = run_repl(['add', 'cancel', 'exit'])
    mock_print.assert_any_call("Operation cancelled")


def test_repl_cancel_on_second_number():
    mock_print = run_repl(['add', '2', 'cancel', 'exit'])
    mock_print.assert_any_call("Operation cancelled")


def test_repl_operation_validation_error():
    mock_print = run_repl(['divide', '5', '0', 'exit'])
    mock_print.assert_any_call("Error: Division by zero is not allowed")


def test_repl_operation_unexpected_error():
    with patch.object(OperationFactory, 'create_operation', side_effect=RuntimeError("factory boom")):
        mock_print = run_repl(['add', '2', '3', 'exit'])
    mock_print.assert_any_call("Unexpected error: factory boom")


def test_repl_keyboard_interrupt_continues_loop():
    mock_print = run_repl([KeyboardInterrupt(), 'exit'])
    mock_print.assert_any_call("\nOperation cancelled")


def test_repl_eof_error_exits():
    mock_print = run_repl([EOFError()])
    mock_print.assert_any_call("\nInput terminated. Exiting...")


def test_repl_unexpected_loop_exception_continues():
    mock_print = run_repl([RuntimeError("weird"), 'exit'])
    mock_print.assert_any_call("Error: weird")


def test_repl_fatal_error_on_init():
    with patch('app.calculator_repl.Calculator', side_effect=RuntimeError("init failed")):
        with patch('builtins.print') as mock_print:
            with pytest.raises(RuntimeError, match="init failed"):
                calculator_repl()
    mock_print.assert_any_call("Fatal error: init failed")
