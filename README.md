# Advanced Python Calculator

A REPL-based calculator built around five classic design patterns (Facade, Strategy, Factory, Observer, Memento), with pandas-backed history persistence and environment-driven configuration.

## Features

- **REPL interface** — continuous read-eval-print loop for interactive calculations
- **Six arithmetic operations** — addition, subtraction, multiplication, division, power, root
- **Undo/redo** — every calculation can be undone and redone via the Memento pattern
- **Persistent history** — calculation history is stored as a pandas `DataFrame` and saved/loaded as CSV
- **Auto-save** — an observer can save history automatically after every calculation
- **Configurable** — directory paths, history size, precision, and more are controlled via environment variables (`python-dotenv`)
- **Comprehensive error handling** — both LBYL and EAFP styles are used where each fits naturally

## Design Patterns

| Pattern | Where | What it does |
|---|---|---|
| **Facade** | `app/calculator.py` (`Calculator`) | Single entry point that hides history management, persistence, logging, and pattern wiring behind a simple API |
| **Strategy** | `app/operations.py` (`Operation` and subclasses) | Each arithmetic operation (`Addition`, `Subtraction`, ...) is an interchangeable strategy with its own `execute`/`validate_operands` |
| **Factory** | `app/operations.py` (`OperationFactory`) | Builds the right `Operation` instance from a string like `"add"`; new operations can be registered at runtime via `register_operation` |
| **Observer** | `app/history.py` (`HistoryObserver`, `LoggingObserver`, `AutoSaveObserver`) | Calculator notifies registered observers after every calculation — used for logging and auto-saving |
| **Memento** | `app/calculator_memento.py` (`CalculatorMemento`) | Snapshots of calculation history pushed onto undo/redo stacks in `Calculator.undo()` / `Calculator.redo()` |

## Error Handling: LBYL vs. EAFP

Both paradigms are used deliberately, side by side:

- **LBYL** — `InputValidator.validate_number` checks `abs(number) > config.max_input_value` *before* acting, and `Division.validate_operands` checks `b == 0` before dividing.
- **EAFP** — the same `InputValidator.validate_number` wraps the `Decimal(str(value))` conversion in a `try/except InvalidOperation`, and `Calculator.perform_operation` wraps operation execution in `try/except` to convert unexpected failures into a domain-specific `OperationError`.

## Project Structure

```
app/
├── calculator.py            # Facade — orchestrates everything below
├── calculator_repl.py       # REPL command loop
├── calculation.py           # Value object for a single calculation
├── calculator_config.py     # Environment-variable-driven configuration
├── calculator_memento.py    # Undo/redo state snapshots
├── exceptions.py            # CalculatorError hierarchy
├── history.py               # Observer pattern (logging, auto-save)
├── input_validators.py      # Input validation/sanitization
└── operations.py            # Strategy + Factory for arithmetic operations
tests/
├── test_calculations.py
├── test_calculator.py
├── test_calculator_config.py
├── test_calculator_memento.py
├── test_calculator_repl.py
├── test_exceptions.py
├── test_history.py
├── test_input_validators.py
└── test_operations.py
main.py                      # Entry point — launches the REPL
```

## Setup

### Requirements
- Python **3.13** — `pandas==2.2.3` / `numpy==2.1.2` in `requirements.txt` do not yet ship wheels (or an installable sdist) for Python 3.14, so a 3.14 interpreter will hang or fail when installing dependencies. Use 3.13 (or 3.12) until the pins are updated.

### Install

```bash
git clone <repository-url>
cd Project-IS218-Module-5

python3.13 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Configuration

Configuration is loaded via `python-dotenv` from a `.env` file in the project root (all settings have sane defaults if omitted):

| Variable | Default | Purpose |
|---|---|---|
| `CALCULATOR_BASE_DIR` | project root | Base directory for logs/history when not overridden individually |
| `CALCULATOR_MAX_HISTORY_SIZE` | `1000` | Maximum number of calculations kept in history |
| `CALCULATOR_AUTO_SAVE` | `true` | Whether history is auto-saved after each calculation |
| `CALCULATOR_PRECISION` | `10` | Decimal places used when formatting results |
| `CALCULATOR_MAX_INPUT_VALUE` | `1e999` | Largest absolute value accepted as input |
| `CALCULATOR_DEFAULT_ENCODING` | `utf-8` | Encoding used for file I/O |
| `CALCULATOR_LOG_DIR` / `CALCULATOR_LOG_FILE` | `<base_dir>/logs[/calculator.log]` | Log file location |
| `CALCULATOR_HISTORY_DIR` / `CALCULATOR_HISTORY_FILE` | `<base_dir>/history[/calculator_history.csv]` | History CSV location |

## Usage

```bash
python main.py
```

```
Calculator started. Type 'help' for commands.

Enter command: add
Enter numbers (or 'cancel' to abort):
First number: 2
Second number: 3

Result: 5
```

### Commands

| Command | Description |
|---|---|
| `add`, `subtract`, `multiply`, `divide`, `power`, `root` | Perform the named operation on two prompted numbers |
| `history` | Show all calculations performed this session |
| `clear` | Clear history and the undo/redo stacks |
| `undo` | Undo the last calculation |
| `redo` | Redo the last undone calculation |
| `save` | Save history to the configured CSV file |
| `load` | Reload history from the configured CSV file |
| `help` | List available commands |
| `exit` | Save history and quit |

While entering operands, type `cancel` to abort the current operation.

## Testing

```bash
pytest --cov=app --cov-report=term-missing
```

The suite achieves 100% statement coverage across `app/`. CI (`.github/workflows/tests.yml`) runs the same command on every push/PR to `main` and fails the build if coverage drops below 100% (`--cov-fail-under=100`).
