import os
import requests
from flask import Flask, redirect, request, session, url_for, render_template, jsonify, send_file
from zipfile import ZipFile
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import shutil

app = Flask(__name__)
app.secret_key = os.urandom(24)
scheduler = BackgroundScheduler()
scheduler.start()

DISCORD_CLIENT_ID = '1244115588029349949'
DISCORD_CLIENT_SECRET = 'TzUTwKjfgfcpP2iaNl8pyzElsHIruyv3'
DISCORD_REDIRECT_URI = 'http://localhost:5000/callback'

def create_directory(playlist_name):
    if not os.path.exists(playlist_name):
        os.makedirs(playlist_name)

def download_playlist(playlist_url, playlist_name):
    create_directory(playlist_name)
    os.chdir(playlist_name)
    os.system(f'spotdl --playlist {playlist_url}')
    os.chdir('..')

def create_zip(playlist_name):
    zip_filename = f"{playlist_name}.zip"
    with ZipFile(zip_filename, 'w') as zipf:
        for root, _, files in os.walk(playlist_name):
            for file in files:
                zipf.write(os.path.join(root, file))
    shutil.rmtree(playlist_name)  # borrar la carpeta después de comprimir
    return zip_filename

def delete_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Deleted file: {file_path}")

@app.route('/')
def index():
    if 'discord_user' in session:
        return render_template('authenticated.html', user=session['discord_user'])
    else:
        return render_template('index.html')

@app.route('/login')
def login():
    discord_auth_url = (
        f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}"
        "&response_type=code&scope=identify"
    )
    return redirect(discord_auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': DISCORD_REDIRECT_URI,
        'scope': 'identify',
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    r = requests.post('https://discord.com/api/oauth2/token', data=data, headers=headers)
    r.raise_for_status()

    access_token = r.json().get('access_token')
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    user_info = requests.get('https://discord.com/api/users/@me', headers=headers).json()
    session['discord_user'] = user_info
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('discord_user', None)
    return redirect(url_for('index'))

@app.route('/download', methods=['POST'])
def download():
    playlist_name = request.form['playlist_name']
    playlist_url = request.form['playlist_url']
    download_playlist(playlist_url, playlist_name)
    zip_filename = create_zip(playlist_name)

    # Programar la eliminación del archivo en una hora
    run_date = datetime.now() + timedelta(hours=1)
    scheduler.add_job(lambda: delete_file(zip_filename), 'date', run_date=run_date)

    return send_file(zip_filename, as_attachment=True)

@app.route('/progress')
def get_progress():
    global progress
    return jsonify({'progress': progress})

if __name__ == "__main__":
    app.run(debug=True)