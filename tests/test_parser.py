import pytest
from decimal import Decimal
from hsbcparser.parse import parse_transaction_amounts


@pytest.mark.parametrize(
    "text,expected",
    [
        (
                "02 May 22 30 Apr 22,,MS NEWSAGENT LONDIS,LONDON SW19,101.50",
                [Decimal("101.50")],
        ),
        (
                "03 Jun 23,02 Jun 23,BKG*HOTEL AT BOOKING.C (888)850-3958,376.34",
                [Decimal("376.34")],
        ),
        (
                "19 Dec 23 18 Dec 23 IAP trainline,,+443332022222,127.29",
                [Decimal("127.29")],
        ),
        (
                "DIRECT DEBIT PAYMENT - THANK YOU,,730.00CR",
                [Decimal("730.00")],
        ),
        (
                "SOME TRANSACTION DESCRIPTION,,456.78DR",
                [Decimal("456.78")],
        ),
        (
                "QUOTED TRANSACTION,,123.45\"",
                [Decimal("123.45")],
        ),
        (
                "QUOTED CREDIT,,678.90CR\"",
                [Decimal("678.90")],
        ),
        (
                "QUOTED DEBIT,,234.56DR\"",
                [Decimal("234.56")],
        ),
        (
                "COMMA ENDING,,100.00,",
                [Decimal("100.00")],
        ),
        (
                "QUOTED COMMA,,200.00CR\",",
                [Decimal("200.00")],
        ),
        (
                "28 May 24 28 May,24 PAYMENT - THANK YOU,\"4,000.00CR\"",
                [Decimal("4000.00")],
        ),
    ],
)
def test_parse_transaction_amounts(text, expected):
    """Ensure parse_transaction_amounts extracts correct Decimal amounts."""
    result = parse_transaction_amounts(text)
    assert result == expected, f"Failed for input: {text}"


def test_parse_transaction_amounts_raises_on_no_match():
    """Ensure ValueError is raised when no amounts are found."""
    with pytest.raises(ValueError, match="No amounts with 2 decimal places"):
        parse_transaction_amounts("This line has no amount")
