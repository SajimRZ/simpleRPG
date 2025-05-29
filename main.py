from flask import Flask, render_template, request, redirect, url_for, session
import random
from functools import wraps
import os

app = Flask(__name__, 
            template_folder='Templates', 
            static_folder='static')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-default-dev-secret-key')

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
    session['turn'] = 'player'

# Decorator to ensure game is active for certain routes
def game_active_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('game_active'):
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/',methods=["GET", "POST"])
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

#The Dungeon Screen
@app.route('/dungeon')
@game_active_required
def dungeon():
    if session['dungeon']['enemy'] is None and not session['dungeon']['in_shop']:
        enter_dungeon()
    return render_template('dungeon.html')

#All in one button
@app.route('/action', methods=['POST'])
@game_active_required
def action():
    player = session['player']
    dungeon = session['dungeon']
    
    if dungeon['in_shop']:
        return redirect(url_for('dungeon'))
    
    enemy = dungeon['enemy']
    enemy_name = enemy['name'] if enemy else 'No Enemy'
    enemy_xp = enemy['exp_reward'] if enemy else 0
    enemy_gold = enemy['gold_reward'] if enemy else 0
    
    #player roll prep
    rolls = []
    total_damage = 0
    player_damage = 0
    #enemy roll prep
    enemy_rolls = []
    enemy_damage = 0
    
    #turn rotation
    if session['turn'] == 'player':
        # Player's turn
        
        for _ in range(player['dice_count']):
            roll = random.choice(player['dice'])
            rolls.append(roll)
            total_damage += roll 

            #damage calculation
            enemy['hp'] -= total_damage
            player_damage = total_damage
            
            # Check if enemy is defeated
            if enemy['hp'] <= 0:
                enemy_defeated()
                #return redirect(url_for('dungeon'))
                return render_template('dungeon.html', 
                         player_rolls=rolls, 
                         player_damage=player_damage,
                         enemy_rolls=enemy_rolls,
                         enemy_damage=enemy_damage,
                         enemy_name=enemy_name,
                         enemy_exp=enemy_xp,
                         enemy_gold=enemy_gold
                         )
        #observe the turn change
        session['turn'] = 'enemy'

    elif session['turn'] == 'enemy':
    
        # Enemy's turn
       
        for _ in range(enemy['dice_count']):
            roll = random.choice(enemy['dice'])
            enemy_rolls.append(roll)
            enemy_damage += roll
        
        player['hp'] -= enemy_damage
        
        # Check if player is defeated
        if player['hp'] <= 0:
            session['game_active'] = False
            return redirect(url_for('index'))
        #observe the turn change
        session['turn'] = 'inter'

    elif session['turn'] == 'inter':
        # Intermission turn, just switch back to player
        session['turn'] = 'player'      
    elif session['turn'] == 'reward':
        # Reward turn, just switch back to player
        session['dungeon']['enemy'] = None  # Clear enemy after reward
        session['turn'] = 'player'
        return redirect(url_for('dungeon'))     
    
    session['player'] = player
    session['dungeon']['enemy'] = enemy
    
    return render_template('dungeon.html', 
                         player_rolls=rolls, 
                         player_damage=player_damage,
                         enemy_rolls=enemy_rolls,
                         enemy_damage=enemy_damage,
                         enemy_name=enemy_name,
                         enemy_exp=enemy_xp,
                         enemy_gold=enemy_gold
                         )

#What happens in the dungeon html page
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

#Create an enemy
def generate_enemy(floor):

    enemy_index = enemy_stats(floor)
    enemy_type = random.choice(list(enemy_index.values()))
   
    
    return enemy_type

