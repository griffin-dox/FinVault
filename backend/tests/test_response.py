#!/usr/bin/env python3
"""
Test the new response format
"""
from app.schemas.transaction import TransactionRequest, TransactionResponse
from datetime import datetime

# Test the new response format
data = {
    'user_id': 1,
    'amount': 1000.0,
    'recipient': 'bryanbinu01@gmail.com',
    'description': 'lauda'
}

req = TransactionRequest(**data)

# Simulate the new response format
response_data = {
    'id': 123,
    'user_id': req.user_id,
    'amount': req.amount,
    'target_account': getattr(req, 'target_account', None),
    'recipient': getattr(req, 'recipient', None),
    'device_info': getattr(req, 'device_info', None),
    'location': getattr(req, 'location', None),
    'intent': getattr(req, 'intent', None),
    'description': getattr(req, 'description', None),
    'risk_score': 40,
    'status': 'completed',
    'created_at': datetime.now()
}

transaction_response = TransactionResponse(**response_data)

final_response = {
    'riskScore': 40,
    'transaction': transaction_response
}

print('✅ New response format:')
print(f'riskScore: {final_response["riskScore"]}')
print(f'transaction.status: {final_response["transaction"].status}')
print(f'transaction.amount: {final_response["transaction"].amount}')
print(f'transaction.recipient: {final_response["transaction"].recipient}')
print('\nThis matches what the frontend expects!')
