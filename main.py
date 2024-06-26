from requests.exceptions import ReadTimeout
from telebot import TeleBot, types
from time import sleep
from conf import *
import sqlite3


# Bot obj
bot = TeleBot(TOKEN)

# Data Base
db = sqlite3.connect("ref.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS refs(
	id INTEGER PRIMARY KEY,
	user_id INTEGER,
	ref_count INTEGER,
	wallet TEXT,
	balance INTEGER
	);""")

db.commit()
cur.close()


# Main menu (Keyboard)
main_menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add("Get link", "Profile")
main_menu.add("Leaderboard")


# Profile menu
prof_menu = types.InlineKeyboardMarkup()

btn_withdraw = types.InlineKeyboardButton("Withdraw coins", callback_data="withdraw")
btn_change = types.InlineKeyboardButton("Change wallet", callback_data="change")

prof_menu.add(btn_withdraw, btn_change)

def withdraw_func(msg):
	try:
		coins = int(msg.text)
	except:
		bot.send_message(msg.chat.id, "Error")
	else:
		cur = db.cursor()
		user = cur.execute(f"SELECT balance, wallet FROM refs WHERE user_id={msg.chat.id}").fetchone()

		tx = f"""ID: {msg.chat.id}
Wallet: {user[1]}
Coins: {coins}
		"""
		if user[0] >= coins:
			cur.execute(f"UPDATE refs SET balance={user[0] - coins} WHERE user_id={msg.chat.id}")
			db.commit()

			bot.send_message(group_id, tx)
			bot.send_message(msg.chat.id, "Request has been sent")
		else:
			bot.send_message(msg.chat.id, "Error, insufficient funds")

		cur.close()

def change_func(msg):
	wallet = msg.text

	cur = db.cursor()

	cur.execute(f"UPDATE refs SET wallet='{wallet}' WHERE user_id={msg.chat.id}")
	db.commit()

	cur.close()

	bot.send_message(msg.chat.id, "Wallet has been changed")

def get_user(user_id):
	cur = db.cursor()
	user = cur.execute(f"SELECT * FROM refs WHERE user_id={user_id}")

	return user.fetchone()


def check_sub(user_id):
	try:
		bot.get_chat_member(channel_id, user_id)
	except:
		bot.send_message(user_id, check_sub_text)

		return False
	else:
		return True


@bot.message_handler(commands=['start'])
def start(msg):
	if channel_id == msg.chat.id:
		return None
	else:	
		args = msg.text.split()
		if len(args) > 1:
			try:
				ref_id = int(args[1])
			except:
				print("Invalid Referral")
			else:
				if check_sub(msg.chat.id):
					user = get_user(ref_id)
					if not(user is None):

						cur = db.cursor()
						us = cur.execute(f"SELECT * FROM refs WHERE user_id={msg.chat.id}").fetchone()

						if us is None:
							cur.execute(f"UPDATE refs SET ref_count={user[2]+1}, balance={user[4] + 100} WHERE user_id={ref_id}")
							db.commit()

						cur.close()
					else:
						print("Not Found Referral")

		bot.send_message(msg.chat.id, start_text, reply_markup=main_menu)


@bot.message_handler(content_types=['text'])
def on_message(msg):
	if channel_id == msg.chat.id or not check_sub(msg.chat.id):
		return None
	else:
		cur = db.cursor()

		user = get_user(msg.chat.id)
		if user is None:
			cur.execute("INSERT INTO refs(user_id, ref_count, wallet, balance) VALUES (?, ?, ?, ?)", (msg.chat.id, 0, "None", 0))
			db.commit()

		if msg.text == "Get link":
			bot.send_message(msg.chat.id, f"https://t.me/notkittycoin_bot/?start={msg.chat.id}")

		elif msg.text == "Profile":
			top = cur.execute("SELECT * FROM refs ORDER BY ref_count desc")
			count = 1
			for i in top:
				if i[1] == msg.chat.id:
					user = i
					break
				count += 1

			profile = f"""Your referrals: {user[2]} 👤

Your NOTKITTY: {user[4]} 🐱

Your place on the leaderboard: {count} 🏅

Your wallet: {user[3]}"""

			bot.send_message(msg.chat.id, profile, reply_markup=prof_menu)

		elif msg.text == "Leaderboard":
			top = cur.execute("SELECT * FROM refs ORDER BY ref_count desc LIMIT 7")
			board = ""

			count = 1
			for user in top:
				board += f"{count}. {bot.get_chat(user[1]).first_name} - {user[2]}\n"
				count += 1

			bot.send_message(msg.chat.id, board)

		cur.close()

@bot.callback_query_handler(func=lambda call: True)
def on_call(call):
	if call.data == "withdraw":
		msg = bot.send_message(call.message.chat.id, "Enter the number of coins:")
		bot.register_next_step_handler(msg, withdraw_func)

	elif call.data == "change":
		msg = bot.send_message(call.message.chat.id, """Connect the wallet address.

Enter your SOL address:""")
		bot.register_next_step_handler(msg, change_func)


bot.infinity_polling(timeout=10, long_polling_timeout=5)
