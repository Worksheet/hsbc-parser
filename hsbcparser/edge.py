from decimal import Decimal, ROUND_HALF_UP
import re


def parse_transaction_amounts(text: str) -> list[Decimal]:
    """
    Parse all transaction amounts from the text, expecting numbers with 2 decimal places
    at the end of each line, optionally with commas in the number, optionally followed by
    CR or DR suffix, a double quote, and/or a comma.
    Returns a list of Decimal amounts.
    """
    # Match a number with optional commas and 2 decimal places, preceded by comma, space, or quote
    pattern = r'(?:,|\s|\")(\d{1,3}(?:,\d{3})*\.\d{2})(?:CR|DR)?\"?,?$'
    matches = re.findall(pattern, text, re.MULTILINE)

    if not matches:
        raise ValueError(f"No amounts with 2 decimal places found in text: {text}")

    # Convert matches to Decimal
    amounts = []
    for match in matches:
        cleaned_amount = match.replace(',', '')
        amount = Decimal(cleaned_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        amounts.append(amount)

    return amounts


# Test cases
test_cases = [
    "02 May 22 30 Apr 22,,MS NEWSAGENT LONDIS,LONDON SW19,101.50",
    "03 Jun 23,02 Jun 23,BKG*HOTEL AT BOOKING.C (888)850-3958,376.34",
    "19 Dec 23 18 Dec 23 IAP trainline,,+443332022222,127.29",
    "DIRECT DEBIT PAYMENT - THANK YOU,,730.00CR",
    "SOME TRANSACTION DESCRIPTION,,456.78DR",
    "QUOTED TRANSACTION,,123.45\"",
    "QUOTED CREDIT,,678.90CR\"",
    "QUOTED DEBIT,,234.56DR\"",
    "COMMA ENDING,,100.00,",
    "QUOTED COMMA,,200.00CR\",",
    "28 May 24 28 May,24 PAYMENT - THANK YOU,\"4,000.00CR\""
]

for test in test_cases:
    result = parse_transaction_amounts(test)
    print(f"Input: {test}")
    print(f"Output: {result}\n")
