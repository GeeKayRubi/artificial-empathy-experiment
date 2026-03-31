from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import os
from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd
import json
from datetime import datetime, timedelta
from flask import send_file


# Load environment variables securely
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialise Flask app
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")


# Admin route to set participant number/condition
@app.route('/admin', methods=['GET'])
def admin():
    return render_template('admin.html')

# Welcome page
@app.route('/welcome')
def welcome():
    return render_template('welcome.html')

@app.route('/set_condition', methods=['POST'])
def set_condition():
    participant_id = request.form['participant_id']
    session['participant_id'] = participant_id

    pid_number = int(participant_id)

    session['bot_condition_1'] = 'safety' if pid_number % 4 in [1, 2] else 'default'
    session['participant_prompt_1'] = 'positive' if pid_number % 2 == 1 else 'negative'

    session['bot_condition'] = session['bot_condition_1']
    session['participant_prompt'] = session['participant_prompt_1']

    session.pop('conversation', None)

    return redirect(url_for('welcome'))

@app.route('/consent')
def consent():
    return render_template('consent.html')

@app.route('/demographics', methods=['GET', 'POST'])
def demographics():
    if request.method == 'POST':
        # Capture form data
        participant_id = session.get('participant_id')
        age = request.form.get('age')

        # Handle gender with "other" logic
        gender = request.form.get('gender')
        gender_other = request.form.get('gender_other')
        if gender == 'other' and gender_other:
            gender = f"Other: {gender_other}"

        # Handle education with "other" logic
        education = request.form.get('education')
        education_other = request.form.get('education_other')
        if education == 'other' and education_other:
            education = f"Other: {education_other}"

        # Structure the data
        demographic_data = {
            'participant_id': participant_id,
            'age_range': age,
            'gender': gender,
            'education': education,
            'timestamp': datetime.now().isoformat()
        }

        # Save data to CSV
        df = pd.DataFrame([demographic_data])
        filename = "demographics_data.csv"
        df.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False)

        # Redirect to next stage
        return redirect(url_for('display_prompt'))

    return render_template('demographics.html')




@app.route('/prompt', methods=['GET'])
def display_prompt():
    if 'participant_prompt' not in session:
        return redirect(url_for('admin'))

    prompt_type = session['participant_prompt']

    if prompt_type == 'positive':
        participant_prompt = (
            "Take a moment to think of a <strong>positive</strong> experience in your life "
            "that still makes you feel happy or content when you remember it. "
            "It could be something big or small: any moment that brought you genuine joy, pride, or comfort. "
            "Take a minute to visualise this memory clearly, and then describe briefly what happened "
            "and how it made you feel. "
            "<br><br>"
            "You will have <strong>five minutes</strong> to share and discuss this memory with the chatbot."
            "<br><br>"
            "(Important: Focus on your feelings, but please do not include any real names or personally identifying details.)"
        )
    else:
        participant_prompt = (
            "Take a moment to think of a <strong>challenging</strong> experience that made you feel upset, "
            "disappointed, or sad: something negative that happened in your life that still mildly bothers you "
            "when you recall it. Please do not choose an extremely distressing, traumatic, or highly upsetting event; "
            "instead, select a more ordinary, moderate negative memory that you feel comfortable reflecting on right now. "
            "Take a moment to recall it clearly, and then briefly describe what happened and how you felt. "
            "<br><br>"
            "You will have <strong>five minutes</strong> to share and discuss this memory with the chatbot."
            "<br><br>"
            "(Important: Focus on your feelings, but please do not include any real names or personally identifying details.)"
        )

    return render_template('prompt.html', participant_prompt=participant_prompt)

@app.route('/start_chat', methods=['POST'])
def start_chat():
    print("[DEBUG] Entered start_chat")
    print("[DEBUG] Session before starting chat:", dict(session))
    session['start_time'] = datetime.now().isoformat()
    return redirect(url_for('home'))

