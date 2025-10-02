import argparse
import os
import sys
import subprocess
import unicodedata
import re
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

from stt_openai import record_until_silence, transcribe_wave
from openai import OpenAI


def normalize_text(text: str) -> str:
    if not text:
        return ""
    # minuscules + suppression diacritiques + ponctuation simple
    text = text.lower()
    text = (
        unicodedata.normalize("NFD", text)
        .encode("ascii", "ignore")
        .decode("utf-8", "ignore")
    )
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_manifest(manifest_path: Path) -> Dict[str, Any]:
    """
    Charge le manifest JSON et retourne:
    {
        "records": [ {id, path, intent}, ...],
        "id_to_path": { id: absolute_path_str }
    }
    """
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest introuvable: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = data.get("records", [])
    id_to_path: Dict[str, str] = {}
    base_dir = manifest_path.parent
    for rec in records:
        rec_id = rec.get("id")
        rec_rel_path = rec.get("path")
        if rec_id and rec_rel_path:
            abs_path = (base_dir.parent / Path(rec_rel_path)).resolve()
            id_to_path[rec_id] = str(abs_path)

    return {"records": records, "id_to_path": id_to_path}


def play_audio(filepath: Path) -> None:
    """
    Lecture simple d'un fichier audio (m4a/mp3/etc.) via `afplay` sur macOS.
    """
    try:
        subprocess.run(["afplay", str(filepath)], check=True)
    except FileNotFoundError:
        print("Erreur: 'afplay' est introuvable. Sur macOS, il devrait être présent par défaut.")
    except subprocess.CalledProcessError:
        print("Erreur: impossible de lire le fichier avec 'afplay'.")


def play_record(record_id: str, id_to_path: Dict[str, str]) -> bool:
    path_str = id_to_path.get(record_id)
    if not path_str:
        print(f"[AUDIO] Introuvable pour record_id='{record_id}'.")
        return False
    path = Path(path_str)
    if not path.exists():
        print(f"[AUDIO] Fichier manquant: {path}")
        return False
    print(f"Lecture du segment: {path.name}")
    play_audio(path)
    return True


def extract_email(text: str) -> Optional[str]:
    if not text:
        return None
    # Simple regex email
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return m.group(0) if m else None


def detect_presentation(text: str) -> bool:
    if not text:
        return False
    norm = normalize_text(text)
    return bool(re.search(r"\b(je m appelle|je suis|moi c est)\b", norm))


