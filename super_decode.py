#!/usr/bin/env python3

import re
import heapq
import copy
import time
import pymem
import mem_func_attack
import pyautogui
import tkinter
import sys
root = tkinter.Tk()
WIDTH = root.winfo_screenwidth()
HEIGHT = root.winfo_screenheight()
root.destroy()

pm= pymem.Pymem(r"freecell.exe")

suits = {0: "C", "C":0, 1: "D", "D":1, 2: "H", "H":2, 3: "S", "S":3}
# have both the bit to suit and suit to bit to make access easy and consistent

move_id = 0
foundations_set = -1
fz = []
# used to keep track of what moves the path actually ended up using

CASCADE_TO_FOUNDATION   = "CAS_TO_FOUND"
CASCADE_TO_CASCADE      = "CAS_TO_CAS"
CASCADE_TO_FREE         = "CAS_TO_FREE"
FREE_TO_CASCADE         = "FREE_TO_CAS"
FREE_TO_FOUNDATION      = "FREE_TO_FOUND"


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

def scan_hex_dump(hex_data): # OUTDATED

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
        cascades[col].append(c)

    return cascades

def solve(board):
    q = []
    visited = set()
    moves = dict()

    init = {"cascade": board["cascade"], "freecell": board["freecell"], "foundation":  board["foundation"], 'moves': dict() }
    heapq.heappush(q, ( 0, 0, id(init), init, None))

    # heapq has [priority to be sorted by, amount of moves it took to get here, id of state (for uniqueness),  current state, parent state ]
    while q:
        _, cost,___,  state, parent = heapq.heappop(q)

        if solved(state['foundation']): return [state, cost, moves]

        if state_hash(state) in visited: continue
        visited.add(state_hash(state))
        vm = valid_moves(state)
        for move in vm:
            new_state = make_move(state, move)
            if state_hash(new_state) not in visited:
                global move_id
                move_id +=1
                if move_id%50000 ==0: 
                    print(f"at move: {move_id} {state}\n")
                moves[move_id] = move
                new_state['moves'][move_id] = None
                if len(vm) ==1: move['len'] = 1
                # using a dict here because it acts like a set but still keeps the order of stuff to loop over at the end
                heapq.heappush(q, (priority(new_state), cost +1, id(new_state),  new_state, parent))

    return [None, None, None]

def priority(state):

    # lower score = better
    # high priority for having more cards in the foundation and less cards in the free cell
    s = [len(fond) for fond in state['foundation']]

    return -sum(s)


def valid_moves(state):
    moves = []
    for col, cascade in enumerate(state["cascade"]):
        if not cascade: continue
        top_card = cascade[-1]
        
        # index = [i for i, card in enumerate(state["cascade"]) if card == top_card]
        index = len(cascade)
        #print(f"top_card: {top_card}")
        if check_foundation(top_card, state['foundation']):
            #need to identify the location of suits
            suit_location = get_foundation_index(top_card, state['foundation'])
            moves.append({  "type": CASCADE_TO_FOUNDATION, "from" :  col,"c_index": index, "card": top_card, "move_col": 0, "move_ind": suit_location})

        if check_empty(state["freecell"]): 
            empty_loc = [i for i, card in enumerate(state["freecell"])if card == None]                  
            moves.append({"type": CASCADE_TO_FREE, "from":  col, "c_index": index, "card":top_card, "move_col":0, "move_ind":empty_loc[0]})
        # 2 checks of just moving a card to either base foundation or a free cell

        for dst_col, dst_cas in enumerate(state["cascade"]): # trying to move card to each different cascade
            if col==dst_col: continue

            elif check_stack(top_card, dst_cas): 
                index_card = len(state["cascade"][dst_col]) + 1
                moves.append({"type": CASCADE_TO_CASCADE, "from" : col, "c_index": index, "move_col":  dst_col, "card": top_card, "move_ind": index_card})


    for cell_index, card in enumerate(state["freecell"]):# trying to move freecell cards to foundation or cascade
        index = [i for i, e_card in enumerate(cascade) if e_card == card]
        if card is None: continue

        if check_foundation(card, state['foundation']):
            suit_location = get_foundation_index(card, state['foundation'])
            moves.append({  "type": FREE_TO_FOUNDATION, "from" : cell_index, "c_index": index, "card": card, "move_col":0, "move_ind": suit_location})
        for dst_col, dst_cas in enumerate(state["cascade"]):
            index_card = len(state["cascade"][dst_col]) + 1
            if not dst_cas: continue

            if check_stack(card, dst_cas): moves.append({"type": FREE_TO_CASCADE, "from": cell_index, "c_index": index, "move_col": dst_col, "card": card, "move_ind":index_card})

    return moves

## NEED TO ACCOUNT FOR:
#       automated moves, when you move from cascade to a foundation i think all other potential foundation moves will automatically be made

'''
    HELPER FUNCTIONS
    make_move is an orchestrator and calls these helper functions
    they are what alter a specific part of the state to have the changes that would be made with a given action
'''
def add_to_foundation(card, foundation):
    global foundations_set
    if card[0] =='A' and card not in fz:
        if card=='AC': print(f"HERE: {foundation} {fz} {foundations_set}")
        fz.append(card)

    foundation[get_foundation_index(card, foundation)].append(card)

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