@app.route('/', methods=['GET'])
def home():
    print("[DEBUG] Entered home")
    print("[DEBUG] Session keys:", list(session.keys()))
    if 'bot_condition' not in session or 'participant_prompt' not in session:
        print("[ERROR] Missing session data — redirecting to /admin")
        return redirect(url_for('admin'))

    prompt_type = session['participant_prompt']

    if prompt_type == 'positive':
        participant_prompt = (
            "Take a moment to think of a positive experience in your life "
            "that still makes you feel happy or content when you remember it. "
            "It could be something big or small: any moment that brought you genuine joy, pride, or comfort. "
            "Take a minute to visualise this memory clearly, and then describe briefly what happened "
            "and how it made you feel. "
        )
    else:
        participant_prompt = (
            "Take a moment to think of a challenging experience that made you feel upset, "
            "disappointed, or sad: something negative that happened in your life that still mildly bothers you "
            "when you recall it. Please do not choose an extremely distressing, traumatic, or highly upsetting event; "
            "instead, select a more ordinary, moderate negative memory that you feel comfortable reflecting on right now. "
            "Take a moment to recall it clearly, and then briefly describe what happened and how you felt. "
        )

    
    # Determine session number
    session_number = 1 if 'session_completed' not in session else 2

    return render_template('index.html', 
                           participant_prompt=participant_prompt, 
                           session_number=session_number)

def load_prompt(condition):
    filename = 'prompts/safety_aware.txt' if condition == 'safety' else 'prompts/default_supportive.txt'
    with open(filename, 'r', encoding='utf-8') as file:
        return file.read()
    
@app.route('/chatbot_questionnaire/<int:session_number>', methods=['GET', 'POST'])
def chatbot_questionnaire(session_number):
    if request.method == 'POST':
        # capture form data
        data = {
            'participant_id': session['participant_id'],
            'session_number': session_number,
            'timestamp': datetime.now().isoformat(),
            'bot_condition': session.get(f'bot_condition_{session_number}', 'unknown'),
            'Q1_satisfaction': request.form.get('q1'),
            'Q2_trust': request.form.get('q2'),
            'Q3_helpfulness': request.form.get('q3'),
            'Q4_emotional_support': request.form.get('q4'),
            'Q5_reuse_intent': request.form.get('q5'),
            'Q6_preference': request.form.get('q6', ''),
            'open_comment': request.form.get('comment', '')
        }

        # store data in CSV file
        df = pd.DataFrame([data])
        filename = "chatbot_questionnaire_responses.csv"
        df.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False)

        # determine next step based on session number
        if session_number == 1:
            return redirect(url_for('panas', panas_type='post_session_1'))
        elif session_number == 2:
            return redirect(url_for('panas', panas_type='post_session_2'))

    return render_template('chatbot_questionnaire.html', session_number=session_number)


    
@app.route('/break')
def break_page():
    return render_template('break.html')


