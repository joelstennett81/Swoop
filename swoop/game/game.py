import random


class Card:
    def __init__(self, value, suit=None, swoop=False):
        self.value = value
        self.suit = suit
        self.swoop = swoop

    def __repr__(self):
        if self.swoop:
            return "Swoop"
        names = {1: "A", 11: "J", 12: "Q", 13: "K"}
        v = names.get(self.value, str(self.value))
        return f"{v}{self.suit[0].upper()}" if self.suit else v


class Deck:
    def __init__(self, num_players):
        cards_needed = num_players * 19
        deck_size = 54
        num_decks = max(1, -(-cards_needed // deck_size))  # ceiling division

        self.cards = []
        suits = ["hearts", "spades", "diamonds", "clubs"]
        values = list(range(1, 14))
        for _ in range(num_decks):
            for suit in suits:
                for v in values:
                    if v == 10:
                        self.cards.append(Card(v, suit, swoop=True))
                    else:
                        self.cards.append(Card(v, suit))
            # two jokers per deck
            self.cards.append(Card(None, None, swoop=True))
            self.cards.append(Card(None, None, swoop=True))
        random.shuffle(self.cards)

    def draw(self):
        return self.cards.pop() if self.cards else None


class Player:
    def __init__(self, name):
        self.name = name
        self.hand = []
        self.board_up = []
        self.board_down = []
        self.score = 0

    def total_cards(self):
        return len(self.hand) + len(self.board_up) + len(self.board_down)

    def sort_hand(self):
        self.hand.sort(key=lambda c: (c.swoop, c.value if c.value else -1))

    def __repr__(self):
        return f"{self.name} (hand={len(self.hand)}, up={len(self.board_up)}, down={len(self.board_down)})"


class SwoopGame:
    def __init__(self, player_names):
        self.player_names = player_names
        self.players = [Player(name) for name in player_names]
        self.deck = Deck(len(player_names))
        self.pile = []
        self.current_turn = 0
        self.deal_cards()
        self.pick_starting_player()

    # --- setup ---
    def deal_cards(self):
        for p in self.players:
            cards = [self.deck.draw() for _ in range(19)]
            random.shuffle(cards)
            p.board_down = cards[:4]
            p.board_up = cards[4:8]
            p.hand = cards[8:]
            p.sort_hand()

    def pick_starting_player(self):
        highest_vals = []
        for p in self.players:
            non_swoops = [c.value for c in p.hand if not c.swoop]
            max_value = max(non_swoops) if non_swoops else 0
            highest_vals.append((max_value, p))
        start_player = max(highest_vals, key=lambda x: x[0])[1]
        self.current_turn = self.players.index(start_player)

    # --- helpers ---
    def top_value(self):
        if not self.pile:
            return None
        top = self.pile[-1]
        return top.value if not top.swoop else 10

    def valid_values(self, player):
        if not self.pile:
            vals = [c.value for c in player.hand + player.board_up if not c.swoop]
        else:
            top = self.top_value()
            vals = [c.value for c in player.hand + player.board_up if not c.swoop and c.value <= top]

        # Add swoop option if any swoops exist
        swoops = [c for c in player.hand + player.board_up if c.swoop or c.value == 10]
        if swoops:
            vals.append("S")

        return sorted(set(vals), key=lambda v: (-1 if v == "S" else v))

    # --- core actions ---
    def play_normal(self, player_idx, value):
        if value == "S":  # redirect swoop
            return self.play_swoop(player_idx)

        player = self.players[player_idx]
        legal_values = self.valid_values(player)
        if value not in legal_values:
            return {"error": f"Value {value} not valid. Valid: {legal_values}"}

        to_play = [c for c in player.hand + player.board_up if c.value == value]
        for c in to_play:
            if c in player.hand:
                player.hand.remove(c)
            else:
                player.board_up.remove(c)

        self.pile.extend(to_play)

        # 4-of-kind swoop check
        if len(self.pile) >= 4:
            last_four = self.pile[-4:]
            if all(not c.swoop and c.value == last_four[0].value for c in last_four):
                self.pile = []
                return {"action": "swoop-4ofkind", "played": [str(c) for c in to_play], "next": player.name}

        self.next_turn()
        return {"action": "play", "played": [str(c) for c in to_play], "next": self.players[self.current_turn].name}

    def play_swoop(self, player_idx):
        player = self.players[player_idx]
        candidates = [c for c in player.board_up + player.hand if c.swoop or c.value == 10]
        if not candidates:
            return {"error": "No swoop cards in up or hand."}

        # choose from board_up first, then hand
        card = candidates[0]
        if card in player.board_up:
            player.board_up.remove(card)
        else:
            player.hand.remove(card)

        self.pile = []
        return {"action": "swoop", "played": str(card), "next": player.name}

    def play_down(self, player_idx):
        player = self.players[player_idx]
        if not player.board_down:
            return self.force_pickup(player_idx, reason="no-down-cards")

        if len(player.board_down) <= len(player.board_up):
            return {"error": "You cannot have fewer down cards than up cards."}

        card = player.board_down.pop(0)
        print(f"{player.name} flips {card}")

        top = self.top_value()
        if not top or card.swoop or card.value == 10 or (card.value and card.value <= top):
            played = [card]
            if not card.swoop and card.value != 10:
                matching_up = [c for c in player.board_up if c.value == card.value]
                matching_hand = [c for c in player.hand if c.value == card.value]
                for c in matching_up:
                    player.board_up.remove(c)
                for c in matching_hand:
                    player.hand.remove(c)
                played.extend(matching_up + matching_hand)

            self.pile.extend(played)

            if card.swoop or card.value == 10:
                self.pile = []
                return {"action": "swoop-down", "played": [str(c) for c in played], "next": player.name}
            else:
                self.next_turn()
                return {"action": "play-down", "played": [str(c) for c in played],
                        "next": self.players[self.current_turn].name}
        else:
            player.hand.extend(self.pile + [card])
            self.pile = []
            player.sort_hand()
            self.next_turn()
            return {"action": "pickup-down", "picked": str(card), "next": self.players[self.current_turn].name}

    def force_pickup(self, player_idx, reason="no-play"):
        player = self.players[player_idx]
        player.hand.extend(self.pile)
        self.pile = []
        player.sort_hand()
        self.next_turn()
        return {"action": "pickup", "reason": reason, "next": self.players[self.current_turn].name}

    # --- dispatcher ---
    def take_turn(self, player_idx, move_type, value=None):
        if move_type == "play":
            return self.play_normal(player_idx, value)
        elif move_type == "down":
            return self.play_down(player_idx)
        elif move_type == "pickup":
            return self.force_pickup(player_idx, reason="forced")
        else:
            return {"error": "Unknown move type"}

    # --- state / printing ---
    def next_turn(self):
        self.current_turn = (self.current_turn + 1) % len(self.players)

    def print_state(self):
        print("\n=== Game State ===")
        print(f"Turn: {self.players[self.current_turn].name}")
        print("Pile:", [str(c) for c in self.pile] if self.pile else "empty")

        for p in self.players:
            hand_preview = " ".join(str(c) for c in p.hand)
            up_preview = " ".join(str(c) for c in p.board_up)
            down_preview = " ".join("X" for _ in p.board_down)
            print(f"{p.name}:")
            print(f"  Hand ({len(p.hand)}): {hand_preview}")
            print(f"  Up   ({len(p.board_up)}): {up_preview}")
            print(f"  Down ({len(p.board_down)}): {down_preview}")
            print(f"  Total cards: {p.total_cards()}")

    # --- autoplay for debugging ---
    def autoplay_game(self):
        names = {1: "A", 11: "J", 12: "Q", 13: "K"}

        print("=== New Game Started (Autoplay) ===")
        print("Players:", [p.name for p in self.players])
        print("First turn:", self.players[self.current_turn].name)

        while True:
            self.print_state()
            player = self.players[self.current_turn]

            if player.total_cards() == 0:
                print(f"\n*** {player.name} WINS the round! ***")
                break

            legal = self.valid_values(player)
            if legal:
                value = max(legal, key=lambda v: -1 if v == "S" else v)
                result = self.play_normal(self.current_turn, value=value)
                print(f"\nTurn: {player.name} (autoplay played {value})")
            else:
                if player.board_down and len(player.board_down) > len(player.board_up):
                    result = self.play_down(self.current_turn)
                    print(f"\nTurn: {player.name} (autoplay flipped down card)")
                else:
                    result = self.force_pickup(self.current_turn, reason="auto-forced")
                    print(f"\nTurn: {player.name} (autoplay forced pickup)")
            print(result)

            for p in self.players:
                if p.total_cards() == 0:
                    print(f"\n*** {p.name} WINS the round! ***")
                    return

    def mixed_game(self):
        num_players = int(input("Enter number of players: "))
        players = []
        manual_flags = []

        for i in range(num_players):
            name = input(f"Enter name for Player {i + 1}: ")
            mode = input("Autoplay this player? (y/n): ").strip().lower()
            players.append(name)
            manual_flags.append(mode != "y")

        game = SwoopGame(players)

        print("=== New Mixed Game Started ===")
        print("Players:", [p.name for p in game.players])
        print("First turn:", game.players[game.current_turn].name)

        names = {1: "A", 11: "J", 12: "Q", 13: "K"}

        while True:
            game.print_state()
            player = game.players[game.current_turn]

            if player.total_cards() == 0:
                print(f"\n*** {player.name} WINS the round! ***")
                break

            if manual_flags[game.current_turn]:
                # Manual
                while True:
                    print(f"\n{player.name}'s turn (manual)")
                    legal = game.valid_values(player)
                    readable = [names.get(v, str(v)) if v != "S" else "S" for v in legal]
                    print("Valid values you can play:", readable)

                    choice = input(
                        "Enter value to play (A/J/Q/K/number or S for swoop, D for down, P for pickup): ").strip().upper()

                    if choice == "D":
                        result = game.play_down(game.current_turn)
                        break
                    elif choice == "P":
                        if player.board_down and len(player.board_down) > len(player.board_up):
                            result = game.play_down(game.current_turn)
                        else:
                            result = game.force_pickup(game.current_turn, reason="manual")
                        break
                    else:
                        mapping = {"A": 1, "J": 11, "Q": 12, "K": 13, "S": "S"}
                        if choice in mapping:
                            value = mapping[choice]
                        else:
                            try:
                                value = int(choice)
                            except ValueError:
                                print("Invalid input.")
                                continue
                        result = game.take_turn(game.current_turn, "play", value)
                        if "error" in result:
                            print("Invalid move:", result["error"])
                            continue
                        break
            else:
                # Autoplay
                print(f"\n{player.name}'s turn (autoplay)")
                legal = game.valid_values(player)
                if legal:
                    value = max(legal, key=lambda v: -1 if v == "S" else v)
                    result = game.play_normal(game.current_turn, value=value)
                    print(f"Autoplay chose {value}")
                else:
                    if not player.hand and not player.board_up and player.board_down:
                        # must flip from down if only downs remain
                        result = game.play_down(game.current_turn)
                        print("Autoplay flipped a down card")
                    else:
                        result = game.force_pickup(game.current_turn, reason="auto-forced")
                        print("Autoplay forced pickup")

            print(result)

            for p in game.players:
                if p.total_cards() == 0:
                    print(f"\n*** {p.name} WINS the round! ***")
                    return
