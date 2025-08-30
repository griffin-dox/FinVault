#!/usr/bin/env python3
"""Test JWT token functionality."""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.services.token_service import create_jwt_token_pair, verify_magic_link_token, refresh_access_token
import json

def test_jwt_tokens():
    # Test JWT token creation
    token_data = {'user_id': 1, 'email': 'test@example.com', 'role': 'user'}
    tokens = create_jwt_token_pair(token_data)
    print('JWT Token Pair Created:')
    print(json.dumps(tokens, indent=2))

    # Test token verification
    payload = verify_magic_link_token(tokens['access_token'])
    print('\nAccess Token Payload:')
    print(json.dumps(payload, indent=2))

    # Test refresh token
    new_access = refresh_access_token(tokens['refresh_token'])
    print('\nNew Access Token from Refresh:')
    print(f'Success: {new_access is not None}')
    if new_access:
        new_payload = verify_magic_link_token(new_access)
        print('New Access Token Payload:')
        print(json.dumps(new_payload, indent=2))

if __name__ == '__main__':
    test_jwt_tokens()
