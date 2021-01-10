import os
from dotenv import load_dotenv # .env file
import discord
from discord import client
from discord.ext import commands
import firebase_admin
from firebase_admin import credentials, db # Firebase AJAX wrapper
import datetime

cred = credentials.Certificate('serviceKey.json')  # Store Firebase Credentials
firebase_admin.initialize_app(cred, { # Open connection to FireBase
    'databaseURL' : 'https://scorebot2-14d48-default-rtdb.firebaseio.com/'
})

root = db.reference()

load_dotenv() # Load env variables
TOKEN = os.getenv('DISCORD_TOKEN') # Store token

bot = commands.Bot(command_prefix='/',) # Prefix to use bot is '/'

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command(name='newgame', pass_context=True, help='Adds a new game to the bot database in firebase, and reaverages player scores')
async def new_game(ctx,*,message): # The '*' in args makes the bot pass everything after the command as a string to the def
    ''' The function converts a player list given by the user to a dict, 
        where the key is place: user. 
        If there is a tie, adds array to that score, 
        and each entry in the array is the user id.
        Does not return a value. '''


    if '[' in message:
        message_split = message.split('[') # Message broken at start of each tie

        users = [] # Places list

        for i in message_split:
            if not ']' in i: # If is not a part of a tie
                users.append(i.replace(' ', '')) # Add it to the list
            else: # Is a tie
                curr_users = i.split(']') # Split rest of message into end of tie, and next places
                for j in curr_users: # For each tie/user
                    at_list = j.split(' ') # Get rid of spaces, convert tie into normal list of users
                    while('' in at_list): # Remove empty strings from list
                        at_list.remove('')
                    users.append(at_list)

        for i in range(len(users)): # Loop to make any lists that are just one user into a string
            if isinstance(users[i], list): # Type checker
                if len(users[i]) == 1: #If is a list of one user
                    users[i] = users[i][0]


        users_ready = [user for user in users if user != []] #No empty lists in 3 player matches

        add_users_to_firebase(users_ready) #Make sure all users are in firebase, and users tag exists

        firebase_users = root.get()['users']

        for i in range(len(users)): #Update match count for each user
            if not isinstance(users[i], list):
                curr_user = firebase_users[users[i]]
                field_updates = { "matches": curr_user['matches'] + 1 }
                curr_user.update(field_updates)
                curr_user_pushed = root.child('users').child(users[i]).set(curr_user)
            else: #2 users in a tie
                for user in users[i]:
                    curr_user = firebase_users[user]
                    field_updates = { "matches": curr_user['matches'] + 1 }
                    curr_user.update(field_updates)
                    curr_user_pushed = root.child('users').child(user).set(curr_user)

        scores_dict = {} # Dictionary that holds score to user (user can be tie of many users)

       


        total_players = 0 #Number users in match
        for place in users_ready: 
            if not isinstance(place, list):
                total_players += 1
            else:
                total_players += len(place)

            

        num_tied_before = 0 #amount of ties
        num_ppl_tied = 0 #number of ppl that have tied

        for i in range(len(users_ready)): #For each place
            if not isinstance(users_ready[i], list): #IF the place is not a tie
                score = total_players - i #If no users have tied yet, max point allotment
                if num_ppl_tied > 0: #People have tied, less points as result
                    score -= num_ppl_tied - num_tied_before # Score subtraction
                
                scores_dict[users_ready[i]] = score
            else:
                # score = ((total players - rank + 1) * number ppl tied - (number ppl tied -1)) / (number ppl tied - 1)
                num_tied_before += 1
                num_ppl_tied += len(users_ready[i])
                for j in range(len(users_ready[i])):
                    back_to_normal = 0
                    for player_after in range(1, len(users_ready[i])): 
                        back_to_normal += player_after #Amount of people left

                    score = ((total_players - i) * len(users_ready[i]) - back_to_normal) / (len(users_ready[i]))
                    scores_dict[users_ready[i][j]] = score

        scores_to_firebase_and_average(scores_dict)
    
    else:

        users = message.split(' ') # Places list

        await ctx.message.delete() 

        users_ready = [user for user in users if user != []] #No empty lists in 3 player matches

        add_users_to_firebase(users_ready) #Make sure all users are in firebase, and users tag exists

        scores_dict = {} # Dictionary that holds score to user (user can be tie of many users)

    
        total_players = 0 #Number users in match
        for place in users_ready: 
            if not isinstance(place, list):
                total_players += 1
            else:
                total_players += len(place)

            

        num_tied_before = 0 #amount of ties
        num_ppl_tied = 0 #number of ppl that have tied

        for i in range(len(users_ready)): #For each place
            if not isinstance(users_ready[i], list): #IF the place is not a tie
                score = total_players - i #If no users have tied yet, max point allotment
                if num_ppl_tied > 0: #People have tied, less points as result
                    score -= num_ppl_tied - num_tied_before # Score subtraction
                
                scores_dict[users_ready[i]] = score
            else:
                # score = ((total players - rank + 1) * number ppl tied - (number ppl tied -1)) / (number ppl tied - 1)
                num_tied_before += 1
                num_ppl_tied += len(users_ready[i])
                for j in range(len(users_ready[i])):
                    back_to_normal = 0
                    for player_after in range(1, len(users_ready[i])): 
                        back_to_normal += player_after #Amount of people left

                    score = ((total_players - i) * len(users_ready[i]) - back_to_normal) / (len(users_ready[i]))
                    scores_dict[users_ready[i][j]] = score

        scores_to_firebase_and_average(scores_dict)

        fb_users = []

        firebase_users = root.get()['users'] #Get user fields

        for user in firebase_users:
            fb_users.append({
                "user": user,
                "matches": firebase_users[user]['matches'],
                "score": firebase_users[user]["score"]
            })

        sorted_users = sorted(fb_users, key=lambda k: k['score'])

        sorted_users.reverse()

        new_message = '__***CURRENT STANDINGS***__\n'

        for i in range(len(sorted_users)):
            new_message += f'***{i + 1})***  {sorted_users[i]["user"]} - {sorted_users[i]["score"]}\n'

        channel = await bot.fetch_channel(797657053953785876)

        messages = await channel.history(limit=1000).flatten()
        for x in messages:
            if x.author == bot.user or x.content.startswith('/'):
                await x.delete()

        await channel.send(new_message)

