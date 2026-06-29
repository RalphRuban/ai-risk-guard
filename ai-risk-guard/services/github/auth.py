"""
services/github/auth.py

Phase 2 GitHub App authentication layer.
Handles:
- JWT generation
- Installation token exchange
"""

import os
import time

import jwt
import requests

from utils.logger import logger


# =========================================================
# JWT GENERATION
# =========================================================

def generate_jwt(
    app_id,
    private_key
):
    """
    Generate a GitHub App JWT.
    Handles raw PEM string (including literal \n), and paths.
    """
    try:
        source = "unknown"
        # 1. Handle key if it's a file path
        if private_key and os.path.exists(private_key):
            source = f"file: {private_key}"
            with open(private_key, "r", encoding="utf-8") as f:
                private_key = f.read()
        else:
            source = "environment/raw string"

        if not private_key:
            raise ValueError("GitHub Private Key is missing or empty")

        # 2. Fix common .env newline issue (literal '\n' to actual newlines)
        if "\\n" in private_key:
            private_key = private_key.replace("\\n", "\n")

        # 3. Clean up whitespace and quotes
        private_key = private_key.strip().strip('"').strip("'")

        # SAFE DIAGNOSTICS (does not log the actual secret)
        key_preview = private_key[:20].replace("\n", "\\n")
        key_end = private_key[-20:].replace("\n", "\\n")
        logger.info(
            f"Attempting JWT encode. Source: {source}, Length: {len(private_key)}, "
            f"Start: {key_preview}..., End: ...{key_end}",
            "AUTH"
        )

        if not private_key.startswith("-----BEGIN"):
            logger.error(f"Key format error: Starts with '{private_key[:15]}'", "AUTH")

        now = int(time.time())
        payload = {
            "iat": now - 60,
            "exp": now + 540,
            "iss": app_id,
        }

        token = jwt.encode(
            payload,
            private_key,
            algorithm="RS256",
        )

        logger.info(
            "GitHub JWT generated successfully",
            "AUTH"
        )

        return token

    except Exception as error:
        logger.error(
            f"JWT generation failed: {error}",
            "AUTH"
        )
        raise RuntimeError(
            f"Failed to generate GitHub JWT: {error}"
        )


# =========================================================
# INSTALLATION TOKEN
# =========================================================

def get_installation_token(
    jwt_token,
    installation_id
):

    try:

        url = (

            "https://api.github.com/app/installations/"
            f"{installation_id}/access_tokens"
        )

        headers = {

            "Authorization":
                f"Bearer {jwt_token}",

            "Accept":
                "application/vnd.github+json",
        }

        response = requests.post(
            url,
            headers=headers,
            timeout=15,
        )

        if response.status_code not in (
            200,
            201,
        ):

            logger.error(

                "Installation token failed: "
                f"{response.status_code} "
                f"{response.text[:200]}",

                "AUTH"
            )

            raise RuntimeError(
                "GitHub installation token request failed"
            )

        data = response.json()

        token = data.get("token")

        if not token:

            logger.error(
                "GitHub token missing in response",
                "AUTH"
            )

            raise RuntimeError(
                "Installation token missing"
            )

        logger.info(
            "Installation token acquired",
            "AUTH"
        )

        return token

    except requests.RequestException as error:

        logger.error(
            f"GitHub network error: {error}",
            "AUTH"
        )

        raise RuntimeError(
            "GitHub API network failure"
        )

    except Exception as error:

        logger.error(
            f"Installation auth failed: {error}",
            "AUTH"
        )
        raise