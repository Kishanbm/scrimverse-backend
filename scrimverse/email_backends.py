import socket
from django.core.mail.backends.smtp import EmailBackend

class IPv4EmailBackend(EmailBackend):
    """
    Custom SMTP backend that forces IPv4 to avoid 'Network is unreachable' 
    errors often caused by IPv6 issues on certain hosting environments like Render.
    """
    def _open(self):
        if self.connection:
            return False
        
        # Original socket.getaddrinfo returns both IPv4 and IPv6
        # We wrap it to only return IPv4
        original_getaddrinfo = socket.getaddrinfo
        
        def forced_ipv4_getaddrinfo(*args, **kwargs):
            # Force AF_INET (IPv4)
            return original_getaddrinfo(args[0], args[1], socket.AF_INET, *args[3:], **kwargs)
        
        try:
            socket.getaddrinfo = forced_ipv4_getaddrinfo
            return super()._open()
        finally:
            socket.getaddrinfo = original_getaddrinfo
