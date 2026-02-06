"""X (Twitter) posting service using tweepy."""

from pathlib import Path

import tweepy

from cloud_loader.config import settings


def _get_client() -> tweepy.Client:
    """Create authenticated X API v2 client."""
    if not all([
        settings.x_api_key,
        settings.x_api_secret,
        settings.x_access_token,
        settings.x_access_token_secret,
    ]):
        raise ValueError(
            "X API keys not configured. "
            "Set X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET in .env"
        )
    return tweepy.Client(
        consumer_key=settings.x_api_key,
        consumer_secret=settings.x_api_secret,
        access_token=settings.x_access_token,
        access_token_secret=settings.x_access_token_secret,
    )


def _get_api_v1() -> tweepy.API:
    """Create authenticated X API v1.1 client (needed for media uploads)."""
    auth = tweepy.OAuth1UserHandler(
        settings.x_api_key,
        settings.x_api_secret,
        settings.x_access_token,
        settings.x_access_token_secret,
    )
    return tweepy.API(auth)


def post_tweet(text: str, media_paths: list[str] | None = None) -> dict:
    """Post a tweet, optionally with images.

    Args:
        text: Tweet text (max 280 chars).
        media_paths: Optional list of image file paths to attach.

    Returns:
        dict with tweet id and url.
    """
    client = _get_client()
    media_ids = None

    if media_paths:
        api_v1 = _get_api_v1()
        media_ids = []
        for path in media_paths:
            if not Path(path).exists():
                raise FileNotFoundError(f"Media file not found: {path}")
            media = api_v1.media_upload(path)
            media_ids.append(media.media_id)

    response = client.create_tweet(text=text, media_ids=media_ids)
    tweet_id = response.data["id"]
    # X doesn't return the username in create_tweet, construct URL with id only
    return {
        "id": tweet_id,
        "url": f"https://x.com/i/status/{tweet_id}",
        "text": text,
    }


def reply_to_tweet(tweet_id: str, text: str) -> dict:
    """Reply to an existing tweet.

    Args:
        tweet_id: The ID of the tweet to reply to.
        text: Reply text.

    Returns:
        dict with reply tweet id and url.
    """
    client = _get_client()
    response = client.create_tweet(
        text=text,
        in_reply_to_tweet_id=tweet_id,
    )
    reply_id = response.data["id"]
    return {
        "id": reply_id,
        "url": f"https://x.com/i/status/{reply_id}",
        "text": text,
    }


def delete_tweet(tweet_id: str) -> bool:
    """Delete a tweet by ID."""
    client = _get_client()
    client.delete_tweet(tweet_id)
    return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m cloud_loader.services.x_poster 'Your tweet text'")
        print("       python -m cloud_loader.services.x_poster 'Text' image1.png image2.png")
        sys.exit(1)

    tweet_text = sys.argv[1]
    images = sys.argv[2:] if len(sys.argv) > 2 else None

    result = post_tweet(tweet_text, media_paths=images)
    print(f"Posted: {result['url']}")
