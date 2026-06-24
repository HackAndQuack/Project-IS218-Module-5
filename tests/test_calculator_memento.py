from datetime import datetime
from decimal import Decimal

from app.calculation import Calculation
from app.calculator_memento import CalculatorMemento


def make_calculation():
    return Calculation(operation="Addition", operand1=Decimal("2"), operand2=Decimal("3"))


def test_memento_default_timestamp_is_set():
    memento = CalculatorMemento(history=[make_calculation()])
    assert isinstance(memento.timestamp, datetime)


def test_memento_to_dict():
    calc = make_calculation()
    memento = CalculatorMemento(history=[calc])
    data = memento.to_dict()
    assert data["history"] == [calc.to_dict()]
    assert data["timestamp"] == memento.timestamp.isoformat()


def test_memento_from_dict_round_trip():
    calc = make_calculation()
    memento = CalculatorMemento(history=[calc])
    data = memento.to_dict()

    restored = CalculatorMemento.from_dict(data)

    assert len(restored.history) == 1
    assert restored.history[0] == calc
    assert restored.timestamp == memento.timestamp


def test_memento_empty_history_round_trip():
    memento = CalculatorMemento(history=[])
    data = memento.to_dict()

    restored = CalculatorMemento.from_dict(data)

    assert restored.history == []
