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
    games = [game.split("\n") for game in log.read().split("\n\n")[:-1]]


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


def parsePlayers(game, rounds):
    players = []
    # There is no clear indicator of where the listing of players ends
    # I use the first round "HOLE CARDS" as a reference to find these indexes
    player_max_i = rounds["HOLE CARDS"] - 3

    player_sb_i = rounds["HOLE CARDS"] - 2
    player_sb_name = game[player_sb_i].split(" ")[0].strip()

    player_bb_i = rounds["HOLE CARDS"] - 1
    player_bb_name = game[player_bb_i].split(" ")[0].strip()

    # Dealer seat is stored in line 2 "gameTableInfo"
    player_dealer_seat = int(game[1].split("Seat #")[1].split(" ")[0].strip()) + 1

    # Starts from index 2 since the first 2 lines are for game&table info
    # Ends before the smallblind line index
    for player_i in range(2, player_sb_i):
        player_data = game[player_i]

        seat = int(player_data.split("Seat ")[1].split(":")[0].strip())
        name = player_data.split(": ")[1].split(" (")[0].strip()
        chips = int(player_data.split(f"{name} (")[1].split(" ")[0].strip())

        is_small_blind = 1 if name == player_sb_name else 0
        is_big_blind = 1 if name == player_bb_name else 0
        is_dealer = 1 if seat == player_dealer_seat else 0

        players.append(
            {
                "seat": seat,
                "name": name,
                "startingChips": chips,
                "roles": {
                    "smallblind": is_small_blind,
                    "bigblind": is_big_blind,
                    "dealer": is_dealer,
                },
            }
        )

    return players


def parseGame(game):
    # Each round of the game is seperated by '*** {round-name} ***'
    # This gives a list of the rounds back with the corresponding index
    rounds = findRounds(game)

    # ex.:
    # Seat 3: quaq_ (5000 in chips)
    # Seat 4: The_Destroyers (5000 in chips)
    # Seat 5: _jake Gggtd_ (20800 in chips)
    # Seat 6: Viovyx (3750 in chips)
    # Seat 8: Eon.Sanders (78750 in chips)
    players = parsePlayers(
        game, rounds
    )  # Rounds is needed to determine indexes (explained more inside function)

    # ex. PokerStars Hand: Hold'em No Limit (25/50) - 2025/12/24 15:56:45 UTC
    raw_type_info = game[0]
    game_info = parseGameInfo(raw_type_info)

    # ex. Table 'BigFoot79's Cash Game' 8-max (Play Money) Seat #4 is the button
    raw_table_info = game[1]
    table_info = parseTableInfo(raw_table_info)

    return {
        "rounds": rounds,
        "gameInfo": game_info,
        "tableInfo": table_info,
        "players": players,
    }


game = games[200]
with open("match.json", "w") as f:
    f.write(json.dumps(parseGame(game), indent=4))
