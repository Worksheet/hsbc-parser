#!/usr/bin/env python3
import os
import re
from pathlib import Path
from typing import NamedTuple, List, Iterator, Optional, Literal
from datetime import date, datetime
from subprocess import check_output, CalledProcessError
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd

# --- Configuration ---
TABULA_PATH = os.environ.get("TABULA_JAR_PATH")
if not TABULA_PATH:
    raise EnvironmentError(
        "Environment variable TABULA_JAR_PATH is not set. "
        "Please set it to the path of the Tabula JAR file."
    )


# --- Data Models ---
class Transaction(NamedTuple):
    received: date
    date: date
    amount: Decimal
    crdr: Literal["CR", "DR", "Payment"]
    is_contactless: bool
    details: str


class NullTransaction(NamedTuple):
    received: Optional[date]
    date: Optional[date]
    amount: Optional[Decimal]
    crdr: Optional[str]
    is_contactless: Optional[bool]
    details: str


# --- Core Parsing Functions ---
def extract_dates(text: str) -> tuple[list[str], Optional[int], Optional[int]]:
    """
    Extract date strings in 'DD Mon YY' format from the text, allowing commas.
    Returns (list of date strings, first index, last index).
    """
    text_normalised = text.replace(",", " ").replace('"', "")
    pattern = r"\b\d{1,2} [A-Za-z]{3} \d{2}\b"
    potential_matches = [(m.group(), m.start(), m.end() - 1)
                         for m in re.finditer(pattern, text_normalised)]

    valid_months = {"Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"}

    valid_matches = [
        (txt, start, end)
        for txt, start, end in potential_matches
        if txt.split()[1].rstrip(",").capitalize() in valid_months
    ]

    if not valid_matches:
        return [], None, None

    date_strs = [m[0] for m in valid_matches]
    return date_strs, valid_matches[0][1], valid_matches[-1][2]


def parse_date(date_str: str) -> datetime:
    """Parse 'dd mmm yy' into datetime."""
    try:
        return datetime.strptime(date_str, "%d %b %y")
    except ValueError as e:
        raise ValueError(f"Unable to parse date '{date_str}': {e}") from e


def parse_transaction_amounts(text: str) -> list[tuple[Decimal, str]]:
    """
    Extract transaction amounts and CR/DR suffix if present.
    Returns list of (amount, crdr) tuples.
    """
    pattern = r'(?:,|\s|\")(\d{1,3}(?:,\d{3})*\.\d{2})(CR|DR)?\"?,?$'
    matches = re.findall(pattern, text, re.MULTILINE)

    if not matches:
        raise ValueError(f"No amounts with 2 decimal places found in text: {text}")

    results = []
    for num_str, suffix in matches:
        cleaned = num_str.replace(",", "")
        amount = Decimal(cleaned).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        crdr = suffix or "Payment"
        results.append((amount, crdr))
    return results


def try_transaction(line: str) -> Iterator[Transaction | NullTransaction]:
    """
    Try to parse a line into Transaction(s). Returns a generator.
    Yields either Transaction or NullTransaction.
    """
    re_dates, first_ix, last_ix = extract_dates(line)
    if not re_dates:
        yield NullTransaction(None, None, None, None, None, line)
        return

    if len(re_dates) != 2:
        raise ValueError(f"Expected 2 dates, found {len(re_dates)}: {re_dates}")

    if first_ix != 0:
        raise ValueError(f"Unexpected received-date placement: {line}")

    rdate, ddate = [parse_date(d) for d in re_dates]

    remaining_line = line[last_ix + 1:]
    amounts = parse_transaction_amounts(remaining_line)
    if len(amounts) != 1:
        raise ValueError(f"Expected 1 amount, found {len(amounts)}: {line}")

    amount, crdr = amounts[0]

    if crdr not in ['CR', 'DR', 'Payment']:
        raise ValueError(f'Unrecognised payment type string: {crdr}')

    # Integrity check: amounts shouldn't be absurd
    if amount > Decimal("100000.00"):
        raise ValueError(f"Unusually large amount: {amount} in line: {line}")

    str_amount = f"{amount:,}"
    amount_start = remaining_line.find(str_amount)
    if amount_start == -1:
        raise ValueError(f"Could not locate amount text in line: {line}")

    amount_end = amount_start + len(str_amount)
    details = (remaining_line[:amount_start] + remaining_line[amount_end:]).replace(",", " ").strip()

    is_contactless = details.startswith(")))")

    yield Transaction(
        received=rdate.date(),
        date=ddate.date(),
        amount=amount,
        crdr=crdr,
        is_contactless=is_contactless,
        details=details,
    )


# --- I/O and orchestration ---
def yield_credit_infos(fname: str | Path) -> Iterator[Transaction | NullTransaction]:
    """
    Run Tabula on a PDF and yield parsed transactions.
    """
    cmd = [
        "java",
        "-jar", TABULA_PATH,
        "--pages", "all",
        "--silent",
        str(fname),
    ]

    try:
        res = check_output(cmd).decode("windows-1252")
    except FileNotFoundError as e:
        raise RuntimeError("Java not found or TABULA_JAR_PATH invalid") from e
    except CalledProcessError as e:
        raise RuntimeError(f"Tabula command failed: {e}") from e

    for line in res.splitlines():
        yield from try_transaction(line)


def get_credit_infos(fname: str | Path) -> List[Transaction | NullTransaction]:
    """Convenience wrapper to return all transactions from a single file."""
    return list(yield_credit_infos(fname))


def make_dataframe_from_path(pdf_folder_path: str | Path) -> pd.DataFrame:
    """
    Build a dataframe of transactions from all PDFs in a folder.
    """
    pdf_folder = Path(pdf_folder_path)
    pdfs = sorted(pdf_folder.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No PDF files found in {pdf_folder}")

    rows = []
    for pdf_path in pdfs:
        sdate = datetime.strptime(pdf_path.name[:10], "%Y-%m-%d").date()
        for t in get_credit_infos(pdf_path):
            rows.append({
                "statement_fpath": pdf_path,
                "statement_date": sdate,
                "received_date": t.received,
                "transaction_date": t.date,
                "amount": float(t.amount) if t.amount is not None else None,
                "crdr": t.crdr,
                "is_contactless": t.is_contactless,
                "details": t.details,
            })

    return pd.DataFrame(rows)
