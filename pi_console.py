# =====================================================================
# File: pi_console.py
# Description: Simple console to run pi_server flows and view DB.
# =====================================================================

from card_db import CardDatabase
from pi_server import TerminalSession

def main():
    db = CardDatabase()
    while True:
        print("\n1) Single read\n2) List cards\n3) View card\n4) Exit")
        ch = input("> ").strip()
        if ch == "1":
            TerminalSession(db).run()
        elif ch == "2":
            for row in db.list_cards():
                print(row)
        elif ch == "3":
            cid = input("Card id: ").strip()
            print(db.get_card(cid))
        elif ch == "4":
            break

if __name__ == "__main__":
    main()
