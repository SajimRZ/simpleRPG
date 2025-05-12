from flask import Flask, render_template, request, redirect, url_for, session
import random

app = Flask(__name__)
app.secret_key = 'SoloLeveling'

def init_game():
    session['player_hp'] = 100
    session['player_maxhp'] = session['player_hp']
    session['enemy_type'] = None
    session['enemy_hp'] = None
    
    session['level'] = 1
    session['exp'] = 0
    session['num'] = 1
    session['Turn'] = 'Player'
    session['player_attack'] = 10
    session['game over'] = False
    


@app.route('/')
def index():
    if 'player_hp' not in session:
        init_game()
    session['enemy_type'] = random.choice(['Goblin', 'Orc', 'Troll', 'Dragon', 'Vampire', 'Zombie', 'Skeleton'])

    if session['enemy_type'] == 'Goblin':       session['enemy_hp'] = 50; session['enemy_attack'] = 5
    elif session['enemy_type'] == 'Orc':        session['enemy_hp'] = 80; session['enemy_attack'] = 5
    elif session['enemy_type'] == 'Troll':      session['enemy_hp'] = 120; session['enemy_attack'] = 5
    elif session['enemy_type'] == 'Dragon':     session['enemy_hp'] = 200; session['enemy_attack'] = 5
    elif session['enemy_type'] == 'Vampire':    session['enemy_hp'] = 150; session['enemy_attack'] = 5
    elif session['enemy_type'] == 'Zombie':     session['enemy_hp'] = 60; session['enemy_attack'] = 5
    elif session['enemy_type'] == 'Skeleton':   session['enemy_hp'] = 100; session['enemy_attack'] = 5

    return render_template('index.html')




if __name__ == '__main__':
    app.run(debug=True)

