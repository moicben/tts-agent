"""
Logique de l'agent conversationnel (FR) avec GPT-4o-mini.

Fonctions principales:
- llm_generate(prompt): interroge GPT-4o-mini via le SDK OpenAI
- respond(user_text): renvoie la réponse (LLM ou fallback)
"""

from typing import Optional

try:
    # SDK OpenAI (python-openai >= 1.0)
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # géré au runtime


def llm_generate(prompt: str) -> Optional[str]:
    """Produit une réponse en français en utilisant GPT-4o-mini.

    Requiert OPENAI_API_KEY dans l'environnement.
    Retourne None en cas d'erreur pour laisser le fallback s'appliquer.
    """
    if not prompt or not prompt.strip():
        return None
    try:
        if OpenAI is None:
            return None
        client = OpenAI()
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Tu es un assistant vocal francophone, réponds brièvement en français."},
                {"role": "user", "content": prompt},
            ],
        )
        text = resp.choices[0].message.content if resp.choices else None
        return text.strip() if text else None
    except Exception:
        return None


def respond(user_text: str) -> str:
    """Retourne la réponse texte de l'agent."""
    if not user_text or not user_text.strip():
        return "Je n'ai rien entendu. Peux-tu répéter ?"

    # Essai LLM d'abord
    llm_response = llm_generate(user_text)
    if llm_response:
        return llm_response

    # Fallback logique simple (écho)
    return f"Tu as dit : {user_text.strip()}"