@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_msg = data['message']

        if 'start_time' not in session:
            session['start_time'] = datetime.now().isoformat()
            print("[DEBUG] Timer started at:", session['start_time'])

        start_time = datetime.fromisoformat(session['start_time'])
        elapsed_time = datetime.now() - start_time
        session_limit = timedelta(minutes=5)

        session_number = 1 if 'session_completed' not in session else 2
        if elapsed_time > session_limit or user_msg =="[SESSION TIMEOUT]":
            if session_number == 1:
                session['bot_condition_2'] = 'default' if session['bot_condition_1'] == 'safety' else 'safety'
                session['participant_prompt_2'] = 'negative' if session['participant_prompt_1'] == 'positive' else 'positive'
                session['session_completed'] = True
           
            session.pop('conversation', None)
            session.pop('start_time', None)

            return jsonify({
        "reply": "Session ended due to time limit.",
        "redirect": f"/chatbot_questionnaire/{session_number}",
        "session_end": True
        })

        if 'conversation' not in session:
            session['conversation'] = [{"role": "system", "content": load_prompt(session['bot_condition'])}]

        session['conversation'].append({"role": "user", "content": user_msg})

        response = client.chat.completions.create(
            model="gpt-4-turbo", 
            messages=session['conversation']
        )

        full_reply = response.choices[0].message.content.strip()
        if '[FLAG: Ethical Challenge]' in full_reply:
            user_reply = full_reply.replace('[FLAG: Ethical Challenge]', '').strip()
            internal_flag = True
        else:
            user_reply = full_reply
            internal_flag = False

        session['conversation'].append({"role": "assistant", "content": full_reply})
        session.modified = True

        session_number = 1 if 'session_completed' not in session else 2

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'participant_id': session['participant_id'],
            'session_number': session_number,
            'participant_message': user_msg,
             'bot_reply_user_facing': user_reply,
            'bot_reply_researcher_facing': full_reply,
            'ethical_challenge_flagged': internal_flag
        }

        history_file = 'chat_history.json'

        if os.path.exists(history_file):
            with open(history_file, 'r') as file:
                history_data = json.load(file)
        else:
            history_data = []

        history_data.append(log_entry)

        with open(history_file, 'w') as file:
            json.dump(history_data, file, indent=2)

        log_csv_entry = pd.DataFrame([{
            'timestamp': datetime.now(), 
            'participant_id': session['participant_id'],
            'bot_condition': session['bot_condition'], 
            'participant_prompt': session['participant_prompt'],
            'session_number': session_number, 
            'participant_message': user_msg, 
            'bot_reply_user_facing': user_reply, 'bot_reply_user_facing': user_reply,
            'bot_reply_researcher_facing': full_reply,
            'ethical_challenge_flagged': internal_flag
        }])

        log_csv_entry.to_csv('chat_logs.csv', mode='a', header=not os.path.exists('chat_logs.csv'), index=False)

        return jsonify({"reply": user_reply, "session_end": False})


    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/monitor')
def monitor():
    return render_template('monitor.html')

@app.route('/get_chat_history')
def get_chat_history():
    history_file = 'chat_history.json'
    try:
        with open(history_file, 'r') as file:
            data = json.load(file)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify([])



@app.route('/panas/post_session_1_direct')
def panas_post_session_1_direct():
    panas_items = [
        "Upset", "Hostile", "Alert", "Ashamed", "Inspired",
        "Nervous", "Determined", "Attentive", "Afraid", "Active"
    ]
    session['panas_type'] = 'post_session_1'  
    return render_template("panas.html", panas_items=panas_items)

@app.route('/chatbot2_questionnaire', methods=['GET', 'POST'])
def chatbot2_questionnaire():
    if request.method == 'POST':
        # process questionnaire data here and save
        return redirect(url_for('panas', panas_type='post_session_2'))
    return render_template('chatbot2_questionnaire.html')


@app.route('/panas/<panas_type>')
def panas(panas_type):
    panas_items = [
        "Upset", "Hostile", "Alert", "Ashamed", "Inspired",
        "Nervous", "Determined", "Attentive", "Afraid", "Active"
    ]
    session['panas_type'] = panas_type  # pre_session_1, post_session_1, etc.
    return render_template("panas.html", panas_items=panas_items)