def decide_next_action(
    last_user_text: str,
    memory: Dict[str, Any],
    records_for_prompt: List[Dict[str, str]],
    allowed_record_ids: List[str],
    client: Optional[OpenAI] = None,
) -> Dict[str, Any]:
    """
    Appelle gpt-5-nano et renvoie un dict {action, record_id, variables:{email}, reason}.
    Utilise JSON strict si possible; fallback à parsing tolérant sinon.
    """
    client = client or OpenAI()

    system_prompt = (
        "Tu es un agent de rendez-vous. Objectif: inviter l’interlocuteur au dashboard. "
        "Pas de planification étape par étape. À chaque tour, choisis l’enregistrement (record_id) le plus utile pour progresser. "
        "Si un email complet est détecté, propose action=do_tool avec variables.email. "
        "Si aucun enregistrement ne convient, propose ask_clarification. "
        "Réponds STRICTEMENT en JSON suivant le schéma demandé. "
        "IMPORTANT: ne propose qu'un record_id appartenant à allowed_record_ids. Si la liste est vide, propose ask_clarification."
    )

    user_payload = {
        "last_user_text": last_user_text or "",
        "memory_flags": {
            "greeted": bool(memory.get("greeted")),
            "presentation_received": bool(memory.get("presentation_received")),
            "email_captured": bool(memory.get("email_captured")),
            "invite_sent": bool(memory.get("invite_sent")),
        },
        "records": [{"id": r.get("id"), "intent": r.get("intent", "")} for r in records_for_prompt],
        "allowed_record_ids": list(allowed_record_ids),
        "schema": {
            "action": "play_record | do_tool | ask_clarification | end",
            "record_id": "string | null",
            "variables": {"email": "string | null"},
            "reason": "string"
        },
    }

    try:
        resp = client.chat.completions.create(
            model="gpt-5-nano",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        # Normalisation minimale
        data.setdefault("action", "ask_clarification")
        data.setdefault("record_id", None)
        data.setdefault("variables", {})
        data.setdefault("reason", "")
        if not isinstance(data.get("variables"), dict):
            data["variables"] = {}
        return data
    except Exception as e:
        print(f"[LLM] Erreur JSON/LLM: {e}")
        return {"action": "ask_clarification", "record_id": None, "variables": {}, "reason": "fallback"}


def beep_short():
    # Bip simple avec sounddevice si dispo; sinon ignore
    try:
        import numpy as np
        import sounddevice as sd

        fs = 44100
        t = np.linspace(0, 0.1, int(fs * 0.1), False)
        tone = (0.2 * np.sin(2 * np.pi * 880 * t)).astype("float32")
        sd.play(tone, fs)
        sd.wait()
    except Exception:
        pass


def send_invite(email: str, memory: Dict[str, Any]) -> None:
    # Simulation d'envoi d'invitation: log uniquement
    print(f"[INVITE] Invitation simulée envoyée à: {email}")
    memory["invite_sent"] = True


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Agent vocal simple: STT FR → décision LLM JSON → lecture segments pré-enregistrés"
        )
    )
    # Plus d'arguments superflus: on utilise les valeurs par défaut plus longues dans stt_openai.record_until_silence
    args = parser.parse_args()

    # Charger .env si présent (sans dépendre de python-dotenv)
    try:
        from dotenv import load_dotenv

        env_path = Path(__file__).resolve().parent / ".env"
        load_dotenv(dotenv_path=env_path, override=False)
    except Exception:
        pass

    if not os.getenv("OPENAI_API_KEY"):
        print("Erreur: OPENAI_API_KEY n'est pas défini dans l'environnement.")
        sys.exit(1)

    # Plus de device-index: afplay utilise la sortie système par défaut

    segments_dir = Path(__file__).resolve().parent / "segments"
    if not segments_dir.exists():
        print(f"Info: le dossier de segments n'existe pas encore: {segments_dir}")
        print("Crée-le et ajoute les m4a/mp3 nécessaires (voir manifest.json).")

    # Charger manifest
    manifest_path = segments_dir / "manifest.json"
    try:
        manifest = load_manifest(manifest_path)
    except Exception as e:
        print(f"Erreur: impossible de charger le manifest: {e}")
        sys.exit(1)

    id_to_path: Dict[str, str] = manifest["id_to_path"]
    records_for_prompt: List[Dict[str, str]] = manifest["records"]

    # Mémoire légère
    memory: Dict[str, Any] = {
        "greeted": False,
        "presentation_received": False,
        "email_captured": False,
        "invite_sent": False,
        "email": None,
    }

    # Définition de la séquence stricte d'étapes (record_id)
    STEP_ORDER: List[str] = [
        "Test_son",
        "Raison_rdv",
        "Presentez_vous",
        "Merci_presentation",
        "Demande_email",
        # Puis action do_tool (invitation)
    ]

    def compute_allowed_records(mem: Dict[str, Any]) -> List[str]:
        # Gating simple par état
        if not mem.get("greeted"):
            # On commence par Bonjour si disponible, sinon Test_son
            return [rid for rid in ["Bonjour", "Test_son"] if rid in id_to_path]
        # Étape 1: Test_son
        if not mem.get("test_son_done") and "Test_son" in id_to_path:
            return ["Test_son"]
        # Étape 2: Raison_rdv
        if not mem.get("raison_done") and "Raison_rdv" in id_to_path:
            return ["Raison_rdv"]
        # Étape 3: Presentez_vous
        if not mem.get("presentation_received") and "Presentez_vous" in id_to_path:
            return ["Presentez_vous"]
        # Étape 4: Merci_presentation (une fois présentation reçue)
        if mem.get("presentation_received") and not mem.get("merci_done") and "Merci_presentation" in id_to_path:
            return ["Merci_presentation"]
        # Étape 5: Demande_email
        if not mem.get("email_captured") and "Demande_email" in id_to_path:
            return ["Demande_email"]
        # Si email capturé: do_tool puis Invitation_done
        if mem.get("email_captured"):
            return []  # Le modèle doit proposer do_tool
        return []

    # Début: jouer Bonjour si dispo
    if "Bonjour" in id_to_path:
        print("[INIT] Lecture de 'Bonjour'.")
        play_record("Bonjour", id_to_path)
        memory["greeted"] = True

    print("Parlez après le bip. Pausez pour terminer votre phrase. Ctrl+C pour quitter.")

    try:
        while True:
            beep_short()

            wav_bytes = record_until_silence()
            text = transcribe_wave(wav_bytes)

            if text:
                print(f"Reconnu (STT): {text}")
            else:
                print("(STT) silence ou inaudible.")

            # Heuristiques mémoire
            if not memory.get("presentation_received") and detect_presentation(text):
                memory["presentation_received"] = True

            if not memory.get("email_captured"):
                email_fb = extract_email(text)
                if email_fb:
                    memory["email"] = email_fb
                    memory["email_captured"] = True

            # Décision LLM avec gating
            allowed = compute_allowed_records(memory)
            decision = decide_next_action(text, memory, records_for_prompt, allowed)
            action = (decision.get("action") or "").strip()
            record_id = decision.get("record_id")
            variables = decision.get("variables") or {}

            if action == "play_record":
                if isinstance(record_id, str) and record_id:
                    # Enforcement: ne jouer que si autorisé par gating
                    if allowed and record_id not in allowed:
                        print(f"[GATE] '{record_id}' non autorisé à cette étape. Autorisés: {allowed}")
                        # forcer le premier autorisé si possible
                        record_id = allowed[0]
                    played = play_record(record_id, id_to_path)
                    # Mise à jour mémoire simple
                    if played and record_id == "Test_son":
                        memory["test_son_done"] = True
                    if played and record_id == "Raison_rdv":
                        memory["raison_done"] = True
                    if played and record_id == "Demande_email":
                        pass  # en attente email utilisateur
                    if played and record_id == "Merci_presentation":
                        memory["presentation_received"] = True
                else:
                    print("[LLM] 'play_record' sans record_id valide.")

            elif action == "do_tool":
                email = variables.get("email") or memory.get("email")
                if email:
                    send_invite(email, memory)
                    # Lecture de confirmation si dispo
                    if "Invitation_done" in id_to_path:
                        play_record("Invitation_done", id_to_path)
                    # Arrêt propre après invitation
                    break
                else:
                    print("[TOOL] Email manquant pour l'invitation. Demande de clarification.")

            elif action == "ask_clarification":
                # Pas de TTS ni fillers: on log simplement
                print("[CLARIF] L'agent demande une clarification (aucun audio dédié).")

            elif action == "end":
                print("[AGENT] Fin de la session demandée par l'agent.")
                break

            else:
                print(f"[LLM] Action inconnue ou vide: '{action}'.")

    except KeyboardInterrupt:
        print("Au revoir !")


if __name__ == "__main__":
    main()


