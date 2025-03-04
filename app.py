import os
import json
import math
from flask import Flask, request, redirect, url_for, session, render_template, abort
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

app = Flask(__name__)
secret_key = os.environ.get('FLASK_SECRET_KEY')
if not secret_key:
    raise RuntimeError("FLASK_SECRET_KEY environment variable not set")
app.secret_key = secret_key

SEVERITY_ADJUSTMENT = {
    "severe": 1.0,
    "moderate": 0.75,
    "mild": 0.5
}

def calculate_question_weight(dsm_codes, severity, binary=False):
    severity_norm = severity.lower()
    if severity_norm in ['no', 'none', '']:
        return 0.0
    if binary:
        return 1.0 if severity_norm == 'yes' else 0.0
    base_weight = 0.9
    reduction = 0.2 * (len(dsm_codes) - 1)
    weight = max(0.5, base_weight - reduction)
    adjusted = weight * SEVERITY_ADJUSTMENT.get(severity_norm, 0.0)
    return round(adjusted, 2)

try:
    with open("questions.json", "r") as f:
        questions = json.load(f)
except Exception as e:
    logging.error(f"Error loading questions.json: {e}")
    raise

# Initialize question weights (using "Severe" as the default severity)
for q in questions:
    default_severity = "Yes" if q.get("binary", False) else "Severe"
    q["question_weight"] = calculate_question_weight(
        q["dsm_codes"], 
        default_severity,
        q.get("binary", False)
    )

validation_rules = [
    {
        "symptoms": ["manic_episode", "depressed_mood"],
        "condition": "not_simultaneous",
        "message": "Manic episode and depression are typically not simultaneous."
    }
]

def get_total_questions():
    return len(questions)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/start')
def start():
    session['index'] = 0
    session['answers'] = {}
    logging.info("Starting new assessment.")
    return redirect(url_for('ask_question'))

@app.route('/ask', methods=['GET', 'POST'])
def ask_question():
    idx = session.get('index', 0)
    answers = session.get('answers', {})
    direction = request.args.get('direction')

    if direction == 'back' and idx > 0:
        idx = session.get('last_answered', 0)
        session['index'] = idx
        answered = [
            i for i, q in enumerate(questions[:idx])
            if q['symptom'] in answers and not answers[q['symptom']].get('was_skipped', False)
        ]
        session['last_answered'] = answered[-1] if answered else 0
        return redirect(url_for('ask_question'))

    if request.method == 'POST':
        severity = request.form.get('severity', 'No')
        severity_norm = severity.lower()
        answer = 'no' if severity_norm in ['no', 'none', ''] else 'yes'
        prev_idx = idx - 1

        if 0 <= prev_idx < len(questions):
            symptom = questions[prev_idx]['symptom']
            codes = questions[prev_idx].get('dsm_codes', [])
            q_weight = calculate_question_weight(codes, severity)
            if not validate_answer(symptom, answer, answers):
                msg = next(
                    rule['message'] 
                    for rule in validation_rules 
                    if symptom in rule['symptoms']
                )
                return render_template('assessment.html', error=msg)
            answers[symptom] = {
                'value': answer, 
                'severity': severity, 
                'question_weight': q_weight,
                'dsm_codes': codes,
                'was_skipped': False
            }
            session['answers'] = answers
            session['last_answered'] = prev_idx
            logging.info(f"Recorded answer for '{symptom}': {answers[symptom]}")

    total_questions = len(questions)
    while idx < total_questions:
        if should_skip_question(questions[idx], answers):
            idx += 1
            session['index'] = idx
            continue
        break

    if idx < total_questions:
        current_q = questions[idx]
        session['index'] = idx + 1
        return render_template(
            'assessment.html',
            question=current_q["question"],
            question_weight=current_q.get("question_weight", 1.0),
            current_question=idx,
            total_questions=total_questions,
            binary=current_q.get("binary", False)
        )
    else:
        return generate_diagnosis()

def needs_to_skip(q, answers):
    if "dependency" in q:
        return answers.get(q["dependency"], {}).get('value', "no") != "yes"
    if "dependencies" in q:
        return not any(answers.get(dep, {}).get('value', "no") == "yes" for dep in q["dependencies"])
    return False

def should_skip_question(q, answers):
    if needs_to_skip(q, answers):
        logging.info(f"Skipping question '{q['symptom']}' due to unmet dependencies.")
        answers[q['symptom']] = {
            'value': 'no', 
            'severity': "No", 
            'question_weight': 0.0, 
            'dsm_codes': q.get('dsm_codes', []),
            'was_skipped': True
        }
        session['answers'] = answers
        return True
    return False

