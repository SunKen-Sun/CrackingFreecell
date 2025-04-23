#!/usr/bin/env python3

import re
import heapq
import copy
import time 
import pymem
import mem_func_attack

pm= pymem.Pymem(r"C:\Users\ludlo\Downloads\Group Project_T2\Group Project_T2\freecell.exe.i64")
suits = {0: "C", "C":0, 1: "D", "D":1, 2: "H", "H":2, 3: "S", "S":3}
# have both the bit to suit and suit to bit to make access easy and consistent

def decode_card(hex_value):

    ranks = ["A", "2", "3", "4", "5", "6", "7",
             "8", "9", "10", "J", "Q", "K"]

    try:
        suit_bit = hex_value & 0x03
        rank_index = (hex_value >> 2)

        if suit_bit not in suits or rank_index >= len(ranks):
            return None

        return f"{ranks[rank_index]}{suits[suit_bit]}"
    except:
        return None

def scan_hex_dump(hex_data):

    clean_hex = re.sub(r'[^0-9a-fA-F]', '', hex_data)

    card_values = re.findall(r'[0-9a-fA-F]{8}', clean_hex)

    results = []
    for value in card_values:
        num = int(value, 16)
        decoded = decode_card(num)
        if decoded:
            results.append((f"0x{value.upper()}", decoded))
            skip = 3
            continue

    return results

def print_cards(cards):
    for col in cards:
        for c in col:
            if not c: continue
            print(f"{c}", end="\t")
        print()

def fix_card_structure(cards):

    cascades = [ [] for _ in range(8)]
    j = -1
    for i, c in enumerate(cards):

        if i < 28:  #first 4 columns
            col = i // 7
            pos = i % 7
        else:  #last 4 columns
            col = 4 + (i - 28) // 6  # Columns 4-7
            pos = (i - 28) % 6
        # cascades[col][pos] = c[1]
        cascades[col].append(c[1])

    return cascades

def reconstruct_path(final_state, parent_state, final_move, visited):
    path = []
    print(len(visited))
    current_state = final_state
    current_move = final_move
    current_parent = parent_state
    p = 1000
    return final_state

    # Backtrack until we reach the initial state (parent=None)
    while current_parent is not None:
        path.append((current_move, current_state))  # Store (move, resulting_state)
        # Move up the chain
        if p <0: break
        p -=1
        for prev_state_info in visited:  # Note: Requires storing parents in `visited` (see optimization below)
            if state_hash(prev_state_info[3]) == state_hash(current_parent):
                current_move = prev_state_info[5]  # move_used
                current_parent = prev_state_info[4]  # parent_state
                break
        else:
            break  # Safety check

    path.reverse()  # Order: init -> solution
    return path

def solve(board):
    q = []
    visited = set()
    
    init = {"cascade": board["cascade"], "freecell": board["freecell"], "foundation":  board["foundation"]}
    # (how many cards in foundation, moves took to get here, id of state, then actual state
    heapq.heappush(q, ( 0, 0, id(init), init, None, None))

    while q:
        prio, cost, _, state, parent, __ = heapq.heappop(q)

        if solved(state['foundation']): return [state, cost] #reconstruct_path(state, parent, __, visited)

        if state_hash(state) in visited: continue
        visited.add(state_hash(state))

        for move in valid_moves(state):
            new_state = make_move(state, move)
            '''
            if move['type'] == "free_to_foundation": 
                #if move['type'] == 'to_foundation' or move['type'] == "free_to_foundation": 
                #print(f"\n\n{state} -> \n{move} -> \n{new_state}\n\n")
                #print(f"\n\n{state} -> \n{move} -> \n{new_state}\n\n")
            '''
            if state_hash(new_state) not in visited:
                 
                heapq.heappush(q, (priority(new_state), cost +1, id(new_state),  new_state, parent, move))

    return None

def priority(state):

    # lower score = better
    # high priority for having more cards in the foundation and less cards in the free cell
    s = sum(len(fond) for fond in state['foundation']) 
    return (-s )


