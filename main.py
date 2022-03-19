import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id
import time
import tokens
from tokens import main_token, stl_token, qiwi_secret_token
import messages
import operator
import random
import sqlite3
from threading import Thread
from datetime import datetime
from itertools import islice
from pyqiwip2p import QiwiP2P

#region keyboards
main_keyboard = VkKeyboard(one_time=True)
main_keyboard.add_button("Проверить пользователя", color=VkKeyboardColor.PRIMARY)
main_keyboard.add_line()
main_keyboard.add_button("Установить слежку", color=VkKeyboardColor.PRIMARY)
main_keyboard.add_line()
main_keyboard.add_button("Купить 🔑", color=VkKeyboardColor.POSITIVE)
main_keyboard.add_line()
main_keyboard.add_button("Что бот умеет?", color=VkKeyboardColor.SECONDARY)

back_keyboard = VkKeyboard(one_time=True)
back_keyboard.add_button("Назад", color=VkKeyboardColor.SECONDARY)

payment_keyboard = VkKeyboard(inline=True)
payment_keyboard.add_button("1x 🔑", color=VkKeyboardColor.PRIMARY)
payment_keyboard.add_button("3x 🔑", color=VkKeyboardColor.PRIMARY)
payment_keyboard.add_button("6x 🔑", color=VkKeyboardColor.PRIMARY)
payment_keyboard.add_line()
payment_keyboard.add_button("10x 🔑", color=VkKeyboardColor.PRIMARY)

check_payment_keyboard = VkKeyboard(inline=True)
check_payment_keyboard.add_button("Проверить оплату", color=VkKeyboardColor.POSITIVE)
check_payment_keyboard.add_line()
check_payment_keyboard.add_button("Назад", color=VkKeyboardColor.SECONDARY)

balance_keyboard = VkKeyboard(inline=True)
balance_keyboard.add_button("Купить 🔑", color=VkKeyboardColor.POSITIVE)
balance_keyboard.add_line()
balance_keyboard.add_button("Назад", color=VkKeyboardColor.SECONDARY)
#endregion
#region vk connection
vk_session = vk_api.VkApi(token=main_token)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)
#endregion
#region sqlite connection
connection = sqlite3.connect("users.db")
cursor = connection.cursor()

#endregion
#region qiwi connection
p2p = QiwiP2P(auth_key=qiwi_secret_token)
#endregion

def stl_session():
    stl_token[0] += 1
    if stl_token[0] >= len(stl_token):
        stl_token[0] = 1

    return vk_api.VkApi(token=stl_token[stl_token[0]])

def get_workflag(user_id):
    cursor.execute("SELECT workflag FROM users WHERE userid=?", (user_id,))
    workflag = cursor.fetchall()
    if not workflag:
        cursor.execute("INSERT INTO users(userid,balance,workflag) VALUES(?,?,?)", (user_id, 0, 0,))
        connection.commit()
        return 0
    else:
        return workflag[0][0]

def set_workflag(user_id, flag):
    temp = get_workflag(user_id)
    cursor.execute("SELECT * FROM users WHERE userid=?", (user_id,))
    workflag = cursor.fetchall()
    print(workflag)

    sql = "UPDATE users SET workflag=? WHERE userid=?"
    val = (str(flag), str(user_id),)
    print("VAL IS ", val)
    cursor.execute(sql, val)
    connection.commit()

    cursor.execute("SELECT * FROM users WHERE userid=?", (user_id,))
    workflag = cursor.fetchall()
    print(workflag)

def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE userid=?", (user_id,))
    workflag = cursor.fetchall()
    if not workflag:
        cursor.execute("INSERT INTO users(userid,balance,workflag) VALUES(?,?,?)", (user_id, 0, 0,))
        connection.commit()
        return 0
    else:
        return workflag[0][0]

def is_enough_keys(user_id):
    cursor.execute("SELECT balance FROM users WHERE userid=?", (user_id,))
    balance = cursor.fetchall()
    print(balance)
    if balance[0][0] < 1:
        vk.messages.send(user_id=user_id, random_id=get_random_id(),
                         message=messages.message_insufficient_funds, keyboard=balance_keyboard.get_keyboard())
        return False
    else:
        return True

def decrement_balance(user_id):
    cursor.execute("UPDATE users SET balance = balance - 1 WHERE userid = ?", (str(user_id),))
    connection.commit()

def add_payment(user_id, bill_id, keys):
    cursor.execute("INSERT INTO payments(userid, billid, keys) VALUES(?,?,?)", (user_id, bill_id, keys,))
    connection.commit()