@app.route('/submit_panas', methods=['POST'])
def submit_panas():
    participant_id = session.get('participant_id')
    panas_type = session.get('panas_type')

    required_items = ["Upset", "Hostile", "Alert", "Ashamed", "Inspired",
                      "Nervous", "Determined", "Attentive", "Afraid", "Active"]

    responses = {item: int(request.form[item]) for item in required_items}

    positive_items = ["Alert", "Inspired", "Determined", "Attentive", "Active"]
    negative_items = ["Upset", "Hostile", "Ashamed", "Nervous", "Afraid"]

    positive_score = sum(responses[item] for item in positive_items)
    negative_score = sum(responses[item] for item in negative_items)

    data_row = {
        'participant_id': participant_id,
        'panas_type': panas_type,
        'timestamp': datetime.now().isoformat(),
        **responses,
        'positive_score': positive_score,
        'negative_score': negative_score
    }

    df = pd.DataFrame([data_row])
    df.to_csv("panas_responses.csv", mode='a', header=not os.path.exists("panas_responses.csv"), index=False)

    if panas_type == "pre_session_1":
        return redirect(url_for('demographics'))
    
    elif panas_type == "post_session_1":
        # explicitly set conditions here (safest solution)
        session['bot_condition_2'] = 'default' if session['bot_condition_1'] == 'safety' else 'safety'
        session['participant_prompt_2'] = 'negative' if session['participant_prompt_1'] == 'positive' else 'positive'
        session['session_completed'] = True
        return redirect(url_for('break_page'))

    elif panas_type == "pre_session_2":
        # Verify again, but now this should always pass
        if 'bot_condition_2' not in session or 'participant_prompt_2' not in session:
            print("[ERROR] Session 2 data missing even after explicit setup.")
            return "Session 2 not ready. Please contact researcher.", 400

        session['bot_condition'] = session['bot_condition_2']
        session['participant_prompt'] = session['participant_prompt_2']
        session['start_time'] = datetime.now().isoformat()
        session.pop('conversation', None)
        session.pop('warned', None)
        return redirect(url_for('display_prompt'))

    elif panas_type == "post_session_2":
        return redirect(url_for('final_questionnaire'))

    return redirect(url_for('home'))



@app.route('/questionnaire')
def questionnaire():
    return render_template('questionnaire.html')

@app.route('/final_questionnaire', methods=['GET', 'POST'])
def final_questionnaire():
    if request.method == 'POST':
        participant_id = session.get('participant_id')
        timestamp = datetime.now().isoformat()

        # Map choices to actual chatbot conditions
        condition_mapping = {
            'first': session.get('bot_condition_1'),
            'second': session.get('bot_condition_2'),
            'both': 'both_bots',
            'first_only': session.get('bot_condition_1'),
            'second_only': session.get('bot_condition_2'),
            'neither': 'neither_bot',
            'no_pref': 'no_preference'
        }

        data = {
            'participant_id': participant_id,
            'timestamp': timestamp,
            'preferred_bot': condition_mapping.get(request.form.get('preferred_bot'), 'unknown'),
            'experiment_purpose': request.form.get('experiment_purpose'),
            'bot_helpfulness': condition_mapping.get(request.form.get('bot_helpfulness'), 'unknown'),
            'most_comfortable_bot': condition_mapping.get(request.form.get('most_comfortable_bot'), 'unknown'),
            'emotionally_supported_bot': condition_mapping.get(request.form.get('emotionally_supported_bot'), 'unknown'),
            'future_bot_choice': condition_mapping.get(request.form.get('future_bot_choice'), 'unknown'),

            # Original participant selections for reference
            'preferred_bot_choice': request.form.get('preferred_bot'),
            'bot_helpfulness_choice': request.form.get('bot_helpfulness'),
            'most_comfortable_bot_choice': request.form.get('most_comfortable_bot'),
            'emotionally_supported_bot_choice': request.form.get('emotionally_supported_bot'),
            'future_bot_choice_original': request.form.get('future_bot_choice'),
            'previous_chatbot_use': request.form.get('previous_chatbot_use'),
            'chatbot_use_comments': request.form.get('chatbot_use_comments', '')
        }

        # Save data
        filename = 'final_questionnaire_responses.csv'
        df = pd.DataFrame([data])
        df.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False)

        return redirect(url_for('debrief'))

    return render_template('final_questionnaire.html')


@app.route('/debrief')
def debrief():
    return render_template('debrief.html')

@app.route('/cheerful')
def cheerful():
    return render_template('cheerful.html')


@app.route('/clear')
def clear_session():
    session.clear()
    return "Session cleared. Go to /admin to restart."


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import os
from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd
import json
from datetime import datetime, timedelta

# Load environment variables securely
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialise Flask app
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")


