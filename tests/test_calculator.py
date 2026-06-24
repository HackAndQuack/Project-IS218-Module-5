import datetime
from contextlib import contextmanager
from pathlib import Path
import pandas as pd
import pytest
from unittest.mock import Mock, patch, PropertyMock
from decimal import Decimal
from tempfile import TemporaryDirectory
from app.calculator import Calculator
from app.calculator_config import CalculatorConfig
from app.exceptions import OperationError, ValidationError
from app.history import LoggingObserver, AutoSaveObserver
from app.operations import OperationFactory


@contextmanager
def patched_config(temp_path):
    """Build a CalculatorConfig whose file paths are redirected into temp_path."""
    config = CalculatorConfig(base_dir=temp_path)
    with patch.object(CalculatorConfig, 'log_dir', new_callable=PropertyMock) as mock_log_dir, \
         patch.object(CalculatorConfig, 'log_file', new_callable=PropertyMock) as mock_log_file, \
         patch.object(CalculatorConfig, 'history_dir', new_callable=PropertyMock) as mock_history_dir, \
         patch.object(CalculatorConfig, 'history_file', new_callable=PropertyMock) as mock_history_file:
        mock_log_dir.return_value = temp_path / "logs"
        mock_log_file.return_value = temp_path / "logs/calculator.log"
        mock_history_dir.return_value = temp_path / "history"
        mock_history_file.return_value = temp_path / "history/calculator_history.csv"
        yield config


# Fixture to initialize Calculator with a temporary directory for file paths
@pytest.fixture
def calculator():
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        with patched_config(temp_path) as config:
            # Return an instance of Calculator with the mocked config
            yield Calculator(config=config)

# Test Calculator Initialization

def test_calculator_initialization(calculator):
    assert calculator.history == []
    assert calculator.undo_stack == []
    assert calculator.redo_stack == []
    assert calculator.operation_strategy is None

# Test Logging Setup

@patch('app.calculator.logging.info')
def test_logging_setup(logging_info_mock):
    with patch.object(CalculatorConfig, 'log_dir', new_callable=PropertyMock) as mock_log_dir, \
         patch.object(CalculatorConfig, 'log_file', new_callable=PropertyMock) as mock_log_file:
        mock_log_dir.return_value = Path('/tmp/logs')
        mock_log_file.return_value = Path('/tmp/logs/calculator.log')
        
        # Instantiate calculator to trigger logging
        calculator = Calculator(CalculatorConfig())
        logging_info_mock.assert_any_call("Calculator initialized with configuration")

# Test Adding and Removing Observers

def test_add_observer(calculator):
    observer = LoggingObserver()
    calculator.add_observer(observer)
    assert observer in calculator.observers

def test_remove_observer(calculator):
    observer = LoggingObserver()
    calculator.add_observer(observer)
    calculator.remove_observer(observer)
    assert observer not in calculator.observers

# Test Setting Operations

