"""Build the labeled Spanish phrase set used to train/evaluate the ORACLE-Voz triage classifier.

Labels: emergency | urgent | routine. Phrases are synthetic (template-based) and written in Mexican Spanish,
including colloquial forms, first person (patient) and third person (family member).
"""
import os, sys, re, random, unicodedata
import pandas as pd

OUT = sys.argv[1] if len(sys.argv) > 1 else "data/voice"
os.makedirs(OUT, exist_ok=True)
random.seed(2026)

WHO_3P = ["mi mamá", "mi papá", "mi abuelita", "mi abuelito", "mi esposo", "mi esposa", "mi suegra", "mi tía", "doña Rosa", "don Pepe"]
SINCE = ["desde ayer", "desde la mañana", "desde hace rato", "desde anoche", "desde hace dos días", "desde el domingo", "hace como una hora", ""]
OPEN = ["", "Buenas tardes, ", "Hola, ", "Oiga, ", "Disculpe, ", "Buenos días, ", "Señorita, ", "Doctora, "]

# (first-person template, third-person template, category)
EMERGENCY = [
    ("no puedo respirar bien", "{w} no puede respirar", "severe_breathing"),
    ("se me va el aire y no lo recupero", "a {w} se le va el aire", "severe_breathing"),
    ("me falta mucho el aire", "a {w} le falta el aire y tiene los labios morados", "severe_breathing"),
    ("me estoy ahogando", "{w} se está ahogando", "severe_breathing"),
    ("me duele muy fuerte el pecho", "a {w} le duele el pecho muy fuerte", "chest_pain"),
    ("siento opresión en el pecho y el dolor se me va al brazo", "{w} dice que tiene opresión en el pecho", "chest_pain"),
    ("me aprieta el pecho", "a {w} le aprieta el pecho y está sudando frío", "chest_pain"),
    ("me desmayé en el baño", "{w} se desmayó", "unconscious"),
    ("", "{w} no responde, no despierta", "unconscious"),
    ("", "{w} perdió el conocimiento", "unconscious"),
    ("", "{w} se privó en la sala", "unconscious"),
    ("no puedo mover el brazo izquierdo", "{w} no puede mover el lado derecho", "stroke_signs"),
    ("", "a {w} se le cayó la cara de un lado", "stroke_signs"),
    ("", "{w} habla arrastrado y no se le entiende lo que dice", "stroke_signs"),
    ("", "a {w} le dio un ataque y se sacudía", "seizure"),
    ("", "{w} tuvo una convulsión", "seizure"),
    ("me corté y no para de sangrar", "{w} sangra mucho de la pierna y no para", "severe_bleeding"),
    ("vomité sangre", "{w} vomitó sangre", "severe_bleeding"),
    ("me caí y no me puedo levantar del piso", "{w} se cayó y no se puede levantar", "serious_fall"),
    ("me caí y me pegué en la cabeza", "{w} se cayó y se pegó en la cabeza", "serious_fall"),
    ("", "de repente {w} no me reconoce", "sudden_confusion"),
    ("", "{w} no sabe dónde está, de repente se puso así", "sudden_confusion"),
    ("ya no quiero vivir", "{w} dice que ya no quiere vivir", "self_harm"),
    ("me quiero morir", "{w} dice que se quiere quitar la vida", "self_harm"),
]
URGENT = [
    ("tengo calentura", "{w} tiene calentura", "fever"),
    ("tengo fiebre y escalofríos", "{w} tiene fiebre", "fever"),
    ("se me hinchó la pierna", "a {w} se le hinchó la pierna", "swelling"),
    ("tengo los pies muy hinchados", "{w} tiene los pies hinchados", "swelling"),
    ("me duele la herida y está roja", "a {w} le supura la herida", "wound"),
    ("me siento mareado", "{w} anda muy mareada", "dizziness"),
    ("he vomitado varias veces", "{w} ha vomitado varias veces", "vomiting"),
    ("tengo diarrea", "{w} tiene diarrea y está débil", "diarrhea"),
    ("no he querido comer nada", "{w} no ha comido ni tomado agua", "not_eating"),
    ("tengo la presión alta, me salió en 170", "a {w} le salió la presión en 170", "blood_pressure"),
    ("me salió la azúcar en 300", "a {w} le salió el azúcar muy alta", "glucose"),
    ("me duele mucho la rodilla, no puedo caminar", "a {w} le duele la cadera y no quiere caminar", "pain"),
    ("tengo mucha tos con flemas", "{w} tiene tos con flemas", "cough"),
    ("me arde al orinar", "a {w} le arde al hacer pipí", "urinary"),
    ("me caí pero no me pegué fuerte", "{w} se resbaló pero no se pegó fuerte", "minor_fall"),
    ("ando más confundido que de costumbre", "{w} anda más confundida que otros días", "confusion_mild"),
    ("me falta el aire cuando camino", "a {w} le cuesta más respirar cuando camina", "breathing_mild"),
    ("me duele el estómago desde la mañana", "a {w} le duele la panza", "abdominal_pain"),
]
ROUTINE = [
    ("no he dormido bien", "{w} no ha dormido bien", "sleep"),
    ("me siento un poco triste", "{w} anda triste", "mood"),
    ("ya se me están acabando las pastillas de la presión", "a {w} ya se le acaban sus medicinas", "medication_refill"),
    ("quería cambiar la cita del jueves", "queremos cambiar la cita de {w}", "appointment"),
    ("tengo poca hambre estos días", "{w} anda con poco apetito", "appetite"),
    ("estoy estreñido", "{w} está estreñida", "constipation"),
    ("me duelen las rodillas como siempre", "a {w} le duelen las rodillas como siempre", "chronic_pain"),
    ("todo bien, solo quería avisar", "{w} está bien, solo quería avisar", "check_in"),
    ("gracias por la visita de ayer", "gracias por atender a {w}", "thanks"),
    ("se me olvidó si me tomé la pastilla", "{w} no recuerda si se tomó la pastilla", "medication_question"),
    ("quería saber a qué hora viene la enfermera", "¿a qué hora viene la enfermera con {w}?", "schedule_question"),
    ("tengo la piel reseca", "{w} tiene la piel reseca", "skin"),
    ("me siento cansado", "{w} anda cansada", "fatigue"),
    ("ya me tomé la presión y salió normal", "a {w} le salió normal la presión", "normal_reading"),
]
# Hard cases that must NOT be read as emergencies by a naive keyword model (label kept as stated)
HARD = [
    ("ayer me dolía el pecho pero ya se me quitó, quiero que me revisen", "urgent", "chest_pain_resolved"),
    ("{w} no tiene dolor en el pecho, solo tos", "urgent", "cough"),
    ("ya no me falta el aire, el medicamento funcionó", "routine", "breathing_resolved"),
    ("{w} se cayó la semana pasada pero ya está bien", "routine", "past_fall"),
    ("ya no puede respirar bien, se está poniendo morado", "emergency", "severe_breathing"),
    ("{w} ya no quiere comer ni vivir, dice que está cansada de todo", "emergency", "self_harm"),
]

