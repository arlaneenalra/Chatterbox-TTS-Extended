#!/usr/bin/env python3
"""
List all available API endpoints from the Gradio server.
This helps identify the correct endpoint name for the bulk client.
"""

import sys

try:
    from gradio_client import Client
except ImportError:
    print("Error: gradio_client library not found.")
    print("Please install it with: pip install gradio_client")
    sys.exit(1)

def list_endpoints(url="http://localhost:7860"):
    """List all available API endpoints from the Gradio server."""
    print(f"Connecting to Gradio server at {url}...")

    try:
        client = Client(url)
        print("✓ Successfully connected\n")

        print("="*70)
        print("AVAILABLE API ENDPOINTS")
        print("="*70)

        # View the API info
        print("\nEndpoint details:")
        print("-"*70)

        # The client has endpoint_info that shows all available endpoints
        if hasattr(client, 'endpoints'):
            for i, endpoint in enumerate(client.endpoints):
                print(f"\n{i}. Endpoint: {endpoint}")

        # Try to access view_api to get more details
        if hasattr(client, 'view_api'):
            print("\n" + "="*70)
            print("FULL API SCHEMA")
            print("="*70)
            print(client.view_api(all_endpoints=True))

        # Alternative: inspect config
        if hasattr(client, 'config'):
            print("\n" + "="*70)
            print("CONFIG INSPECTION")
            print("="*70)
            config = client.config
            if 'components' in config:
                print("\nComponents found:")
                for comp in config['components']:
                    comp_type = comp.get('type', 'unknown')
                    comp_id = comp.get('id', 'unknown')
                    print(f"  - {comp_type} (id: {comp_id})")

        print("\n" + "="*70)
        print("\nTip: Use client.view_api() to see the full API schema")
        print("="*70)

    except Exception as e:
        print(f"Error: {str(e)}")
        print("\nMake sure the Chatterbox Gradio server is running:")
        print("  python Chatter.py")
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="List Gradio API endpoints")
    parser.add_argument('--url', default='http://localhost:7860',
                       help='Gradio server URL (default: http://localhost:7860)')
    args = parser.parse_args()

    list_endpoints(args.url)