def valid_moves(state):
    moves = []
    for col, cascade in enumerate(state["cascade"]):
        if not cascade: continue
        top_card = cascade[-1]
        
        index = [i for i, card in enumerate(state["cascade"]) if card == top_card]
        #print(f"top_card: {top_card}")
        if check_foundation(top_card, state['foundation']):
            #need to identify the location of suits
            suit_location = [i for i, card in enumerate(state["foundation"]) if top_card[1] == card[1]]
            moves.append({  "type": "to_foundation", "from" :  col,"c_index": index, "card": top_card, "move_col": 0, "move_ind": suit_location})

        if check_empty(state["freecell"]): 
            empty_loc = [i for i, card in enumerate(state["freecell"])if card == None]                  
            moves.append({"type": "to_freecell", "from":  col, "c_index": index, "card":top_card, "move_col":0, "move_ind":empty_loc})
        # 2 checks of just moving a card to either base foundation or a free cell

        for dst_col, dst_cas in enumerate(state["cascade"]): # trying to move card to each different cascade
            if col==dst_col: continue

            elif check_stack(top_card, dst_cas): 
                index_card = len(state["cascade"][dst_col]) + 1
                moves.append({"type": "cascade_to_cascade", "from" : col, "c_index": index, "move_col":  dst_col, "card": top_card, "move_ind": index_card})


    for cell_index, card in enumerate(state["freecell"]):# trying to move freecell cards to foundation or cascade
        index = [i for i, e_card in enumerate(cascade) if e_card == card]
        if card is None: continue

        if check_foundation(card, state['foundation']):
             suit_location = [i for i, card in enumerate(state["foundation"]) if top_card[1] == card[1]]
            moves.append({  "type": "free_to_foundation", "from" : cell_index, "c_index": index, "card": card, "move_col":0, "move_ind": suit_location})
        for dst_col, dst_cas in enumerate(state["cascade"]):
            index_card = len(state["cascade"][dst_col]) + 1
            if not dst_cas: continue

            if check_stack(card, dst_cas): moves.append({"type": "free_to_cascade", "from": cell_index, "c_index": index, "move_col": dst_col, "card": card, "move_ind":index_card})

    return moves

## NEED TO ACCOUNT FOR: 
#       automated moves, when you move from cascade to a foundation i think all other potential foundation moves will automatically be made

'''
    HELPER FUNCTIONS
    make_move is an orchestrator and calls these helper functions
    they are what alter a specific part of the state to have the changes that would be made with a given action 
'''
def add_to_foundation(card, foundation):
    foundation[suits[card[-1]]].append(card)
    
def remove_from_cascade(origin, cascade):
    if len(cascade[origin]) ==0:
        return
    c = cascade[origin].pop()

def add_to_cascade(card, to, cascade):
    cascade[to].append(card)

def add_to_freecell(card, freecell):
    
    for i,c in enumerate(freecell): 
        if not c: 
            freecell[i] = card    
            break

def remove_from_freecell(card, freecell):

    for i, c in enumerate(freecell): 
        if c == card: 
            freecell[i] = None    
            break

def make_move(state, move):

    '''
    1) cas to foundation
    2) cas to freecell
    3) cas to cas
    4) freecell to foundation
    5) freecell to cas
    '''

    # given the move description, alter the state to reflect what it would be if the state was chosen.
    move_t = move["type"]
    card = move["card"]
    move_f = move["from"] #col
    index = move["c_index"] #index specified card for shell injection
    #New location address
    move_col = move["move_col"]
    move_index = move["move_index"]
    
    new_state = {"cascade": copy.deepcopy(state["cascade"]), "freecell": state["freecell"].copy(), "foundation": copy.deepcopy(state["foundation"])}
    
    if move_t == "to_foundation":
        add_to_foundation(card, new_state["foundation"])
        mem_func_attack.Inject_shell_code(pm,move_f, index)
        remove_from_cascade(move_f, new_state["cascade"])
        #mem_func_attack.identify_message_box(pm);
        mem_func_attack.Inject_shell_code(pm,move_col, move_index)
        mem_func_attack.identify_message_box(pm);
        
    elif move_t == "to_freecell": 
        add_to_freecell(card, new_state["freecell"])   
        mem_func_attack.Inject_shell_code(pm,move_f, index)
        remove_from_cascade(move_f, new_state["cascade"])
        mem_func_attack.Inject_shell_code(pm,move_col, move_index)
        mem_func_attack.identify_message_box(pm);
    elif move_t == "cascade_to_cascade": 
        add_to_cascade(card, move["to"], new_state["cascade"])
        mem_func_attack.Inject_shell_code(pm,move_f, index)
        remove_from_cascade(move_f, new_state["cascade"])
        mem_func_attack.Inject_shell_code(pm,move_col, move_index)
        mem_func_attack.identify_message_box(pm);
    elif move_t == "free_to_foundation":
        add_to_foundation(card, new_state["foundation"])
        mem_func_attack.Inject_shell_code(pm,move_f, index)
        remove_from_freecell(card, new_state["freecell"])
        mem_func_attack.Inject_shell_code(pm,move_col, move_index)
        mem_func_attack.identify_message_box(pm);
        
        
    elif move_t == "free_to_cascade":
        add_to_cascade(card, move["to"], new_state["cascade"])
        mem_func_attack.Inject_shell_code(pm,move_f, index)
        remove_from_freecell(card, new_state["freecell"])
        mem_func_attack.Inject_shell_code(pm,move_col, move_index)
        mem_func_attack.identify_message_box(pm);
    else: print(f"ERROR: {move_t}")

    return new_state

