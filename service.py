import uvicorn
from pyngrok import ngrok
from config import *
import sys


def setup_ngrok():
   try:
       ngrok.set_auth_token(NGROK_TOKEN)
       
       # Clean existing tunnels silently
       for tunnel in ngrok.get_tunnels():
           ngrok.disconnect(tunnel.public_url)

       http_tunnel = ngrok.connect(
           5001,
           subdomain="refined-magnetic-buck", 
           bind_tls=True
       )
       print(f"\nNgrok URL: {http_tunnel.public_url}\n")
       return http_tunnel.public_url

   except Exception as e:
       sys.exit(1)

def start_service():
    public_url = setup_ngrok()
       
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5001,
    )

if __name__ == "__main__":
   start_service()