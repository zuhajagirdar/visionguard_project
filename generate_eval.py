import os
import json

manifest = []

cases = [
    # id, filename, text_content, exp_amount, exp_date, exp_merchant, is_pdf, is_corrupt
    ('case_01', 'case_01.pdf', 'Amount: 12.50\nDate: 2026-01-01\nMerchant: Starbucks', '12.50', '2026-01-01', 'Starbucks', True, False),
    ('case_02', 'case_02.pdf', 'Total Amount: .99\nDate: 2026-02-15\nMerchant: Target', '.99', '2026-02-15', 'Target', True, False),
    ('case_03', 'case_03.pdf', 'Amount: 100\nDate: 03/15/2026\nMerchant: Best Buy', '100', '03/15/2026', 'Best Buy', True, False),
    ('case_04', 'case_04.pdf', 'Amount: 1,234.56\nDate: 2026-04-10\nMerchant: Apple Store', '1,234.56', '2026-04-10', 'Apple Store', True, False),
    ('case_05', 'case_05.pdf', 'Date: 2026-05-20\nMerchant: Walmart', '0.0', '2026-05-20', 'Walmart', True, False),
    ('case_06', 'case_06.pdf', 'Amount: 99.99\nMerchant: Amazon', '99.99', 'Unknown', 'Amazon', True, False),
    ('case_07', 'case_07.pdf', 'Amount: 50.00\nDate: 2026-07-01', '50.00', '2026-07-01', 'Unknown', True, False),
    ('case_08', 'case_08.pdf', 'amount: 12.34\ndate: 2026-08-08\nmerchant: shell', '12.34', '2026-08-08', 'shell', True, False),
    ('case_09', 'case_09.pdf', 'AMOUNT: 88.88\nDATE: 2026-09-09\nMERCHANT: EXXON', '88.88', '2026-09-09', 'EXXON', True, False),
    ('case_10', 'case_10.pdf', 'Amount: 10.00 Date: 2026-10-10 Merchant: Subway', '10.00', '2026-10-10', 'Subway', True, False),
    ('case_11', 'case_11.pdf', 'Amount  : 20.00\nDate  : 2026-11-11\nMerchant  : McDonalds', '20.00', '2026-11-11', 'McDonalds', True, False),
    ('case_12', 'case_12.pdf', 'Garbage text\nAmount: 30.00\nMore garbage\nDate: 2026-12-12\nMerchant: KFC', '30.00', '2026-12-12', 'KFC', True, False),
    ('case_13', 'case_13.pdf', 'Amount: 40.00\nDate: 2027-01-01\nMerchant: Wendys', '40.00', '2027-01-01', 'Wendys', True, False),
    ('case_14', 'case_14.png', '', '0.0', 'Unknown', 'Unknown', False, True),
    ('case_15', 'case_15.pdf', 'Amount: 500\nDate: 2027-02-28\nMerchant: Delta', '500', '2027-02-28', 'Delta', True, False)
]

for c_id, fname, text, e_amt, e_date, e_merch, is_pdf, is_corrupt in cases:
    path = os.path.join('eval/data', fname)
    if is_corrupt:
        with open(path, 'wb') as f:
            f.write(b'this is not a valid image or pdf')
    elif is_pdf:
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(path)
        for i, line in enumerate(text.split('\n')):
            c.drawString(100, 750 - (i*15), line)
        c.save()
        
    manifest.append({
        'case_id': c_id,
        'document_path': path,
        'expected_amount': e_amt,
        'expected_date': e_date,
        'expected_merchant': e_merch,
        'expected_error': is_corrupt
    })

with open('eval/manifest.json', 'w') as f:
    json.dump(manifest, f, indent=2)

print('Evaluation data regenerated as PDFs.')