def make_move(state, move): # simulates being at state1, taking move, then ending at state2. there is no gurantee that state2 is actually needed for the final solution though

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
    move_f = move["from"]
    new_state = {"cascade": copy.deepcopy(state["cascade"]), "freecell": state["freecell"].copy(), "foundation": copy.deepcopy(state["foundation"]), 'moves': state['moves'].copy()}

    if move_t == CASCADE_TO_FOUNDATION:            
        add_to_foundation(card, new_state["foundation"])
        remove_from_cascade(move_f, new_state["cascade"])
    elif move_t == CASCADE_TO_FREE:
        add_to_freecell(card, new_state["freecell"])
        remove_from_cascade(move_f, new_state["cascade"])
    elif move_t == CASCADE_TO_CASCADE:
        add_to_cascade(card, move["move_col"], new_state["cascade"])
        remove_from_cascade(move_f, new_state["cascade"])
    elif move_t == FREE_TO_FOUNDATION:
        add_to_foundation(card, new_state["foundation"])
        remove_from_freecell(card, new_state["freecell"])
    elif move_t == FREE_TO_CASCADE:
        add_to_cascade(card, move["move_col"], new_state["cascade"])
        remove_from_freecell(card, new_state["freecell"])
    else: print(f"ERROR: {move_t}")

    return new_state


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
    if card[0] == '1': return 10  # if card is 10, ie 10D then will start with 1 -> return 10. if card is an ace it will be AD so no need to worry about other first chars being a 1
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

def get_foundation_index(card, foundation):
    suit = card[-1]
    '''
    if card[0] =='A':
        if card in fz: 
            return fz.index(card)
        return len(fz)
    '''
    for i, f in enumerate(foundation): 
        if not f : 
            if card[0] =='A': return i
            continue
        if f[0][-1] == suit: return i
    return 4

def check_foundation(card, foundation):
    # find the foundation the card should be in, see if the card is +1 to the foundation top
    # club, diamond, heart, spade: order program will always put stuff in the foundation.

    suit = card[-1]
    #print(f"{card} - {foundation}")

    if card[0] =='A': 
        return True
    # if we have an ace then automatically know we can place card value
    index = get_foundation_index(card, foundation)
    if ((len(foundation[index]) + 1)  == get_card_value(card) ) :
        return True

    return False

def check_empty(free_cells):

    for cell in free_cells: # just need to check if any free cell is empty
        if not cell:
            return True
    return False

def move_cursor(move):
  
    x = 0
    y= 0
    x1 = 0
    y1 = 0

    if move['type'] == CASCADE_TO_FOUNDATION:
        x, y = (move['from']+1) *125, 610+(move['c_index']-7)*30
        x1, y1 = 675 + move['move_ind']*125, 200

    if move['type'] == CASCADE_TO_FREE:
        x, y = (move['from']+1) *125, 610+(move['c_index']-7)*30
        x1, y1 = (1 + move['move_ind'])*100, 200

    if move['type'] == CASCADE_TO_CASCADE:
        x, y = (move['from']+1) *125, 610+(move['c_index']-7)*30
        x1, y1 = (move['move_col']+1) *125, 610 + (move['move_ind'] -7) * 30
 
    if move['type'] == FREE_TO_CASCADE:
        x, y = (1 + move['from'])*100, 200
        x1, y1 = (move['move_col']+1) *125, 610 + (move['move_ind'] -7) * 30


    if move['type'] == FREE_TO_FOUNDATION:
        x, y = (1 + move['from'])*100, 200
        x1, y1 = 675 + move['move_ind']*125, 200

    pyautogui.moveTo(x,y)
    pyautogui.click()
    pyautogui.moveTo(x1, y1)
    pyautogui.click()
    pyautogui.moveTo(250,370) ## place to go to click cancel on the popup
    pyautogui.click()
    pyautogui.moveTo(530, 125)  # place to go in case accidentally clicked a card, undos the potential card click
    pyautogui.click()
    # print(f"start: {x}, {y}]\t end: {x1}, {y1}")


def main():
    print("make sure executable is running and path to exe is set in the PM:")
    print("Also make sure window for freecell is in the top left")
    hex_vals = mem_func_attack.get_initial_cards(pm) # returns the raw data values of the entire chunk of code where the cascade is 
    cards = []
    print(WIDTH)
    print(HEIGHT)
    
    

    for h in hex_vals:
        decoded = decode_card(h)
        if decoded: cards.append(decoded) # some values arent actuall cards, ie buffer spaces and the such, so double check they are cards before adding them
    print(cards)
    cards=cards[0:52] # ignore any extra bytes read in 
    # cards printed from back left pile to right pile
    # go from back most card to front most in each pile

    cards = fix_card_structure(cards)
    board = {"cascade": cards, "freecell": [None for n in range(4)],
            "foundation": [[] for n in range(5)] } # 5th place in the foundation is a dummy place so out of bounds doesnt happen
    print(board)

    start = time.time()
    xop, cost, moves = solve(board)
    print(len(cards))

    print(f"got {xop}")
    print(f"{cost} vs {len(xop['moves'])} vs {len(moves)}")
    print(f"{time.time()-start}")

    # ensures we are 'clicked in' to the free cell application
    pyautogui.moveTo(200,200)
    pyautogui.mouseDown()
    pyautogui.mouseUp()
    mult = 1
    for i,id in enumerate(xop['moves']): ## area of actually simulating going through the moves in order, each move is guranteed to be in the path for the correct end goal
        move  = moves[id]
        #mem_func_attack.Inject_shell_code(pm,move['from'], move['c_index'])
        print(f"{i}, {id} - {moves[id]}")
        if len(sys.argv) ==1: move_cursor(move)
        if pyautogui.position()[1] <=100: break


if __name__ == "__main__":
    main()