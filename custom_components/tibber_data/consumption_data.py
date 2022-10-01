"""Consumption data for Tibber."""
from homeassistant.util import dt as dt_util


class Consumption:
    """Consumption data."""

    def __init__(self, timestamp, cons, price, cost):
        """Initialize the data."""
        self.timestamp = timestamp
        self.cons = cons
        self.price = price
        self.cost = cost

    @property
    def day(self):
        """Return day."""
        return dt_util.as_local(self.timestamp).date()

    def __lt__(self, other):
        if self.cons is None and other.cons is None:
            return self.timestamp < other.timestamp
        if self.cons is None:
            return True
        if other.cons is None:
            return False
        return self.cons < other.cons

    def __eq__(self, other):
        return self.timestamp == other.timestamp

    def __hash__(self):
        return hash(self.timestamp)

    def __radd__(self, other):
        if self.cons is None:
            return None
        return other + self.cons

    def __str__(self):
        cons = f"{self.cons:.2f}" if self.cons else "-"
        cost = f"{self.cost:.2f}" if self.cost else "-"
        price = f"{self.price:.2f}" if self.price else "-"
        return f"Cons({self.timestamp}, {cons}, {price}, {cost})"

    def __repr__(self):
        return self.__str__()