#region check for banned tokens
for token in stl_token[1::]:
    print("TOKEN ", token, " : ")
    res = stl_session().method("friends.get", {"user_id": "253605549"})
#endregion

flag = "MADE BY POLICELETTUCE 15.02.2022"
busy_users = []

def check(raw_link, current_event):
    if current_event.user_id in busy_users:
        vk.messages.send(user_id=current_event.user_id, random_id=get_random_id(),
                         message=messages.message_wait_for_check, keyboard=back_keyboard.get_keyboard())
        return
    else:
        busy_users.append(current_event.user_id)
        parts = raw_link.split("/")
        user_sex = 0
        try:
            temp = vk_session.method("users.get", {"user_id": parts[-1], "fields": "sex"})[0]
            user_id = temp.get("id")
            user_sex = temp.get("sex")
            user_name = temp.get("first_name") + " " + temp.get("last_name")
        except Exception as exc:
            busy_users.remove(current_event.user_id)
            vk.messages.send(user_id=current_event.user_id, random_id=get_random_id(),
                             message=messages.message_error_user_search,
                             keyboard=back_keyboard.get_keyboard())
            print("USERS.GET ERROR! ", exc)
            return

        try:
            temp = stl_session().method("friends.get", {"user_id": user_id, "order": "random", "count": 500})
            friends_list = temp.get("items")
            friends_count = temp.get("count")
        except Exception as exc:
            busy_users.remove(current_event.user_id)
            vk.messages.send(user_id=current_event.user_id, random_id=get_random_id(),
                             message=messages.message_error_user_private,
                             keyboard=main_keyboard.get_keyboard())
            print("FRIENDS.GET ERROR! ", exc)
            return

        vk.messages.send(user_id=current_event.user_id, random_id=get_random_id(),
                         message=messages.message_check_in_progress)
        decrement_balance(event.user_id)        #ПИЗДИМ денЬГИ У АБОненТА
        times_user_liked = {}
        no_mutual_friends = []

        for friend_id in friends_list:
            try:
                times_user_liked[friend_id] = 0
                need_to_check = False
                if user_sex != 0:
                    sex = vk_session.method("users.get", {"user_id": friend_id, "fields": "sex"})[0].get("sex")
                    if sex != user_sex:
                        need_to_check = True

                else:
                    need_to_check = True

                if need_to_check:
                    mutual = stl_session().method("friends.getMutual", {"source_uid": user_id, "target_uids": friend_id})[0].get("common_count")
                    print("CHECKING MUTUAL BETWEEN ", user_id, " AND ", friend_id)
                    print("AMT OF MUTUALS: ", mutual)
                    if mutual == 0:
                        no_mutual_friends.append(friend_id)
                        print("APPENDED!")

                    photos = stl_session().method("photos.get", {"user_id": friend_id, "album_id": "profile"}).get("items")
                    photos += stl_session().method("photos.get", {"user_id": friend_id, "album_id": "wall"}).get("items")

                    for photo in photos:
                        is_liked = stl_session().method("likes.isLiked", {"user_id": user_id, "type": "photo",
                                                        "owner_id": friend_id, "item_id": photo.get("id")}).get("liked")
                        if (is_liked):
                            times_user_liked[friend_id] += 1
                            print("FOUND LIKED PHOTO! TOTAL LIKES BY USER: ", times_user_liked[friend_id])

            except Exception:
                continue

    times_user_liked = sorted(times_user_liked.items(), key=operator.itemgetter(1))
    times_user_liked.reverse()
    random.shuffle(no_mutual_friends)
    print("LIKES: ", times_user_liked)
    print(no_mutual_friends)

    #region message formatting
    message_name = "👤" + user_name + "\n\n"
    temp = vk_session.method("users.get", {"user_id": parts[-1], "fields": "last_seen"})[0]
    user_last_seen = temp.get("last_seen").get("time")
    message_last_seen = "🕔Был(а) в сети: " + datetime.fromtimestamp(user_last_seen).strftime("%d.%m.%Y, %H:%M") + "\n"
    message_friends_amt = "👫Друзей: " + str(friends_count) + "\n\n"

    message_liked = "❤Больше всего лайкает:\n"
    ctr = 1
    for key in islice(times_user_liked, 5):
        temp = stl_session().method("users.get", {"user_id": key[0]})[0]
        name = temp.get("first_name") + " " + temp.get("last_name")
        message_liked += str(ctr) + ") [id" + str(key[0]) + "|" + str(name) + "]: " + str(key[1]) + "\n"
        ctr += 1
    message_liked += "\n"

    message_no_mutuals = "🤔Нет общих друзей с:\n"
    ctr = 1
    for id in no_mutual_friends[:5]:
        temp = stl_session().method("users.get", {"user_id": id})[0]
        name = temp.get("first_name") + " " + temp.get("last_name")
        message_no_mutuals += str(ctr) + ") [id" + str(id) + "|" + str(name) + "]\n"
        ctr += 1
    message_no_mutuals += "\n"

    message_most_wanted = "🤭Самый подозрительный человек:\n"
    for key in islice(times_user_liked, 1):
        temp = stl_session().method("users.get", {"user_id": key[0]})[0]
        name = temp.get("first_name") + " " + temp.get("last_name")
        message_most_wanted += "[id" + str(key[0]) + "|" + str(name) + "]" + "\n"

    message_check = message_name + message_last_seen + message_friends_amt + message_liked + message_no_mutuals + message_most_wanted
    #endregion
    busy_users.remove(current_event.user_id)
    vk.messages.send(user_id=current_event.user_id, random_id=get_random_id(),
                     message=message_check, keyboard=back_keyboard.get_keyboard())