#enemy defeated, rewards given, turn = 'reward'
def enemy_defeated():
    player = session['player']
    enemy = session['dungeon']['enemy']

    session['turn'] = 'reward'
    
    #player gets the loot
    player['gold'] += enemy['gold_reward']
    player['exp'] += enemy['exp_reward']
    
    # Check for level up
    if player['exp'] >= player['exp_to_level']:
        player['level'] += 1
        player['max_hp'] += 5
        player['hp'] = player['max_hp']
        player['exp'] -= player['exp_to_level']
        player['exp_to_level'] = int(player['exp_to_level'] * 1.5)
        
    
    #session['dungeon']['enemy'] = None
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
    
    return redirect(url_for('dungeon'))

@app.route('/rest', methods=['POST'])
@game_active_required
def rest():
    player = session['player']
    cost = 10
    
    if player['gold'] >= cost:
        player['gold'] -= cost
        player['hp'] = player['max_hp']
    
    session['player']['dice'] = player['dice']
    session['player']['gold'] = player['gold']
    
    session['dungeon']['in_shop'] = False
    enter_dungeon()
    return redirect(url_for('dungeon'))

@app.route('/leave_shop', methods=['POST'])
@game_active_required
def leave_shop():
    session['dungeon']['in_shop'] = False
    enter_dungeon()
    return redirect(url_for('dungeon'))

@app.route('/quit', methods=['POST'])
@game_active_required
def quit():
    
    session.clear()
    session['game_active'] = False
    return redirect(url_for('index'))

