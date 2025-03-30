#!/usr/bin/env python3
import os
import re
from pathlib import Path
from typing import NamedTuple, List
from datetime import date, datetime
from subprocess import check_output
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd

TABULA_PATH = os.environ['TABULA_JAR_PATH']

class Transaction(NamedTuple):
    received: date
    date: date
    amount: Decimal
    details: str

class NullTransaction(NamedTuple):
    received: None
    date: None
    amount: None
    details: str

def extract_dates(text: str) -> tuple[list[str], int | None, int | None]:
    """
    Extract date strings in 'DD Mon YY' format from the text, allowing for optional comma
    between month and year (e.g., '14 Aug 23' or '14 Aug,23').
    Only accepts standard English month abbreviations (Jan, Feb, Mar, etc.).
    Returns a tuple of (date_strings, first_index, last_index).
    """
    # Sometimes there is a comma inside the date, ideally this would be handled somewhere more obvious.
    text_normalised = text.replace(',', ' ').replace('"', '')
    pattern = r"\b\d{1,2} [A-Za-z]{3} \d{2}\b"
    potential_matches = [(match.group(), match.start(), match.end() - 1) for match in re.finditer(pattern, text_normalised)]

    # Valid month abbreviations
    valid_months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Filter matches to ensure month is valid
    valid_matches = []
    for match_text, start, end in potential_matches:
        # Extract just the month portion (should be the second word)
        parts = match_text.split()
        if len(parts) >= 2:
            month_part = parts[1].rstrip(',')
            if month_part in valid_months or month_part.capitalize() in valid_months:
                valid_matches.append((match_text, start, end))

    date_strs = [match[0] for match in valid_matches]
    if valid_matches:
        first_ix = valid_matches[0][1]  # Start index of first valid date
        last_ix = valid_matches[-1][2]  # End index of last valid date
    else:
        first_ix = last_ix = None

    return date_strs, first_ix, last_ix


def parse_date(date_str: str) -> datetime:
    """
    Parse a date string in 'dd mmm yy' format into a datetime object.
    Raises ValueError if parsing fails.
    """
    try:
        return datetime.strptime(date_str, "%d %b %y")
    except ValueError:
        raise ValueError(f"Unable to parse date: {date_str}")

def parse_transaction_amounts(text: str) -> list[Decimal]:
    """
    Parse all transaction amounts from the text, expecting numbers with 2 decimal places,
    possibly with commas and optional CR/DR suffix, and potentially enclosed in quotes.
    Returns a list of Decimal amounts.
    """
    # Match numbers with 2 decimal places, optional commas, optional CR/DR suffix, and optional quotes
    pattern = r'"?(\d{1,3}(?:,\d{3})*\.\d{2}(?:CR|DR)?)"?'
    matches = re.findall(pattern, text)

    if not matches:
        raise ValueError(f"No amounts with 2 decimal places found in text: {text}")

    # Clean and convert matches to Decimal
    amounts = []
    for match in matches:
        cleaned_amount = match.replace(',', '').rstrip('CR').rstrip('DR')
        amount = Decimal(cleaned_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        amounts.append(amount)

    return amounts

def yield_credit_infos(fname: str):
    CMD = [
        'java',
        '-jar', TABULA_PATH,
        '--pages', 'all',
        '--silent',
        fname,
    ]
    res = check_output(CMD).decode('windows-1252')

    def try_transaction(line: str):
        """Given a line from a credit card statement, create a Transaction where the line can be parsed as
        a transaction, returns None otherwise."""
        re_dates, first_char_ix, last_char_ix = extract_dates(line)
        if len(re_dates) == 0:
            yield NullTransaction(
                received=None,
                date=None,
                amount=None,
                details=line,
            )
            return
        assert len(re_dates) == 2, f'Wrong number of dates: {re_dates}'
        assert first_char_ix == 0, f'Unexpected received date placement on line: {line}'
        rdate, ddate = [parse_date(dt_str) for dt_str in re_dates]


        remaining_line = line[last_char_ix + 1:]
        amounts = parse_transaction_amounts(remaining_line)
        assert len(amounts) == 1, f'Unexpected number of amounts on line {line}'
        amount = amounts[0]

        # Extract details: remove dates and full amount string (including CR/DR if present), then strip
        str_amount = str(amount)
        amount_start, amount_end = remaining_line.find(str_amount), remaining_line.find(str_amount) + len(str_amount)
        details = remaining_line[:amount_start] + remaining_line[amount_end:]
        details = details.replace(',', ' ').strip()

        yield Transaction(
            received=rdate.date(),
            date=ddate.date(),
            amount=amount,
            details=details,
        )

    for line in res.splitlines():
        for t in try_transaction(line):
            yield t

def get_credit_infos(fname: str) -> List[Transaction]:
    return list(yield_credit_infos(fname))


def make_dataframe_from_path(pdf_folder_path: str | Path):
    res = sorted(Path(pdf_folder_path).glob('*.pdf'))
    assert len(res) > 0
    data = []
    for pdf_path in res:
        print(pdf_path)
        sdate = datetime.strptime(pdf_path.name[:10], "%Y-%m-%d").date()
        transactions = get_credit_infos(pdf_path)
        for t in transactions:
            data.append({
                'statement_fpath': pdf_path,
                'statement_date': sdate,
                'received_date': t.received,
                'transaction_date': t.date,
                'amount': t.amount,
                'details': t.details
            })
    return pd.DataFrame(data)