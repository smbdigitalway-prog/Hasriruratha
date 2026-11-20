# tiny local SMTP server: saves each email as a file so tests can read OTP codes
import time, pathlib, asyncio
from aiosmtpd.controller import Controller
OUT = pathlib.Path("/opt/mailcatch/mail")
class H:
    async def handle_DATA(self, server, session, envelope):
        name = "%d-%s.eml" % (time.time_ns(), envelope.rcpt_tos[0])
        (OUT / name).write_bytes(envelope.content)
        return "250 OK"
c = Controller(H(), hostname="127.0.0.1", port=1025); c.start()
import threading; threading.Event().wait()
