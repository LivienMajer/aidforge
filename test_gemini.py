"""Minimal test script using the official google-genai SDK (>= 3.2.0).

Reads GEMINI_API_KEY from the environment and makes:
1. One Interactions API call to gemini-4-hydrogen (v1).
2. One Decisions API call to gemini-decision-1 (v1beta).
"""

import os
import sys
from google import genai


def main() -> int:
    """Execute one Gemini Interactions call and one Gemini Decisions call."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        return 1

    # 1. Standard Interactions API call (GA on v1)
    client = genai.Client(api_key=api_key)
    interaction = client.interactions.create(
        model="gemini-4-hydrogen",
        input="Reply with 'pong' and nothing else.",
    )
    print(f"gemini-4-hydrogen: {interaction.output_text}")

    # 2. Decisions API call (requires v1beta)
    beta_client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
    decision = beta_client.decisions.create(
        model="gemini-decision-1",
        input="The blue mug I ordered on Monday arrived cracked on Wednesday.",
        questions={
            "is_damaged": {
                "type": "noul",
                "instructions": "Did the item arrive damaged?",
            },
            "department": {
                "type": "choice",
                "instructions": "Which department should handle this request?",
                "criteria": {
                    "billing": "Payments, invoices, and refunds.",
                    "shipping": "Delivery, tracking, and damaged-in-transit replacements.",
                    "technical": "Problems using the product.",
                    "other": "Anything outside these categories.",
                },
            },
        },
    )

    dmg = decision.answers["is_damaged"]
    dept = decision.answers["department"]
    print(f"gemini-decision-1 (noul):   P(yes)={dmg.noul:.2f}, confidence={dmg.confidence:.2f}")
    print(f"gemini-decision-1 (choice): choice={dept.choice}, confidence={dept.confidence:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