def enemy_stats(floor):
    # Define prefixes for each enemy type
    enemy_prefixes = {
        0: ['Fuzzy', 'Bald', 'Steroid', 'Chimera', 'Skeletal', 'Spiritual', 'Vorpal'],  # Rat
        1: ['Blue', 'Core', 'Tentacle', 'Moon', 'Humanoid', 'abyssal', 'draconic'],  # Slime
        2: ['Blind', 'Echo', 'Parasitic', 'Blood', 'Vampire', 'Noble', 'Sun Touched'],  # Bat
        3: ['Fresh', 'Rot', 'Elder', 'Ancestral', 'Shaman', 'Demonic', 'Litch'],  # Zombie
        4: ['Missing', 'Rusty', 'Metalic', 'Knight', 'Elemental', 'Ghastly', 'Monarch'],  # Armour 
        5: ['Fish', 'Unconvincing', 'Convincing', 'Charming', 'Water-body', 'Royal', 'Posidion'],  #Mermaid 
        6: ['Toy', 'Wooden', 'Lying', 'Soulless', 'Mecha', 'Pinocchio', 'True-Soul'],  # Puppet
        7: ['Wild', 'Armed', 'Warrior', 'Pack', 'Hob', 'Chief', 'Progenator'],  # Goblin
        8: ['Featherless', 'Winged', 'Singing', 'Mature', 'Sky', 'Elder', 'Ruler'],  # Harpy
        9: ['Novice', 'Amature', 'Anxious', 'Crimson', 'Megu', 'Arch', 'Dark'],  # Mage
        10: ['Lesser', 'Small', 'Greater', 'Arcane', 'Queen', 'Origin', 'Arachne'],  # Spider
        11: ['Infant', 'Lizard', 'Ground', 'Adult', 'Silver', 'Gold', 'True'],  # Dragon
        12: ['Imp', 'Infirior', 'Lost','Full','Ancient', 'Sin', 'Primordial']  # Demon
    }
    
    # Base enemy stats with silly fantasy creatures and thematic dice
    base_enemies = {
        0: {'name': 'Rat', 'hp': 5, 'max_hp': 5, 
            'dice': [1,1,2,3,4], 'dice_count': 1, 
            'gold_reward': 5, 'exp_reward': 5},
        
        1: {'name': 'Slime', 'hp': 6, 'max_hp': 6, 
            'dice': [1,2,2,3,6], 'dice_count': 1,  
            'gold_reward': 8, 'exp_reward': 8},
        
        2: {'name': 'Bat', 'hp': 7, 'max_hp': 7, 
            'dice': [1,3,3,5,7], 'dice_count': 1,  
            'gold_reward': 12, 'exp_reward': 5},
        
        3: {'name': 'Zombie', 'hp': 12, 'max_hp': 12, 
            'dice': [1,1,2,6,6,8], 'dice_count': 1,  
            'gold_reward': 6, 'exp_reward': 12},
        
        4: {'name': 'Armour', 'hp': 10, 'max_hp': 10, 
            'dice': [2,2,3,4,5,6], 'dice_count': 1, 
            'gold_reward': 7, 'exp_reward': 6},
        
        5: {'name': 'Mermaid', 'hp': 9, 'max_hp': 9, 
            'dice': [2,4,4,6,8], 'dice_count': 1,
            'gold_reward': 8, 'exp_reward': 8},
        
        6: {'name': 'puppet', 'hp': 16, 'max_hp': 16, 
            'dice': [2,3,4,5,5,6,7], 'dice_count': 1,
            'gold_reward': 12, 'exp_reward': 15},
        
        7: {'name': 'Goblin', 'hp': 16, 'max_hp': 16, 
            'dice': [2,3,4,4,6,8], 'dice_count': 1,
            'gold_reward': 11, 'exp_reward': 12},
        
        8: {'name': 'Harpy', 'hp': 13, 'max_hp': 13, 
            'dice': [3,5,5,7,9], 'dice_count': 1, 
            'gold_reward': 10, 'exp_reward': 14},
        
        9: {'name': 'Mage', 'hp': 19, 'max_hp': 19, 
            'dice': [2,3,4,5,6,8], 'dice_count': 1,
            'gold_reward': 8, 'exp_reward': 15},
        
        10: {'name': 'Spider', 'hp': 20, 'max_hp': 20, 
             'dice': [3,5,6,7,8,9], 'dice_count': 1,
             'gold_reward': 13, 'exp_reward': 18},
        
        11: {'name': 'Dragon', 'hp': 27, 'max_hp': 27, 
             'dice': [4,5,6,7,8,9], 'dice_count': 1,
             'gold_reward': 15, 'exp_reward': 20},
        
        12: {'name': 'Demon', 'hp': 32, 'max_hp': 32, 
             'dice': [5,6,7,7,8], 'dice_count': 1,  # Sick burns (literal and metaphorical)
             'gold_reward': 20, 'exp_reward': 30}
    }
    
    scaled_enemies = {}
    
    # Determine scaling factors based on floor
    scale_tier = floor // 10
    hp_scale = 1 + (scale_tier * 0.4)  # 40% more HP per tier
    dmg_scale = 1 + (scale_tier * 0.3)  # 30% more damage per tier
    reward_scale = 1 + (scale_tier * 0.6)  # 60% more rewards per tier
    
    for enemy_id, enemy in base_enemies.items():
        # Create copy to modify
        scaled_enemy = enemy.copy()
        
        # Add prefix 
        if floor > 0:
            prefixes = enemy_prefixes.get(enemy_id, []) #all frefixes for the enemy type
            if prefixes:
                prefix = prefixes[min(floor // 10, len(prefixes) - 1)] #set prefix based on floor, if floor exceeds then use the last one
                scaled_enemy['name'] = f"{prefix} {enemy['name']}"
        
        # Scale HP
        scaled_enemy['hp'] = int(enemy['hp'] * hp_scale)
        scaled_enemy['max_hp'] = int(enemy['max_hp'] * hp_scale)
        
        # Scale damage dice
        scaled_enemy['dice'] = [max(1, int(x * dmg_scale)) for x in enemy['dice']]
        
        # Scale rewards
        if 'gold_reward' in enemy:
            scaled_enemy['gold_reward'] = int(enemy['gold_reward'] * reward_scale)
        if 'exp_reward' in enemy:
            scaled_enemy['exp_reward'] = int(enemy['exp_reward'] * reward_scale)
        
        scaled_enemies[enemy_id] = scaled_enemy
    
    return scaled_enemies
    


if __name__ == '__main__':
    app.run(debug=True)

