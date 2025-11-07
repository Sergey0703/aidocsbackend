#!/usr/bin/env python3
"""
Analyze extraction quality from Vehicle Registration Certificate
"""
import os
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv('rag_indexer/.env')

# Expected data from Vehicle Registration Certificate
EXPECTED_DATA = {
    'registration_number': '231-D-54321',
    'first_registration_date': '25/07/2023',
    'owner_name': 'Murphy Builders Ltd.',
    'owner_address': 'Unit 15, Business Park, Dublin 12, Co. Dublin',
    'make': 'FORD',
    'model': 'TRANSIT CONNECT',
    'vehicle_category': 'N1 (GOODS VEHICLE)',
    'vin': 'WF0XXXXXXXXXXXXX',
    'max_mass': '2200 KG',
    'engine_capacity': '1499',
    'date_of_issue': '01/08/2023',
    'certificate_number': 'VRC987654321'
}

def main():
    conn_str = os.getenv('SUPABASE_CONNECTION_STRING')
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()

    print('='*70)
    print('EXTRACTION QUALITY ANALYSIS')
    print('='*70)

    # Get chunks
    cur.execute('''
        SELECT
            metadata->>'text' as text
        FROM vecs.documents
        ORDER BY id
    ''')

    chunks = cur.fetchall()

    # Combine all text
    all_text = ' '.join([c[0] if c[0] else '' for c in chunks])

    print(f'\nTotal extracted text length: {len(all_text)} characters')
    print(f'Number of chunks: {len(chunks)}')

    print('\n' + '='*70)
    print('CHECKING EXPECTED DATA FIELDS')
    print('='*70)

    found_count = 0
    missing_count = 0

    for field, expected_value in EXPECTED_DATA.items():
        # Check if value exists in text
        if expected_value.lower() in all_text.lower():
            print(f'[+] {field}: FOUND - "{expected_value}"')
            found_count += 1
        else:
            print(f'[-] {field}: MISSING - Expected "{expected_value}"')
            missing_count += 1

    print('\n' + '='*70)
    print('EXTRACTION QUALITY SUMMARY')
    print('='*70)
    print(f'Found: {found_count}/{len(EXPECTED_DATA)} fields ({found_count/len(EXPECTED_DATA)*100:.1f}%)')
    print(f'Missing: {missing_count}/{len(EXPECTED_DATA)} fields')

    # Show sample of extracted text
    print('\n' + '='*70)
    print('SAMPLE OF EXTRACTED TEXT (first 800 chars)')
    print('='*70)
    print(all_text[:800])
    if len(all_text) > 800:
        print('...')

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