# Admin route to set participant number/condition
@app.route('/admin', methods=['GET'])
def admin():
    return render_template('admin.html')

# Welcome page
@app.route('/welcome')
def welcome():
    return render_template('welcome.html')

@app.route('/set_condition', methods=['POST'])
def set_condition():
    participant_id = request.form['participant_id']
    session['participant_id'] = participant_id

    pid_number = int(participant_id)

    session['bot_condition_1'] = 'safety' if pid_number % 4 in [1, 2] else 'default'
    session['participant_prompt_1'] = 'positive' if pid_number % 2 == 1 else 'negative'

    session['bot_condition'] = session['bot_condition_1']
    session['participant_prompt'] = session['participant_prompt_1']

    session.pop('conversation', None)

    return redirect(url_for('welcome'))

@app.route('/consent')
def consent():
    return render_template('consent.html')

@app.route('/demographics', methods=['GET', 'POST'])
def demographics():
    if request.method == 'POST':
        # Capture form data
        participant_id = session.get('participant_id')
        age = request.form.get('age')

        # Handle gender with "other" logic
        gender = request.form.get('gender')
        gender_other = request.form.get('gender_other')
        if gender == 'other' and gender_other:
            gender = f"Other: {gender_other}"

        # Handle education with "other" logic
        education = request.form.get('education')
        education_other = request.form.get('education_other')
        if education == 'other' and education_other:
            education = f"Other: {education_other}"

        # Structure the data
        demographic_data = {
            'participant_id': participant_id,
            'age_range': age,
            'gender': gender,
            'education': education,
            'timestamp': datetime.now().isoformat()
        }

        # Save data to CSV
        df = pd.DataFrame([demographic_data])
        filename = "demographics_data.csv"
        df.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False)

        # Redirect to next stage
        return redirect(url_for('display_prompt'))

    return render_template('demographics.html')




@app.route('/prompt', methods=['GET'])
def display_prompt():
    if 'participant_prompt' not in session:
        return redirect(url_for('admin'))

    prompt_type = session['participant_prompt']

    if prompt_type == 'positive':
        participant_prompt = (
            "Take a moment to think of a <strong>positive</strong> experience in your life "
            "that still makes you feel happy or content when you remember it. "
            "It could be something big or small: any moment that brought you genuine joy, pride, or comfort. "
            "Take a minute to visualise this memory clearly, and then describe briefly what happened "
            "and how it made you feel. "
            "<br><br>"
            "You will have <strong>five minutes</strong> to share and discuss this memory with the chatbot."
            "<br><br>"
            "(Important: Focus on your feelings, but please do not include any real names or personally identifying details.)"
        )
    else:
        participant_prompt = (
            "Take a moment to think of a <strong>challenging</strong> experience that made you feel upset, "
            "disappointed, or sad: something negative that happened in your life that still mildly bothers you "
            "when you recall it. Please do not choose an extremely distressing, traumatic, or highly upsetting event; "
            "instead, select a more ordinary, moderate negative memory that you feel comfortable reflecting on right now. "
            "Take a moment to recall it clearly, and then briefly describe what happened and how you felt. "
            "<br><br>"
            "You will have <strong>five minutes</strong> to share and discuss this memory with the chatbot."
            "<br><br>"
            "(Important: Focus on your feelings, but please do not include any real names or personally identifying details.)"
        )

    return render_template('prompt.html', participant_prompt=participant_prompt)

@app.route('/start_chat', methods=['POST'])
def start_chat():
    print("[DEBUG] Entered start_chat")
    print("[DEBUG] Session before starting chat:", dict(session))
    session['start_time'] = datetime.now().isoformat()
    return redirect(url_for('home'))

