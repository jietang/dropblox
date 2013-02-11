import json
import os
import sys
import webbrowser
import requests

def generate_game_file(game_dir):
    response = {'code': 200,
                'states': [],
                'active': False
                }
    state_files = [file for file in os.listdir(game_dir) if file.startswith('state')]
     
    states = [int(state_file[5:]) for state_file in state_files]
    for state in sorted(states):
        with open(os.path.join(game_dir, 'state%s' % (state,))) as f:
            state_data = f.read()
        try:
            with open(os.path.join(game_dir, 'move%s' % (state,))) as f:
                move_data = f.read()
        except Exception:
            move_data = '[]'
        
        response['states'].append({
            'id': 0,
            'state': state_data,
            "moves": move_data,
            })
    return json.dumps(response)

def find_most_recent_game(d='history'):
    return sorted([(os.stat(os.path.join(d, f)).st_mtime, os.path.join(d, f)) for f in os.listdir(d)], reverse=True)[0][1]

if __name__ == "__main__":
    # read in the directory, generate the file    
    if len(sys.argv) <= 1:
        game_dir = find_most_recent_game()
    else:
        game_dir = sys.argv[1]

    r = requests.post("http://localhost:8080/post_game", data=generate_game_file(game_dir))
    webbrowser.open("http://localhost:8080/view_game?id=%s" % r.text)