def test_set_operation(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    assert calculator.operation_strategy == operation

# Test Performing Operations

def test_perform_operation_addition(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    result = calculator.perform_operation(2, 3)
    assert result == Decimal('5')

def test_perform_operation_validation_error(calculator):
    calculator.set_operation(OperationFactory.create_operation('add'))
    with pytest.raises(ValidationError):
        calculator.perform_operation('invalid', 3)

def test_perform_operation_operation_error(calculator):
    with pytest.raises(OperationError, match="No operation set"):
        calculator.perform_operation(2, 3)

# Test Undo/Redo Functionality

def test_undo(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.undo()
    assert calculator.history == []

def test_redo(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.undo()
    calculator.redo()
    assert len(calculator.history) == 1

# Test History Management

@patch('app.calculator.pd.DataFrame.to_csv')
def test_save_history(mock_to_csv, calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.save_history()
    mock_to_csv.assert_called_once()

@patch('app.calculator.pd.read_csv')
@patch('app.calculator.Path.exists', return_value=True)
def test_load_history(mock_exists, mock_read_csv, calculator):
    # Mock CSV data to match the expected format in from_dict
    mock_read_csv.return_value = pd.DataFrame({
        'operation': ['Addition'],
        'operand1': ['2'],
        'operand2': ['3'],
        'result': ['5'],
        'timestamp': [datetime.datetime.now().isoformat()]
    })
    
    # Test the load_history functionality
    try:
        calculator.load_history()
        # Verify history length after loading
        assert len(calculator.history) == 1
        # Verify the loaded values
        assert calculator.history[0].operation == "Addition"
        assert calculator.history[0].operand1 == Decimal("2")
        assert calculator.history[0].operand2 == Decimal("3")
        assert calculator.history[0].result == Decimal("5")
    except OperationError:
        pytest.fail("Loading history failed due to OperationError")
        
            
# Test Clearing History

def test_clear_history(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.clear_history()
    assert calculator.history == []
    assert calculator.undo_stack == []
    assert calculator.redo_stack == []

# Test Logging Setup Failure

def test_setup_logging_failure_raises_and_prints(capsys):
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        with patched_config(temp_path) as config:
            with patch('app.calculator.logging.basicConfig', side_effect=OSError("disk full")):
                with pytest.raises(OSError, match="disk full"):
                    Calculator(config=config)
    assert "Error setting up logging" in capsys.readouterr().out


# Test History Load Failure During Initialization

def test_init_load_history_failure_is_logged_not_raised():
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        with patched_config(temp_path) as config:
            with patch('app.calculator.Calculator.load_history', side_effect=OperationError("bad csv")):
                with patch('app.calculator.logging.warning') as mock_warning:
                    calc = Calculator(config=config)
    assert calc.history == []
    mock_warning.assert_called_once()
    assert "Could not load existing history" in mock_warning.call_args[0][0]


# Test History Size Trimming

def test_history_trims_to_max_history_size(calculator):
    calculator.config.max_history_size = 2
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(1, 1)
    calculator.perform_operation(2, 2)
    calculator.perform_operation(3, 3)
    assert len(calculator.history) == 2
    assert calculator.history[0].operand1 == Decimal('2')


# Test Generic Exception Wrapping in perform_operation

def test_perform_operation_wraps_generic_exception(calculator):
    mock_operation = Mock()
    mock_operation.execute.side_effect = RuntimeError("execute boom")
    calculator.set_operation(mock_operation)
    with pytest.raises(OperationError, match="Operation failed: execute boom"):
        calculator.perform_operation(1, 2)


# Test Saving Empty History

def test_save_history_with_empty_history_writes_header_only(calculator):
    calculator.history = []
    calculator.save_history()
    df = pd.read_csv(calculator.config.history_file)
    assert list(df.columns) == ['operation', 'operand1', 'operand2', 'result', 'timestamp']
    assert df.empty


@patch('app.calculator.pd.DataFrame.to_csv', side_effect=Exception("write failed"))
def test_save_history_raises_operation_error(mock_to_csv, calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    with pytest.raises(OperationError, match="Failed to save history"):
        calculator.save_history()


# Test Loading an Empty History File

def test_load_history_with_empty_csv_sets_empty_history(calculator):
    calculator.config.history_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=['operation', 'operand1', 'operand2', 'result', 'timestamp']).to_csv(
        calculator.config.history_file, index=False
    )
    calculator.load_history()
    assert calculator.history == []


# Test Loading History Failure

@patch('app.calculator.pd.read_csv', side_effect=Exception("corrupt"))
@patch('app.calculator.Path.exists', return_value=True)
def test_load_history_raises_operation_error(mock_exists, mock_read_csv, calculator):
    with pytest.raises(OperationError, match="Failed to load history"):
        calculator.load_history()


# Test get_history_dataframe

def test_get_history_dataframe_returns_expected_columns(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    df = calculator.get_history_dataframe()
    assert list(df.columns) == ['operation', 'operand1', 'operand2', 'result', 'timestamp']
    assert len(df) == 1


# Test show_history

def test_show_history_formats_entries(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    assert calculator.show_history() == ["Addition(2, 3) = 5"]


# Test Undo/Redo with Empty Stacks

def test_undo_returns_false_when_stack_empty(calculator):
    assert calculator.undo() is False


def test_redo_returns_false_when_stack_empty(calculator):
    assert calculator.redo() is False
