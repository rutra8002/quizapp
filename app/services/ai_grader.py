import re

from google import genai


class AIModelUnavailableError(Exception):
    """Raised when the AI model/service is temporarily unavailable (HTTP 503)."""

class AIModelUnavailableError(Exception):
    """Raised when the AI model/service is temporarily unavailable (HTTP 503)."""


class AIRateLimitError(Exception):
    """Raised when the AI service quota/rate limit is exceeded (HTTP 429)."""


class AIGrader:
    def __init__(self, api_key: str | None, model_name: str = "gemini-3-flash-preview"):
        self.model_name = model_name
        self.client = genai.Client(api_key=api_key) if api_key else None

    def score(self, question_text: str, ref_answer: str, user_answer: str) -> int:
        """
        Ask Gemini to grade the user's answer 0-10.
        Returns an int in [0, 10]. Falls back to exact match if no API client is configured.
        """
        if not self.client:
            return 10 if user_answer.strip().lower() == str(ref_answer).strip().lower() else 0

        prompt = (
            "You are a strict grader. Grade the user's answer to the question against the reference answer.\n"
            "- Return only a single integer from 0 to 10 inclusive.\n"
            "- 0 means completely incorrect, 10 means fully correct.\n"
            f"Question: {question_text}\n"
            f"Reference answer: {ref_answer}\n"
            f"User answer: {user_answer}\n"
            "Score (0-10):"
        )

        try:
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            raw = (response.text or "").strip()
            match = re.search(r"(-?\d+)", raw)
            score = int(match.group(1)) if match else 0
        except Exception as error:
            msg = str(error) or ""
            status_code = getattr(error, "status_code", None) or getattr(error, "code", None)
            if status_code == 503:
                raise AIModelUnavailableError(msg)
            if status_code == 429:
                raise AIRateLimitError(msg)
            print(error)
            score = 0

        return max(0, min(10, score))

