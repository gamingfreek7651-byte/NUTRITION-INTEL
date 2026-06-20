import http.server
import socketserver
import os
import sys

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

def main():
    # Force socket reuse so running the script repeatedly does not cause "Address already in use" errors
    socketserver.TCPServer.allow_reuse_address = True
    
    print("==================================================================")
    print("  Amazon Nutrition Supplement Competitive Intelligence Platform  ")
    print("==================================================================")
    print("  Serving files from: " + DIRECTORY)
    print("  Dashboard is running locally at:")
    print(f"\n      http://localhost:{PORT}\n")
    print("  Press Ctrl+C to stop the server.")
    print("==================================================================")
    
    try:
        with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        sys.exit(0)
    except Exception as e:
        print(f"\nError occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
