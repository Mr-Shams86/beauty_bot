import os, sys
sys.exit(0 if os.getenv("BOT_TOKEN") else 1)
