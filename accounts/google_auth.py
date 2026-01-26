"""
Google OAuth Authentication Utilities
"""
from decouple import config
from google.auth.transport import requests
from google.oauth2 import id_token


class GoogleOAuth:
    """Helper class for Google OAuth operations"""

    @staticmethod
    def verify_google_token(token):
        """
        Verify Google OAuth token and return user info

        Args:
            token (str): Google OAuth token from frontend

        Returns:
            dict: User information from Google

        Raises:
            ValueError: If token is invalid
        """
        try:
            client_id = config("GOOGLE_CLIENT_ID")

            # Verify the token
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), client_id)

            # Verify the issuer
            if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
                raise ValueError("Wrong issuer.")

            # Return user info
            return {
                "email": idinfo.get("email"),
                "email_verified": idinfo.get("email_verified", False),
                "name": idinfo.get("name"),
                "picture": idinfo.get("picture"),
                "given_name": idinfo.get("given_name"),
                "family_name": idinfo.get("family_name"),
                "google_id": idinfo.get("sub"),
            }

        except ValueError as e:
            # Invalid token
            raise ValueError(f"Invalid Google token: {str(e)}")