def track(state):
    # go through the state and backtrack to find the solution
    pass

def state_hash(state):

    # call a function that will hash the specific state for future use
    h1 = hash(frozenset(tuple(c) for c in state['cascade']))
    h2 = hash(frozenset(tuple(c) for c in state['foundation']))
    h3 = hash(frozenset(tuple(['freecell']))  )
    return hash(frozenset(tuple([h1, h2, h3])))


def solved(foundation):

    if len(foundation[0]) ==13 and len(foundation[1]) ==13 and len(foundation[2]) ==13 and len(foundation[3]) ==13: return True

    return False

def get_card_value(card): # helper function to break card to get its value 

    if card[0] == 'K': return 13
    if card[0] == 'Q': return 12
    if card[0] == 'J': return 11
    if card[0] == 'A': return 1
    if card[0] == '1': return 10
    else: return int(card[0])

def descending(card1, card2, check_colors): # card 1 = already placed card, card 2 = card trying to make the move
    
    if not card1 or not card2: return False

    val1, suit1 = get_card_value(card1), card1[-1]
    val2, suit2 = get_card_value(card2), card2[-1]

    if (val1 + 1) != val2: return False 
    
    # if we do not need to check for colors, ie for foundation, then just return based on numbers
    if not check_colors: return True

    # checking for same color 
    if (suit1 == 'D' or suit1 =='H') and (suit2=='D' or suit2 =='H'): return False 
    if (suit1 == 'S' or suit1 =='C') and (suit2=='S' or suit2 =='C'): return False 
    return True
    

def check_stack(card, dst_cas):

    # descending will automatically check the color and values for us, just need to seperate the dst_cas
    if len(dst_cas) <1: return True
    return descending(card, dst_cas[-1], True)


def check_foundation(card, foundation):
    # find the foundation the card should be in, see if the card is +1 to the foundation top
    # club, diamond, heart, spade: order program will always put stuff in the foundation.

    suit = card[-1]
    if card[0] =='A': return True 
    # if we have an ace then automatically know we can place card value

    if ((len(foundation[suits[suit]]) + 1)  == get_card_value(card) ) : 
        return True
    #else: print(f"{len(foundation[suits[suit]]) + 1}: {get_card_value(card)}" ) 

    return False

def check_empty(free_cells):

    for cell in free_cells: # just need to check if any free cell is empty
        if not cell:
            return True

    return False



def main():
    print("paste hex dump (ctrl+D to finish):")
    
    hex_dump = []
    while True:
        try:
            line = input()
            hex_dump.append(line)
        except EOFError:
            break

    full_dump = '\n'.join(hex_dump)
    cards = scan_hex_dump(full_dump) # raw string of all the info

    cards=cards[0:52] # ignore any extra bytes read in from the paste
    # cards printed from back left pile to right pile
    # go from back most card to front most in each pile

    cards = fix_card_structure(cards)
    print_cards(cards)
    board = {"cascade": cards, "freecell": [None for n in range(4)],
            "foundation": [[] for n in range(4)] }
    print(board)
    
    start = time.time()
    xop = solve(board)
    print(len(cards))
    
    print(f"got {xop}")
    print(f"{time.time()-start}")

if __name__ == "__main__":
    main()