def scores_to_firebase_and_average(scores_dict):

    ''' Function to update user data in firebase by upping match count, and recalculating score '''

    firebase_users = root.get()['users'] #Get user fields
    for user in scores_dict:
        curr_user = firebase_users[user]
        old_score = curr_user['score'] * curr_user['matches']
        add_score = scores_dict[user]
        new_score = (old_score + add_score) / (curr_user['matches'] + 1)

        update_fields = { "score": new_score, "matches": curr_user['matches'] + 1 }

        curr_user.update(update_fields)
        curr_user_pushed = root.child('users').child(user).set(curr_user)

    return


def add_users_to_firebase(users):
    ''' Function to add all users not already in firebase to firebase, does not return a value '''
    if root.get():
        if 'users' in root.get():
            firebase_users = root.get()['users']
            for user in users:
                if not isinstance(user, list):
                    if not user in firebase_users:
                        new_user = root.child('users').child(user).set({
                            'matches': 0,
                            'score': 0, 
                            'first_match' : datetime.datetime.now().strftime("%m/%d/%Y")
                        })
                else:
                    for tie_user in user:
                        new_user = root.child('users').child(tie_user).set({
                            'matches': 0,
                            'score': 0, 
                            'first_match' : datetime.datetime.now().strftime("%m/%d/%Y")
                        })
        else:
            for user in users:
                if not isinstance(user, list):
                        new_user = root.child('users').child(user).set({
                            'matches' : 0,
                            'score': 0, 
                            'first_match' : datetime.datetime.now().strftime("%m/%d/%Y")
                        })
                else:
                    for tie_user in user:
                        new_user = root.child('users').child(tie_user).set({
                            'matches': 0,
                            'score': 0, 
                            'first_match' : datetime.datetime.now().strftime("%m/%d/%Y")
                        })
    else:
        for user in users:
            if not isinstance(user, list):
                    new_user = root.child('users').child(user).set({
                        'matches': 0,
                        'score': 0, 
                        'first_match' : datetime.datetime.now().strftime("%m/%d/%Y")
                    })
            else:
                for tie_user in user:
                    new_user = root.child('users').child(tie_user).set({
                        'matches': 0,
                        'score': 0, 
                        'first_match' : datetime.datetime.now().strftime("%m/%d/%Y")
                    })

    return

bot.run(TOKEN)