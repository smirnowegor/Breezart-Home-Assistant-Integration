#!/usr/bin/env python3
"""Test Breezart TCP connection."""
import asyncio
import sys


async def test_breezart(host: str, port: int, password: int):
    """Test connection to Breezart."""
    print(f"Connecting to {host}:{port}...")
    
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=5.0
        )
        print("✓ TCP connection established")
        
        # Build request
        password_hex = f"{password:04x}"
        request = f"VPr07_{password_hex}"
        print(f"Sending: {request}")
        
        # Send request (without newline, like breezart-client)
        writer.write(request.encode())
        await writer.drain()
        print("✓ Request sent")
        
        # Try to read response
        print("Waiting for response (3 seconds)...")
        try:
            # Try reading until newline
            raw = await asyncio.wait_for(reader.readuntil(b'\n'), timeout=3.0)
            response = raw.decode().strip()
            print(f"✓ Response received: {response}")
        except asyncio.TimeoutError:
            print("✗ Timeout - no response received")
            # Try reading any available data
            try:
                raw = await asyncio.wait_for(reader.read(1024), timeout=1.0)
                if raw:
                    print(f"  Partial data received: {raw}")
                else:
                    print("  No data available")
            except:
                print("  No data available at all")
        except asyncio.LimitOverrunError:
            print("✗ Response too long without newline, trying to read...")
            raw = await asyncio.wait_for(reader.read(4096), timeout=1.0)
            response = raw.decode().strip()
            print(f"✓ Response received (no newline): {response}")
        
        writer.close()
        await writer.wait_closed()
        print("✓ Connection closed")
        
    except asyncio.TimeoutError:
        print("✗ Connection timeout")
        return False
    except ConnectionRefusedError:
        print("✗ Connection refused - is the device on?")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    return True


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.121"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 1560
    password = int(sys.argv[3]) if len(sys.argv) > 3 else 21579
    
    print(f"Testing Breezart at {host}:{port} with password {password}")
    print("-" * 60)
    
    asyncio.run(test_breezart(host, port, password))
