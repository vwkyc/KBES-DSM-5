## Overview
A web-based expert system that uses Python-based rules and DSM-5-TR criteria to provide preliminary mental health disorder screening. The system walks users through diagnostic questions and provides weighted assessments based on responses.

## Warning
This is a prototype system for educational and research purposes only.
Not intended for clinical use or actual diagnosis.
All diagnoses should be made by qualified mental health professionals.

## Installation
1. Clone this repository
2. Create a Python virtual environment:
```sh
python -m venv myenv
source myenv/bin/activate  # Linux/Mac
myenv\Scripts\activate     # Windows
```
3. Install dependencies:
```sh
pip install -r requirements.txt
pip install waitress #if on windows
```

## Usage
1. Start the Flask web application:
```sh
export FLASK_SECRET_KEY="your_very_secret_key"
gunicorn -w 4 --bind 0.0.0.0:5000 --log-level info app:app
waitress-serve --port=5000 app:app #if on windows
```
2. Open your web browser to `http://localhost:5000`
3. Complete the interactive diagnostic assessment
4. Review the analysis results

## Details

### Diagnostic Assessment
The system evaluates 7 major DSM-5-TR categories:
- Major Depressive Disorder (296.2x)
- Bipolar Disorder (296.4x)
- Generalized Anxiety Disorder (300.02) 
- ADHD (314.0x)
- Schizophrenia (295.90)
- OCD (300.3)
- PTSD (309.81)

#### Question Distribution
Total questions per DSM code:
- **296.2x:** 9 questions  
- **296.4x:** 7 questions  
- **300.02:** 7 questions  
- **314.0x:** 6 questions  
- **295.90:** 5 questions  
- **300.3:**  5 questions  
- **309.81:** 5 questions

Stand-alone questions (single DSM code) per category:
- **296.2x:** 3 questions
- **296.4x:** 3 questions
- **300.02:** 3 questions
- **314.0x:** 3 questions
- **295.90:** 4 questions  
- **300.3:**  5 questions  
- **309.81:** 5 questions  

### Methodology
- **Dynamic Question Weights**: Questions are weighted based on specificity and severity.
- **Severity Scaling**: Responses scaled as None/Mild/Moderate/Severe.
- **Rule-Based Logic**: Python rules process responses based on DSM-5-TR criteria.
- **Dependency Handling**: Questions can be conditionally shown based on previous responses.

### Calculations
Question weights are calculated using:
- Base weight: 0.9
- Reduction for multiple DSM codes: -0.2 per additional code
- Severity adjustments:
  - Severe: 100% of weight
  - Moderate: 75% of weight  
  - Mild: 50% of weight

### Symptom Threshold
For a diagnosis to be considered, the system requires that at least 70% of the relevant symptoms for each disorder are present. Only when 70% or more of the symptom questions for a given DSM-5-TR category are answered affirmatively does the disorder qualify for diagnosis.
