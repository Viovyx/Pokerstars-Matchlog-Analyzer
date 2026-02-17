import os
import json
from datetime import datetime
from dotenv import load_dotenv


load_dotenv()
# Must have an .env in same dir with var LOG that has a string with the MatchLog.txt you want to analyze
# Example for default location in steam:
# LOG="C:\...\SteamLibrary\steamapps\common\PokerStars VR\PokerStarsVR_Data\StreamingAssets\MatchLog.txt"
logfile = os.getenv("LOG")

# Convert file into array of games
# Each game is an array of itself for each line
with open(logfile, "r") as log:
    games = [game.strip().split("\n") for game in log.read().split("\n\n")[:-1]]


def findRounds(game):
    rounds = {}
    for i in range(len(game)):
        # Check if a line starts with the round marker (***)
        # If so then it strips the round name from that line with its index
        if game[i][:3] == "***":
            name = game[i].split("***")[1].strip()
            rounds[name] = i

    return rounds


def parseGameInfo(gameTypeInfo):
    # Various splits and strips to extract the needed info from the gameTypeInfo line
    game_type = gameTypeInfo.split("PokerStars Hand: ")[1].split(" (")[0].strip()
    stake_sb = int(gameTypeInfo.split(f"{game_type} (")[1].split("/")[0].strip())
    stake_bb = int(
        gameTypeInfo.split(f"{game_type} ({stake_sb}/")[1].split(")")[0].strip()
    )

    # Stakes are stored in a list to allow for custom manipulation in other programs
    stakes = [stake_sb, stake_bb]

    # The starttime of a game is stored as a rounded timestamp
    datetime_s = gameTypeInfo.split(" - ")[1].strip()
    game_datetime = int(
        round(datetime.strptime(datetime_s, "%Y/%m/%d %H:%M:%S %Z").timestamp())
    )

    return {"gameType": game_type, "gameStakes": stakes, "gameDateTime": game_datetime}


def parseTableInfo(gameTableInfo):
    # Various splits and strips to extract the needed info from the gameTableInfo line
    table_name = gameTableInfo.split("Table '")[1].split("' ")[0].strip()
    table_max_players = int(
        gameTableInfo.split(f"{table_name}' ")[1].split("-max")[0].strip()
    )

    return {"tableName": table_name, "tableMaxPlayers": table_max_players}


def parseCards(card_string, new_card=""):
    cards_str = card_string.strip("[]").split(" ")

    if new_card != "":
        cards_str.append(new_card.strip("[]"))

    cards = []
    for card in cards_str:
        match card[0]:
            case "t":
                number = 10
            case "j":
                number = 11
            case "q":
                number = 12
            case "k":
                number = 13
            case _:
                number = int(card[0])

        match card[1]:
            case "c":
                suite = "clubs"
            case "s":
                suite = "spades"
            case "h":
                suite = "hearts"
            case "d":
                suite = "diamonds"
        cards.append({"suite": suite, "number": number})

    return cards


def parsePlayers(game, rounds):
    players = []
    # There is no clear indicator of where the listing of players ends
    # I use the first round "HOLE CARDS" as a reference to find these indexes
    player_max_i = rounds["HOLE CARDS"] - 3
    player_sb_i = rounds["HOLE CARDS"] - 2

    # Player who the logs are from (shows card info)
    active_player_name = (
        game[rounds["HOLE CARDS"] + 1].split("Dealt to ")[1].split(" [")[0]
    )
    active_player_cards = parseCards(
        game[rounds["HOLE CARDS"] + 1].split(f"Dealt to {active_player_name} ")[1]
    )

    # Starts from index 2 since the first 2 lines are for game&table info
    # Ends before the smallblind line index
    for player_i in range(2, player_sb_i):
        player_data = game[player_i]

        seat = int(player_data.split("Seat ")[1].split(":")[0].strip())
        name = player_data.split(": ")[1].split(" (")[0].strip()
        chips = int(player_data.split(f"{name} (")[1].split(" ")[0].strip())

        if active_player_name != name:
            player = {
                "seat": seat,
                "name": name,
                "startingChips": chips,
            }
        else:
            player = {
                "seat": seat,
                "name": name,
                "startingChips": chips,
                "cards": active_player_cards,
            }

        players.append(player)

    return players


def parseRoles(game, rounds, players):
    sb_i = rounds["HOLE CARDS"] - 2
    sb_name = game[sb_i].split(" posts")[0].strip()
    sb_seat = [player["seat"] for player in players if player["name"] == sb_name][0]

    bb_i = rounds["HOLE CARDS"] - 1
    bb_name = game[bb_i].split(" posts")[0].strip()
    bb_seat = [player["seat"] for player in players if player["name"] == bb_name][0]

    # Dealer seat is stored in line 2 "gameTableInfo"
    dealer_seat = int(game[1].split("Seat #")[1].split(" ")[0].strip()) + 1

    return {
        "dealerSeat": dealer_seat,
        "smallblindSeat": sb_seat,
        "bigblindSeat": bb_seat,
    }


def parseRounds(game, game_info, rounds, roles, players):
    round_names = list(rounds.keys())
    for current_round in round_names:
        current_round_i = round_names.index(current_round, 0, len(round_names))
        next_round = round_names[
            current_round_i + (1 if current_round_i != len(round_names) - 1 else 0)
        ]

        start_i = rounds[current_round] + 1
        end_i = rounds[next_round] if next_round != current_round else len(game)

        # TODO: Parse actions for each round

        # Debug prints:
        print(current_round)
        for i in range(start_i, end_i):
            print(game[i])
        print("\n")


def parseGame(game):
    # Each round of the game is seperated by '*** {round-name} ***'
    # This gives a list of the rounds back with the corresponding index
    rounds_i = findRounds(game)

    # ex.:
    # Seat 3: quaq_ (5000 in chips)
    # Seat 4: The_Destroyers (5000 in chips)
    # Seat 5: _jake Gggtd_ (20800 in chips)
    # Seat 6: Viovyx (3750 in chips)
    # Seat 8: Eon.Sanders (78750 in chips)
    players = parsePlayers(
        game, rounds_i
    )  # Rounds is needed to determine indexes (explained more inside function)

    roles = parseRoles(game, rounds_i, players)

    # ex. PokerStars Hand: Hold'em No Limit (25/50) - 2025/12/24 15:56:45 UTC
    raw_type_info = game[0]
    game_info = parseGameInfo(raw_type_info)

    # ex. Table 'BigFoot79's Cash Game' 8-max (Play Money) Seat #4 is the button
    raw_table_info = game[1]
    table_info = parseTableInfo(raw_table_info)

    rounds = parseRounds(game, game_info, rounds_i, roles, players)

    return {
        "rounds": rounds_i,
        "gameInfo": game_info,
        "tableInfo": table_info,
        "roles": roles,
        "players": players,
        "playthrough": rounds,
    }


game = games[149]
with open("match.json", "w") as f:
    f.write(json.dumps(parseGame(game), indent=4))