@app.route('/', methods=['GET'])
def home():
    print("[DEBUG] Entered home")
    print("[DEBUG] Session keys:", list(session.keys()))
    if 'bot_condition' not in session or 'participant_prompt' not in session:
        print("[ERROR] Missing session data — redirecting to /admin")
        return redirect(url_for('admin'))

    prompt_type = session['participant_prompt']

    if prompt_type == 'positive':
        participant_prompt = (
            "Take a moment to think of a positive experience in your life "
            "that still makes you feel happy or content when you remember it. "
            "It could be something big or small: any moment that brought you genuine joy, pride, or comfort. "
            "Take a minute to visualise this memory clearly, and then describe briefly what happened "
            "and how it made you feel. "
        )
    else:
        participant_prompt = (
            "Take a moment to think of a challenging experience that made you feel upset, "
            "disappointed, or sad: something negative that happened in your life that still mildly bothers you "
            "when you recall it. Please do not choose an extremely distressing, traumatic, or highly upsetting event; "
            "instead, select a more ordinary, moderate negative memory that you feel comfortable reflecting on right now. "
            "Take a moment to recall it clearly, and then briefly describe what happened and how you felt. "
        )

    
    # Determine session number
    session_number = 1 if 'session_completed' not in session else 2

    return render_template('index.html', 
                           participant_prompt=participant_prompt, 
                           session_number=session_number)

def load_prompt(condition):
    filename = 'prompts/safety_aware.txt' if condition == 'safety' else 'prompts/default_supportive.txt'
    with open(filename, 'r', encoding='utf-8') as file:
        return file.read()
    
@app.route('/chatbot_questionnaire/<int:session_number>', methods=['GET', 'POST'])
def chatbot_questionnaire(session_number):
    if request.method == 'POST':
        # capture form data
        data = {
            'participant_id': session['participant_id'],
            'session_number': session_number,
            'timestamp': datetime.now().isoformat(),
            'bot_condition': session.get(f'bot_condition_{session_number}', 'unknown'),
            'Q1_satisfaction': request.form.get('q1'),
            'Q2_trust': request.form.get('q2'),
            'Q3_helpfulness': request.form.get('q3'),
            'Q4_emotional_support': request.form.get('q4'),
            'Q5_reuse_intent': request.form.get('q5'),
            'Q6_preference': request.form.get('q6', ''),
            'open_comment': request.form.get('comment', '')
        }

        # store data in CSV file
        df = pd.DataFrame([data])
        filename = "chatbot_questionnaire_responses.csv"
        df.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False)

        # determine next step based on session number
        if session_number == 1:
            return redirect(url_for('panas', panas_type='post_session_1'))
        elif session_number == 2:
            return redirect(url_for('panas', panas_type='post_session_2'))

    return render_template('chatbot_questionnaire.html', session_number=session_number)


    
@app.route('/break')
def break_page():
    return render_template('break.html')


