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
        num_decks = max(1, num_players // 2)
        self.cards = []
        suits = ["hearts", "spades", "diamonds", "clubs"]
        values = list(range(1, 14))  # 1=Ace, 11=Jack, 12=Queen, 13=King
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
        # sort numerically, swoops last
        self.hand.sort(key=lambda c: (c.swoop, c.value if c.value else 99))

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

    def top_value(self):
        if not self.pile:
            return None
        top = self.pile[-1]
        return top.value if not top.swoop else 10

    def valid_values(self, player):
        if not self.pile:
            return sorted(set(c.value for c in player.hand + player.board_up if not c.swoop))
        top = self.top_value()
        return sorted(set(c.value for c in player.hand + player.board_up if not c.swoop and c.value <= top))

    def play_cards(self, player_idx, value=None, swoop=False, use_down=False):
        player = self.players[player_idx]
        legal_values = self.valid_values(player)

        # 1. Swoop attempt
        if swoop:
            if legal_values:
                return {"error": "Swoop not allowed; valid normal cards exist."}

            candidates = [c for c in player.hand + player.board_up if c.swoop or c.value == 10]
            if not candidates:
                return {"error": "No swoop cards in hand."}

            card = candidates[0]
            if card in player.hand:
                player.hand.remove(card)
            else:
                player.board_up.remove(card)

            self.pile = []
            return {"action": "swoop", "played": str(card), "next": player.name}

        # 2. Normal play
        if legal_values and value:
            if value not in legal_values:
                return {"error": f"Value {value} not valid. Valid: {legal_values}"}

            to_play = [c for c in player.hand + player.board_up if c.value == value]
            for c in to_play:
                if c in player.hand:
                    player.hand.remove(c)
                else:
                    player.board_up.remove(c)

            self.pile.extend(to_play)

            if len(self.pile) >= 4:
                last_four = self.pile[-4:]
                if all(not c.swoop and c.value == last_four[0].value for c in last_four):
                    self.pile = []
                    return {"action": "swoop-4ofkind", "played": [str(c) for c in to_play], "next": player.name}

            self.next_turn()
            return {"action": "play", "played": [str(c) for c in to_play], "next": self.players[self.current_turn].name}

        # 3. Try facedown card
        if use_down:
            if not player.board_down:
                # no facedown cards left → must pick up pile
                player.hand.extend(self.pile)
                self.pile = []
                player.sort_hand()
                self.next_turn()
                return {"action": "pickup", "reason": "no-down-cards", "next": self.players[self.current_turn].name}

            card = player.board_down.pop(0)
            print(f"{player.name} flips {card}")

            top = self.top_value()
            if not top or card.swoop or card.value == 10 or (card.value and card.value <= top):
                self.pile.append(card)
                if card.swoop or card.value == 10:
                    self.pile = []
                    return {"action": "swoop-down", "played": str(card), "next": player.name}
                else:
                    self.next_turn()
                    return {"action": "play-down", "played": str(card),
                            "next": self.players[self.current_turn].name}
            else:
                # not playable → must pick up pile + card
                player.hand.extend(self.pile + [card])
                self.pile = []
                player.sort_hand()
                self.next_turn()
                return {"action": "pickup-down", "picked": str(card), "next": self.players[self.current_turn].name}

    def next_turn(self):
        self.current_turn = (self.current_turn + 1) % len(self.players)

    def game_state(self):
        return {
            "turn": self.players[self.current_turn].name,
            "pile": [str(c) for c in self.pile],
            "players": {
                p.name: {
                    "hand": [str(c) for c in p.hand],
                    "up": [str(c) for c in p.board_up],
                    "down": ["X" for _ in p.board_down],
                    "total": p.total_cards(),
                }
                for p in self.players
            },
        }

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

    def autoplay_game(self):
        game = SwoopGame(self.player_names)
        print("=== New Game Started ===")
        print("Players:", [p.name for p in game.players])
        print("First turn:", game.players[game.current_turn].name)
        game_over = False
        while not game_over:
            print(game.print_state())
            player = game.players[game.current_turn]

            if player.total_cards() == 0:
                print(f"\n*** {player.name} WINS the round! ***")
                game_over = True

            legal = game.valid_values(player)
            if legal:
                value = max(legal)
                result = game.play_cards(game.current_turn, value=value)
            else:
                # try swoop, else facedown
                result = game.play_cards(game.current_turn, swoop=True)
                if "error" in result:
                    result = game.play_cards(game.current_turn, use_down=True)

            print(f"\nTurn: {player.name}")
            print(result)
            print("Pile:", [str(c) for c in game.pile])

            for p in game.players:
                if p.total_cards() == 0:
                    print(f"\n*** {p.name} WINS the round! ***")
                    return
