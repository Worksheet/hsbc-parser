from hsbcparser import parse_transaction_amounts

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