@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_msg = data['message']

        if 'start_time' not in session:
            session['start_time'] = datetime.now().isoformat()
            print("[DEBUG] Timer started at:", session['start_time'])

        start_time = datetime.fromisoformat(session['start_time'])
        elapsed_time = datetime.now() - start_time
        session_limit = timedelta(minutes=5)

        session_number = 1 if 'session_completed' not in session else 2
        if elapsed_time > session_limit or user_msg =="[SESSION TIMEOUT]":
            if session_number == 1:
                session['bot_condition_2'] = 'default' if session['bot_condition_1'] == 'safety' else 'safety'
                session['participant_prompt_2'] = 'negative' if session['participant_prompt_1'] == 'positive' else 'positive'
                session['session_completed'] = True
           
            session.pop('conversation', None)
            session.pop('start_time', None)

            return jsonify({
        "reply": "Session ended due to time limit.",
        "redirect": f"/chatbot_questionnaire/{session_number}",
        "session_end": True
        })

        if 'conversation' not in session:
            session['conversation'] = [{"role": "system", "content": load_prompt(session['bot_condition'])}]

        session['conversation'].append({"role": "user", "content": user_msg})

        response = client.chat.completions.create(
            model="gpt-4-turbo", 
            messages=session['conversation']
        )

        full_reply = response.choices[0].message.content.strip()
        if '[FLAG: Ethical Challenge]' in full_reply:
            user_reply = full_reply.replace('[FLAG: Ethical Challenge]', '').strip()
            internal_flag = True
        else:
            user_reply = full_reply
            internal_flag = False

        session['conversation'].append({"role": "assistant", "content": full_reply})
        session.modified = True

        session_number = 1 if 'session_completed' not in session else 2

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'participant_id': session['participant_id'],
            'session_number': session_number,
            'participant_message': user_msg,
             'bot_reply_user_facing': user_reply,
            'bot_reply_researcher_facing': full_reply,
            'ethical_challenge_flagged': internal_flag
        }

        history_file = 'chat_history.json'

        if os.path.exists(history_file):
            with open(history_file, 'r') as file:
                history_data = json.load(file)
        else:
            history_data = []

        history_data.append(log_entry)

        with open(history_file, 'w') as file:
            json.dump(history_data, file, indent=2)

        log_csv_entry = pd.DataFrame([{
            'timestamp': datetime.now(), 
            'participant_id': session['participant_id'],
            'bot_condition': session['bot_condition'], 
            'participant_prompt': session['participant_prompt'],
            'session_number': session_number, 
            'participant_message': user_msg, 
            'bot_reply_user_facing': user_reply, 
            'bot_reply_researcher_facing': full_reply,
            'ethical_challenge_flagged': internal_flag
        }])

        log_csv_entry.to_csv('chat_logs.csv', mode='a', header=not os.path.exists('chat_logs.csv'), index=False)

        return jsonify({"reply": user_reply, "session_end": False})


    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/monitor')
def monitor():
    return render_template('monitor.html')

@app.route('/get_chat_history')
def get_chat_history():
    history_file = 'chat_history.json'
    try:
        with open(history_file, 'r') as file:
            data = json.load(file)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify([])



@app.route('/panas/post_session_1_direct')
def panas_post_session_1_direct():
    panas_items = [
        "Upset", "Hostile", "Alert", "Ashamed", "Inspired",
        "Nervous", "Determined", "Attentive", "Afraid", "Active"
    ]
    session['panas_type'] = 'post_session_1'  
    return render_template("panas.html", panas_items=panas_items)

@app.route('/chatbot2_questionnaire', methods=['GET', 'POST'])
def chatbot2_questionnaire():
    if request.method == 'POST':
        # process questionnaire data here and save
        return redirect(url_for('panas', panas_type='post_session_2'))
    return render_template('chatbot2_questionnaire.html')


@app.route('/panas/<panas_type>')
def panas(panas_type):
    panas_items = [
        "Upset", "Hostile", "Alert", "Ashamed", "Inspired",
        "Nervous", "Determined", "Attentive", "Afraid", "Active"
    ]
    session['panas_type'] = panas_type  # pre_session_1, post_session_1, etc.
    return render_template("panas.html", panas_items=panas_items)