def validate_answer(symptom: str, answer: str, answers: dict) -> bool:
    if answer.lower() == 'no':
        return True
    for rule in validation_rules:
        if symptom in rule['symptoms'] and rule['condition'] == 'not_simultaneous':
            if any(answers.get(other, {}).get('value', 'no') == 'yes' 
                   for other in rule['symptoms'] if other != symptom):
                return False
    return True

def generate_diagnosis():
    answers = session.get('answers', {})
    diagnoses = []
    severity_order = {"No": 0, "Mild": 1, "Moderate": 2, "Severe": 3}

    diagnosis_rules = [
        {
            "name": "Major Depressive Disorder",
            "dsm_code": "296.2x",
            "symptoms": ["depressed_mood", "loss_of_interest", "fatigue", "sleep_disturbance", "feelings_of_guilt", "difficulty_concentrating", "social_withdrawal", "weight_appetite_change", "hopelessness"]
        },
        {
            "name": "Generalized Anxiety Disorder",
            "dsm_code": "300.02",
            "symptoms": ["excessive_worry", "restlessness", "difficulty_concentrating", "irritability", "sleep_disturbance", "fatigue", "muscle_tension"]
        },
        {
            "name": "Bipolar Disorder",
            "dsm_code": "296.4x",
            "symptoms": ["depressed_mood", "loss_of_interest", "manic_episode", "decreased_need_for_sleep", "racing_thoughts", "impulsivity", "irritability"]
        },
        {
            "name": "Schizophrenia",
            "dsm_code": "295.90",
            "symptoms": [
                {"any_of": ["hallucinations", "delusions"]},
                "disorganized_speech",
                "social_withdrawal",
                "disorganized_behavior"
            ]
        },
        {
            "name": "Obsessive-Compulsive Disorder",
            "dsm_code": "300.3",
            "symptoms": ["obsessions", "compulsions", "distress", "time_consuming", "suppress_obsessions"]
        },
        {
            "name": "Post-Traumatic Stress Disorder",
            "dsm_code": "309.81",
            "symptoms": [
                "trauma_exposure",
                {"any_of": ["intrusive_memories", "flashbacks"]},
                "avoidance",
                "hyperarousal"
            ]
        },
        {
            "name": "Attention-Deficit/Hyperactivity Disorder",
            "dsm_code": "314.0x",
            "symptoms": ["inattention", "hyperactivity", "impulsivity", "difficulty_organizing", "difficulty_concentrating", "irritability"]
        }
    ]

    for rule in diagnosis_rules:
        total_symptoms = 0
        present_count = 0
        total_weight = 0.0
        
        for sym in rule["symptoms"]:
            total_symptoms += 1
            if isinstance(sym, dict) and "any_of" in sym:
                answered = False
                weight = 0.0
                for candidate in sym["any_of"]:
                    ans = answers.get(candidate, {})
                    if ans.get('value', 'no') == 'yes' and ans.get('question_weight', 0) > 0:
                        answered = True
                        weight = ans.get('question_weight', 0)
                        break
                if answered:
                    present_count += 1
                    total_weight += weight
            else:
                ans = answers.get(sym, {})
                if ans.get('value', 'no') == 'yes' and ans.get('question_weight', 0) > 0:
                    present_count += 1
                    total_weight += ans.get('question_weight', 0)

        threshold = math.ceil(total_symptoms * 0.7)
        if present_count >= threshold and present_count > 0:
            result_weight = total_weight / present_count
            diagnoses.append({
                "name": rule["name"],
                "dsm_code": rule["dsm_code"],
                "question_weight": result_weight
            })

    valid_diagnoses = sorted(
        [d for d in diagnoses if d['question_weight'] * 100 >= 40],
        key=lambda x: x['question_weight'],
        reverse=True
    )

    if valid_diagnoses:
        diagnosis_items = []
        for d in valid_diagnoses:
            diagnosis_items.append(
                f'<div class="diagnosis-item">'
                f'<div class="diagnosis-item-name">{d["name"]}</div>'
                f'<div class="diagnosis-item-details">'
                f'DSM-5-TR: {d["dsm_code"]} | Certainty: {d["question_weight"]*100:.0f}%</div></div>'
            )
        diagnosis_result = '\n'.join(diagnosis_items)
    else:
        diagnosis_result = '<div class="diagnosis-item">No diagnosis could be determined based on your responses.</div>'

    logging.info(f"Final diagnoses: {diagnosis_result}")
    return render_template('assessment.html', result=diagnosis_result)

@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"Unhandled exception: {e}")
    return render_template('assessment.html', error="An unexpected error occurred. Please try again later."), 500

if __name__ != '__main__':
    logging.info("App loaded in production mode.")
