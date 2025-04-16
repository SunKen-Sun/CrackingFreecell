#!/usr/bin/env python3

import re

def decode_card(hex_value):

    suits = {0: "C", 2: "H", 1: "D", 3: "S"}
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

    card_values = re.findall(r'[0-9a-fA-F]{2}', clean_hex)

    results = []
    skip = 0 # each card is padded by a group of zeros after it is read, this just skips over the zeros so the code doesnt confuse them for ace of clubs
    for value in card_values:
        if skip>0:
            skip -=1
            continue
        num = int(value, 16)
        decoded = decode_card(num)
        if decoded:
            results.append((f"0x{value.upper()}", decoded))
            skip = 3
            continue

    return results

def print_cards(cards):
    for i, c in enumerate(cards):
        if i <= 28:
            if i%7 ==0: print("\n")
            print(f"{c[1]}", end="\t")
        else: # new lines for each row/pile of cards that appear
            if i== 34 or i==40 or  i==46 or i ==53: print("\n")
            print(f"{c[1]}", end="\t")



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
    cards = scan_hex_dump(full_dump)

    cards=cards[0:52]
    # cards printed from back left pile to right pile
    # go from back most card to front most in each pile
    print_cards(cards)
    print()


if __name__ == "__main__":
    main()
