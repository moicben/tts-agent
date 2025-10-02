from RealtimeTTS import TextToAudioStream  # casse possible selon la version
import RealtimeTTS as rt
# Option de sortie: définis un index de périphérique si nécessaire (ex: AirPods = 3)
OUTPUT_DEVICE_INDEX = None  # remplace par un entier (ex: 3) pour forcer la sortie

# Sélectionne un moteur disponible (priorité aux moteurs sans boucle pyttsx3)
Engine = (
    getattr(rt, "GTTSEngine", None)
    or getattr(rt, "EdgeEngine", None)
    or getattr(rt, "SystemEngine", None)
)
if Engine is None:
    raise RuntimeError(
        "Aucun engine compatible trouvé (GTTSEngine/EdgeEngine/SystemEngine)."
    )

# Instanciation avec préférences FR
if Engine.__name__ == "GTTSEngine":
    engine = Engine(voice="fr")
elif Engine.__name__ == "EdgeEngine":
    engine = Engine()
elif Engine.__name__ == "SystemEngine":
    # Voix macOS française (Thomas). Ajuste si besoin
    engine = Engine(voice="com.apple.speech.synthesis.voice.thomas")
else:
    engine = Engine()

stream = TextToAudioStream(
    engine,
    output_device_index=OUTPUT_DEVICE_INDEX,
    language="fr",
)
stream.feed("Bonjour, ceci est un test avec RealtimeTTS. J'espère que vous m'entendez maintenant.")
stream.play()