def with_variations(text, first_person):
    o = random.choice(OPEN)
    s = random.choice(SINCE)
    t = text
    if s and random.random() < 0.6:
        t = f"{t} {s}"
    t = o + (t[0].upper() + t[1:] if not o else t)
    if random.random() < 0.3:
        t += random.choice([", ¿qué hago?", ", ayúdenme por favor", ". Estoy preocupada.", ", por favor manden a alguien", "."])
    return t

rows = []
def add(label, group, target):
    seen = set(); tries = 0
    while len(seen) < target and tries < target * 40:
        tries += 1
        fp, tp, cat = random.choice(group)
        use_first = fp and random.random() < 0.45
        text = with_variations(fp, True) if use_first else with_variations(tp.format(w=random.choice(WHO_3P)), False)
        if text not in seen:
            seen.add(text)
            rows.append({"text": text, "label": label, "category": cat, "speaker": "patient" if use_first else "family", "hard_case": False})

add("emergency", EMERGENCY, 450)
add("urgent", URGENT, 520)
add("routine", ROUTINE, 520)
for tmpl, label, cat in HARD:
    for _ in range(6):
        text = with_variations(tmpl.format(w=random.choice(WHO_3P)), False)
        rows.append({"text": text, "label": label, "category": cat, "speaker": "family" if "{w}" in tmpl else "patient", "hard_case": True})

df = pd.DataFrame(rows).drop_duplicates("text").sample(frac=1, random_state=2026).reset_index(drop=True)
df.insert(0, "phrase_id", [f"PHR-{i+1:05d}" for i in range(len(df))])
# stratified split 70/15/15
df["split"] = "train"
for lab, g in df.groupby("label"):
    idx = g.index.tolist(); n = len(idx)
    df.loc[idx[int(n * .70):int(n * .85)], "split"] = "validation"
    df.loc[idx[int(n * .85):], "split"] = "test"
df.to_csv(os.path.join(OUT, "triage_phrases.csv"), index=False, lineterminator="\n")
print(df.label.value_counts().to_dict(), df.split.value_counts().to_dict(), len(df))