@app.route('/submit_panas', methods=['POST'])
def submit_panas():
    participant_id = session.get('participant_id')
    panas_type = session.get('panas_type')

    required_items = ["Upset", "Hostile", "Alert", "Ashamed", "Inspired",
                      "Nervous", "Determined", "Attentive", "Afraid", "Active"]

    responses = {item: int(request.form[item]) for item in required_items}

    positive_items = ["Alert", "Inspired", "Determined", "Attentive", "Active"]
    negative_items = ["Upset", "Hostile", "Ashamed", "Nervous", "Afraid"]

    positive_score = sum(responses[item] for item in positive_items)
    negative_score = sum(responses[item] for item in negative_items)

    data_row = {
        'participant_id': participant_id,
        'panas_type': panas_type,
        'timestamp': datetime.now().isoformat(),
        **responses,
        'positive_score': positive_score,
        'negative_score': negative_score
    }

    df = pd.DataFrame([data_row])
    df.to_csv("panas_responses.csv", mode='a', header=not os.path.exists("panas_responses.csv"), index=False)

    if panas_type == "pre_session_1":
        return redirect(url_for('demographics'))
    
    elif panas_type == "post_session_1":
        # explicitly set conditions here (safest solution)
        session['bot_condition_2'] = 'default' if session['bot_condition_1'] == 'safety' else 'safety'
        session['participant_prompt_2'] = 'negative' if session['participant_prompt_1'] == 'positive' else 'positive'
        session['session_completed'] = True
        return redirect(url_for('break_page'))

    elif panas_type == "pre_session_2":
        # Verify again, but now this should always pass
        if 'bot_condition_2' not in session or 'participant_prompt_2' not in session:
            print("[ERROR] Session 2 data missing even after explicit setup.")
            return "Session 2 not ready. Please contact researcher.", 400

        session['bot_condition'] = session['bot_condition_2']
        session['participant_prompt'] = session['participant_prompt_2']
        session['start_time'] = datetime.now().isoformat()
        session.pop('conversation', None)
        session.pop('warned', None)
        return redirect(url_for('display_prompt'))

    elif panas_type == "post_session_2":
        return redirect(url_for('final_questionnaire'))

    return redirect(url_for('home'))



@app.route('/questionnaire')
def questionnaire():
    return render_template('questionnaire.html')

@app.route('/final_questionnaire', methods=['GET', 'POST'])
def final_questionnaire():
    if request.method == 'POST':
        participant_id = session.get('participant_id')
        timestamp = datetime.now().isoformat()

        # Map choices to actual chatbot conditions
        condition_mapping = {
            'first': session.get('bot_condition_1'),
            'second': session.get('bot_condition_2'),
            'both': 'both_bots',
            'first_only': session.get('bot_condition_1'),
            'second_only': session.get('bot_condition_2'),
            'neither': 'neither_bot',
            'no_pref': 'no_preference'
        }

        data = {
            'participant_id': participant_id,
            'timestamp': timestamp,
            'preferred_bot': condition_mapping.get(request.form.get('preferred_bot'), 'unknown'),
            'experiment_purpose': request.form.get('experiment_purpose'),
            'bot_helpfulness': condition_mapping.get(request.form.get('bot_helpfulness'), 'unknown'),
            'most_comfortable_bot': condition_mapping.get(request.form.get('most_comfortable_bot'), 'unknown'),
            'emotionally_supported_bot': condition_mapping.get(request.form.get('emotionally_supported_bot'), 'unknown'),
            'future_bot_choice': condition_mapping.get(request.form.get('future_bot_choice'), 'unknown'),

            # Original participant selections for reference
            'preferred_bot_choice': request.form.get('preferred_bot'),
            'bot_helpfulness_choice': request.form.get('bot_helpfulness'),
            'most_comfortable_bot_choice': request.form.get('most_comfortable_bot'),
            'emotionally_supported_bot_choice': request.form.get('emotionally_supported_bot'),
            'future_bot_choice_original': request.form.get('future_bot_choice'),
            'previous_chatbot_use': request.form.get('previous_chatbot_use'),
            'chatbot_use_comments': request.form.get('chatbot_use_comments', '')
        }

        # Save data
        filename = 'final_questionnaire_responses.csv'
        df = pd.DataFrame([data])
        df.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False)

        return redirect(url_for('debrief'))

    return render_template('final_questionnaire.html')


@app.route('/debrief')
def debrief():
    return render_template('debrief.html')

@app.route('/cheerful')
def cheerful():
    return render_template('cheerful.html')


@app.route('/clear')
def clear_session():
    session.clear()
    return "Session cleared. Go to /admin to restart."


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv("PORT", 5000)))

#Render
@app.route('/view_csv/<filename>')
def view_csv(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return f.read()
    return "File not found"

@app.route('/download_csv/<filename>')
def download_csv(filename):
    if os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    return "File not found"
#python -m venv .venv
#.venv\Scripts\activate
#pip install -r requirements.txt
#pip freeze > requirements.txt