from flask import Flask, render_template, request, redirect, url_for, session
import random
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Initialize game state
def init_game():
    session.clear()
    session['player'] = {
        'hp': 20,
        'max_hp': 20,
        'gold': 0,
        'exp': 0,
        'level': 1,
        'dice': [1, 2, 3, 4, 5, 6],  # Default dice faces
        'dice_count': 1,  # Number of dice to roll
        'exp_to_level': 10
    }
    session['dungeon'] = {
        'floor': 0,
        'enemy': None,
        'in_shop': False
    }
    session['game_active'] = False

# Decorator to ensure game is active for certain routes
def game_active_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('game_active'):
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    init_game()
    return render_template('index.html')

def vercel_handler(request):
    from flask import Response
    with app.app_context():
        response = app.full_dispatch_request()
        return Response(
            response.get_data(),
            status=response.status_code,
            headers=dict(response.headers)
        )

@app.route('/start_game', methods=['POST'])
def start_game():
    init_game()
    session['game_active'] = True
    enter_dungeon()
    return redirect(url_for('dungeon'))

@app.route('/dungeon')
@game_active_required
def dungeon():
    if session['dungeon']['enemy'] is None and not session['dungeon']['in_shop']:
        enter_dungeon()
    return render_template('dungeon.html')

@app.route('/attack', methods=['POST'])
@game_active_required
def attack():
    player = session['player']
    dungeon = session['dungeon']
    
    if dungeon['in_shop']:
        return redirect(url_for('dungeon'))
    
    enemy = dungeon['enemy']
    
    # Player's turn
    rolls = []
    total_damage = 0
    for _ in range(player['dice_count']):
        roll = random.choice(player['dice'])
        rolls.append(roll)
        total_damage += roll
    
    enemy['hp'] -= total_damage
    player_damage = total_damage
    
    # Check if enemy is defeated
    if enemy['hp'] <= 0:
        enemy_defeated()
        return redirect(url_for('dungeon'))
    
    # Enemy's turn
    enemy_rolls = []
    enemy_damage = 0
    for _ in range(enemy['dice_count']):
        roll = random.choice(enemy['dice'])
        enemy_rolls.append(roll)
        enemy_damage += roll
    
    player['hp'] -= enemy_damage
    
    # Check if player is defeated
    if player['hp'] <= 0:
        session['game_active'] = False
        return redirect(url_for('index'))
    
    session['player'] = player
    session['dungeon']['enemy'] = enemy
    
    return render_template('dungeon.html', 
                         player_rolls=rolls, 
                         player_damage=player_damage,
                         enemy_rolls=enemy_rolls,
                         enemy_damage=enemy_damage
                         )

def enter_dungeon():
    dungeon = session['dungeon']
    dungeon['floor'] += 1
    
    # Every 5 floors, show shop instead of enemy
    if dungeon['floor'] % 5 == 0:
        dungeon['in_shop'] = True
        dungeon['enemy'] = None
    else:
        dungeon['in_shop'] = False
        dungeon['enemy'] = generate_enemy(dungeon['floor'])
    
    session['dungeon'] = dungeon

def generate_enemy(floor):
    base_hp = 5 + floor * 5
    base_dice = [1 + floor // 3, 2 + floor // 4, 3 + floor // 4, 
                 4 + floor // 5, 5 + floor // 5, 6 + floor // 3]
    
    # Higher floors have a chance for multiple dice
    dice_count = 1
    if floor >= 10 and random.random() < 0.3:
        dice_count = 2
    if floor >= 20 and random.random() < 0.2:
        dice_count = 3
    
    return {
        'name': random.choice(['Goblin', 'Orc', 'Skeleton', 'Zombie', 'Spider', 'Troll']),
        'hp': base_hp,
        'max_hp': base_hp,
        'dice': base_dice,
        'dice_count': dice_count,
        'gold_reward': random.randint(5, 10) + floor * 2,
        'exp_reward': random.randint(5, 10) + floor
    }

def enemy_defeated():
    player = session['player']
    enemy = session['dungeon']['enemy']
    
    player['gold'] += enemy['gold_reward']
    player['exp'] += enemy['exp_reward']
    
    # Check for level up
    if player['exp'] >= player['exp_to_level']:
        player['level'] += 1
        player['max_hp'] += 5
        player['hp'] = player['max_hp']
        player['exp'] -= player['exp_to_level']
        player['exp_to_level'] = int(player['exp_to_level'] * 1.5)
        
        # Add a new dice face at level up
        new_face = max(player['dice']) + 1
        player['dice'].append(new_face)
    
    session['dungeon']['enemy'] = None
    session['player'] = player

@app.route('/upgrade', methods=['POST'])
@game_active_required
def upgrade():
    face_index = int(request.form['face_index'])
    cost = int(request.form['cost'])
    
    player = session['player']
    
    if player['gold'] >= cost:
        player['gold'] -= cost
        player['dice'][face_index] += 1
        session['player'] = player
    
    return redirect(url_for('dungeon'))

@app.route('/buy_dice', methods=['POST'])
@game_active_required
def buy_dice():
    player = session['player']
    cost = 50 * player['dice_count']  # Scaling cost
    
    if player['gold'] >= cost:
        player['gold'] -= cost
        player['dice_count'] += 1
        session['player'] = player
    
    session['dungeon']['in_shop'] = False
    return redirect(url_for('dungeon'))

@app.route('/rest', methods=['POST'])
@game_active_required
def rest():
    player = session['player']
    cost = 10
    
    if player['gold'] >= cost:
        player['gold'] -= cost
        player['hp'] = player['max_hp']
        session['player'] = player
    
    session['dungeon']['in_shop'] = False
    return redirect(url_for('dungeon'))

@app.route('/leave_shop', methods=['POST'])
@game_active_required
def leave_shop():
    session['dungeon']['in_shop'] = False
    return redirect(url_for('dungeon'))

if __name__ == '__main__':
    app.run(debug=True)