for event in longpoll.listen():         #workflags: 0 = free, 1 = check, 2 = spy
    if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text and event.from_user:
        text = event.text
        if (text == "Начать" or text == "Назад"):
            set_workflag(event.user_id, 0)
            vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                             message=messages.message_choose, keyboard=main_keyboard.get_keyboard())

        elif (text == "Что бот умеет?"):
            set_workflag(event.user_id, 0)
            vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                             message=messages.message_bot_func, keyboard=main_keyboard.get_keyboard())

        elif (text == "Установить слежку"):
            set_workflag(event.user_id, 2)
            vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                             message=messages.message_spy_first_link, keyboard=back_keyboard.get_keyboard())

        elif (text == "Проверить оплату"):
            cursor.execute("SELECT * FROM payments WHERE userid=?", (str(event.user_id),))
            payments = cursor.fetchall()
            is_paid = False
            for payment in payments:
                if str(p2p.check(bill_id=payment[1]).status) == "PAID":
                    is_paid = True
                    user_id = payment[0]
                    keys = payment[2]
                    print("PAYMENT[1] IS " + payment[1])
                    cursor.execute("UPDATE users SET balance = balance + ? WHERE userid = ?", (str(keys), str(user_id),))
                    cursor.execute("DELETE FROM payments WHERE billid = ?", (str(payment[1]),))
                elif (str(p2p.check(bill_id=payment[1]).status) == "REJECTED") or (str(p2p.check(bill_id=payment[1]).status) == "EXPIRED"):
                    cursor.execute("DELETE FROM payments WHERE billid = ?", (str(payment[1]),))
                connection.commit()

            if is_paid:
                msg = messages.message_payment_successful + str(get_balance(event.user_id))
                vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                 message=msg, keyboard=main_keyboard.get_keyboard())
            else:
                vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                 message=messages.message_payment_failed, keyboard=main_keyboard.get_keyboard())

        elif (text == "Купить 🔑"):
            msg_balance = "Ваш текущий баланс: " + str(get_balance(event.user_id)) + "🔑"
            vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                             message=messages.message_pricelist, keyboard=payment_keyboard.get_keyboard())
            vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                             message=msg_balance, keyboard=main_keyboard.get_keyboard())

        elif (text == "1x 🔑"):
            comment = str(event.user_id) + "_" + str(random.randint(100000, 999999))
            bill = p2p.bill(amount=5, lifetime=2, comment=comment)
            msg = messages.message_payment + bill.pay_url
            add_payment(event.user_id, bill.bill_id, 1)
            vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                             message=msg, keyboard=check_payment_keyboard.get_keyboard())

        elif (text == "Проверить пользователя"):
            set_workflag(event.user_id, 1)
            vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                             message=messages.message_check_link, keyboard=back_keyboard.get_keyboard())

        else:
            get_workflag(event.user_id)
            if (get_workflag(event.user_id) == 1):
                if is_enough_keys(event.user_id):
                    Thread(target=check, args=(text, event,)).start()
            elif (get_workflag(event.user_id) == 2):
                temp = 1
            else:
                vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                 message="сначала выбери функцию", keyboard=main_keyboard.get_keyboard())

