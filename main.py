import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id
from tokens import main_token, stl_token, qiwi_secret_token
from pricing import x1_key_price, x3_key_price, x6_key_price, x10_key_price
import time
import os
import messages
import operator
import random
import sqlite3
from threading import Thread
from datetime import datetime, timedelta
from itertools import islice
from pyqiwip2p import QiwiP2P

print(time.strftime('%Y-%m-%d %H:%M:%S'))
os.environ['TZ'] = 'Europe/Moscow'
time.tzset()
print(time.strftime('%Y-%m-%d %H:%M:%S'))

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

spy_keyboard = VkKeyboard(inline=True)
spy_keyboard.add_button("1 день", color=VkKeyboardColor.PRIMARY)
spy_keyboard.add_button("3 дня", color=VkKeyboardColor.PRIMARY)
spy_keyboard.add_button("7 дней", color=VkKeyboardColor.PRIMARY)
spy_keyboard.add_line()
spy_keyboard.add_button("Назад", color=VkKeyboardColor.SECONDARY)
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

    sql = "UPDATE users SET workflag=? WHERE userid=?"
    val = (str(flag), str(user_id),)
    cursor.execute(sql, val)
    connection.commit()

    cursor.execute("SELECT * FROM users WHERE userid=?", (user_id,))
    workflag = cursor.fetchall()

def set_spy_price(user_id, price):
    cursor.execute("SELECT * FROM spying WHERE send_to=?", (user_id,))
    row = cursor.fetchall()
    if not row:
        cursor.execute("INSERT INTO spying(id1,id2,send_to,expires,price) VALUES(?,?,?,?,?)", (0, 0, str(user_id), 0, str(price)))
        connection.commit()
    else:
        cursor.execute("UPDATE spying SET price = ? where send_to = ?", (str(price), str(user_id),))
        connection.commit()

def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE userid=?", (user_id,))
    workflag = cursor.fetchall()
    if not workflag:
        cursor.execute("INSERT INTO users(userid,balance,workflag) VALUES(?,?,?)", (user_id, 0, 0,))
        connection.commit()
        return 0
    else:
        return workflag[0][0]

def buy_keys(cash_amount, keys_amount, user_id):
    comment = str(event.user_id) + "_" + str(random.randint(1000, 9999))
    bill = p2p.bill(amount=cash_amount, lifetime=15, comment=comment)
    msg = messages.message_payment + bill.pay_url
    add_payment(event.user_id, bill.bill_id, keys_amount)
    try:
        vk.messages.send(user_id=user_id, random_id=get_random_id(),
                         message=msg, keyboard=check_payment_keyboard.get_keyboard())
    except Exception as msgexc:
        print(msgexc)
        pass

def is_enough_keys(user_id):
    cursor.execute("SELECT balance FROM users WHERE userid=?", (user_id,))
    balance = cursor.fetchall()
    if balance[0][0] < 1:
        return False
    else:
        return True

def decrement_balance(user_id):
    cursor.execute("UPDATE users SET balance = balance - 1 WHERE userid = ?", (str(user_id),))
    connection.commit()

def decrement_balance_by_amt(user_id, amt):
    cursor.execute("UPDATE users SET balance = balance - ? WHERE userid = ?", (amt, str(user_id),))
    connection.commit()

def add_payment(user_id, bill_id, keys):
    cursor.execute("INSERT INTO payments(userid, billid, keys) VALUES(?,?,?)", (user_id, bill_id, keys,))
    connection.commit()

def check_payment(user_id):
    cursor.execute("SELECT * FROM payments WHERE userid=?", (str(user_id),))
    payments = cursor.fetchall()
    is_paid = False
    for payment in payments:
        if str(p2p.check(bill_id=payment[1]).status) == "PAID":
            is_paid = True
            user_id = payment[0]
            keys = payment[2]
            cursor.execute("UPDATE users SET balance = balance + ? WHERE userid = ?", (str(keys), str(user_id),))
            cursor.execute("DELETE FROM payments WHERE billid = ?", (str(payment[1]),))
        elif (str(p2p.check(bill_id=payment[1]).status) == "REJECTED") or (
                str(p2p.check(bill_id=payment[1]).status) == "EXPIRED"):
            cursor.execute("DELETE FROM payments WHERE billid = ?", (str(payment[1]),))
        connection.commit()
    if is_paid:
        return True
    else:
        return False

def send_closed_check_message(user_id, text):
    parts = text.split("/")
    try:
        temp = stl_session().method("users.get", {"user_id": parts[-1], "fields": "last_seen", "lang": "0"})[0]
        user_id = temp.get("id")
        user_name = temp.get("first_name") + " " + temp.get("last_name")
        if temp.get("last_seen") is None:
            user_last_seen = None
        else:
            user_last_seen = temp.get("last_seen").get("time")
    except Exception as exc:
        try:
            vk.messages.send(user_id=user_id, random_id=get_random_id(),
                             message=messages.message_error_user_search,
                             keyboard=back_keyboard.get_keyboard())
        except Exception as msgexc:
            print(msgexc)
            pass
        if (str(exc).split(" ")[0] == "[5]"):
            print("CAUGHT EXCEPTION: ", exc)
            remove_last_token()
        return

    try:
        temp = stl_session().method("friends.get",
                                    {"user_id": user_id, "order": "random", "count": 500, "lang": "0"})
        friends_count = temp.get("count")
    except Exception as exc:
        try:
            vk.messages.send(user_id=user_id, random_id=get_random_id(),
                             message=messages.message_error_user_private,
                             keyboard=main_keyboard.get_keyboard())
        except Exception as msgexc:
            print(msgexc)
            pass
        if (str(exc).split(" ")[0] == "[5]"):
            print("CAUGHT EXCEPTION: ", exc)
            remove_last_token()
        return
    #region message formatting
    message_name = "👤" + user_name + "\n\n"
    if user_last_seen is not None:
        message_last_seen = "🕔Был(а) в сети: " + datetime.fromtimestamp(user_last_seen).strftime(
        "%d.%m.%Y, %H:%M") + "\n"
    else:
        message_last_seen = ""
    message_friends_amt = "👫Друзей: " + str(friends_count) + "\n\n"
    message_liked = "❤Больше всего лайкает: 🔒\n"
    message_no_mutuals = "🤔Нет общих друзей с: 🔒\n"
    message_most_wanted = "🤭Самый подозрительный человек: 🔒\n\n"
    message_fin = "Узнать данные за 🔒 вы можете всего за один 🔑 ключ!\n\nВаш баланс: 0 🔑"
    message_check = message_name + message_last_seen + message_friends_amt + message_liked + message_no_mutuals + message_most_wanted + message_fin
    #endregion
    try:
        vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                         message=message_check,
                         keyboard=balance_keyboard.get_keyboard())
    except Exception as msgexc:
        print(msgexc)
        pass

def remove_last_token():
    print("REMOVED BAD TOKEN: ", stl_token[stl_token[0]])
    stl_token.remove(stl_token[stl_token[0]])
    stl_token[0] -= 1

def check_for_banned_tokens():
    ctr = 0
    for token in stl_token[1::]:
        try:
            res = stl_session().method("friends.get", {"user_id": "253605549", "lang": "0"})
        except vk_api.ApiError as exc:
            print("CAUGHT EXCEPTION: ", exc)
            if (str(exc).split(" ")[0] == "[5]"):
                ctr += 1
                remove_last_token()
    print("Total bad tokens: ", ctr)


check_for_banned_tokens()
flag = "MADE BY POLICELETTUCE 15.02.2022"
busy_users = []
pending_spy = []

def check(current_event, friends_list, user_sex, user_id, friends_count, parts, user_name):
    print("STARTED CHECK OF: ", user_id, " REQUESTER: ", current_event.user_id)
    times_user_liked = {}
    no_mutual_friends = []

    for friend_id in friends_list:
        try:
            times_user_liked[friend_id] = 0
            need_to_check = False
            if user_sex != 0:
                sex = 1337
                try:
                    sex = stl_session().method("users.get", {"user_id": friend_id, "fields": "sex", "lang": "0"})[0].get("sex")
                except vk_api.ApiError as exc:
                    if (str(exc).split(" ")[0] == "[5]"):
                        print("CAUGHT EXCEPTION: ", exc)
                        remove_last_token()
                if sex != user_sex:
                    need_to_check = True

            else:
                need_to_check = True

            if need_to_check:
                mutual = stl_session().method("friends.getMutual", {"source_uid": user_id, "target_uids": friend_id, "lang": "0"})[0].get("common_count")
                if mutual == 0:
                    no_mutual_friends.append(friend_id)

                photos = stl_session().method("photos.get", {"user_id": friend_id, "album_id": "profile", "lang": "0"}).get("items")
                photos += stl_session().method("photos.get", {"user_id": friend_id, "album_id": "wall", "lang": "0"}).get("items")

                for photo in photos:
                    try:
                        is_liked = stl_session().method("likes.isLiked", {"user_id": user_id, "type": "photo",
                                                        "owner_id": friend_id, "item_id": photo.get("id"), "lang": "0"}).get("liked")
                        if (is_liked):
                            times_user_liked[friend_id] += 1
                    except vk_api.ApiError as exc:
                        if (str(exc).split(" ")[0] == "[5]"):
                            print("CAUGHT EXCEPTION: ", exc)
                            remove_last_token()

        except vk_api.ApiError as exc:
            if (str(exc).split(" ")[0] == "[5]"):
                print("CAUGHT EXCEPTION: ", exc)
                remove_last_token()
            continue

    times_user_liked = sorted(times_user_liked.items(), key=operator.itemgetter(1))
    times_user_liked.reverse()
    random.shuffle(no_mutual_friends)

    #region message formatting
    message_name = ""
    message_last_seen = ""
    message_friends_amt = ""
    try:
        message_name = "👤" + user_name + "\n\n"
        temp = stl_session().method("users.get", {"user_id": parts[-1], "fields": "last_seen", "lang": "0"})[0]
        if temp.get("last_seen") is None:
            user_last_seen = None
            message_last_seen = ""
        else:
            user_last_seen = temp.get("last_seen").get("time")
            message_last_seen = "🕔Был(а) в сети: " + datetime.fromtimestamp(user_last_seen).strftime("%d.%m.%Y, %H:%M") + "\n"
        message_friends_amt = "👫Друзей: " + str(friends_count) + "\n\n"
    except vk_api.ApiError as exc:
        if (str(exc).split(" ")[0] == "[5]"):
            print("CAUGHT EXCEPTION: ", exc)
            remove_last_token()

    message_liked = "❤Больше всего лайкает:\n"
    ctr = 1
    for key in islice(times_user_liked, 5):
        try:
            temp = stl_session().method("users.get", {"user_id": key[0], "lang": "0"})[0]
            name = temp.get("first_name") + " " + temp.get("last_name")
            message_liked += str(ctr) + ") [id" + str(key[0]) + "|" + str(name) + "]: " + str(key[1]) + "\n"
            ctr += 1
        except vk_api.ApiError as exc:
            if (str(exc).split(" ")[0] == "[5]"):
                print("CAUGHT EXCEPTION: ", exc)
                remove_last_token()
            continue
    message_liked += "\n"

    message_no_mutuals = "🤔Нет общих друзей с:\n"
    ctr = 1
    for id in no_mutual_friends[:5]:
        try:
            temp = stl_session().method("users.get", {"user_id": id, "lang": "0"})[0]
            name = temp.get("first_name") + " " + temp.get("last_name")
            message_no_mutuals += str(ctr) + ") [id" + str(id) + "|" + str(name) + "]\n"
            ctr += 1
        except vk_api.ApiError as exc:
            if (str(exc).split(" ")[0] == "[5]"):
                print("CAUGHT EXCEPTION: ", exc)
                remove_last_token()
            continue
    message_no_mutuals += "\n"

    message_most_wanted = "🤭Самый подозрительный человек:\n"
    for key in islice(times_user_liked, 1):
        try:
            temp = stl_session().method("users.get", {"user_id": key[0], "lang": "0"})[0]
            name = temp.get("first_name") + " " + temp.get("last_name")
            message_most_wanted += "[id" + str(key[0]) + "|" + str(name) + "]" + "\n"
        except vk_api.ApiError as exc:
            if (str(exc).split(" ")[0] == "[5]"):
                print("CAUGHT EXCEPTION: ", exc)
                remove_last_token()
            continue

    message_check = message_name + message_last_seen + message_friends_amt + message_liked + message_no_mutuals + message_most_wanted
    #endregion
    busy_users.remove(current_event.user_id)
    try:
        vk.messages.send(user_id=current_event.user_id, random_id=get_random_id(),
                         message=message_check, keyboard=main_keyboard.get_keyboard())
    except Exception as msgexc:
        print(msgexc)
        pass


def send_spy_message(id, current_flag, sendto):
    user = stl_session().method("users.get", {"user_id": id, "fields": "online, last_seen", "lang": "0"})[0]
    user_name = user.get("first_name") + " " + user.get("last_name")
    user_flag = user.get("online")
    if user.get("last_seen") is None:
        user_last_seen = datetime.now().timestamp()
    else:
        user_last_seen = user.get("last_seen").get("time")
    if current_flag != user_flag:
        if user_flag == 0:
            msg = datetime.fromtimestamp(user_last_seen).strftime("%H:%M") + " " + user_name + " вышел(а) из VK!"
            try:
                vk.messages.send(user_id=sendto, random_id=get_random_id(),
                                 message=msg, keyboard=main_keyboard.get_keyboard())
            except Exception as msgexc:
                print(msgexc)
                pass
            return user_flag
        else:
            msg = datetime.fromtimestamp(user_last_seen).strftime("%H:%M") + " " + user_name + " онлайн!"
            try:
                vk.messages.send(user_id=sendto, random_id=get_random_id(),
                                 message=msg, keyboard=main_keyboard.get_keyboard())
            except Exception as msgexc:
                print(msgexc)
                pass
            return user_flag
    else:
        return user_flag

def spy():
    spy_connection = sqlite3.connect("spy.db")
    spy_cursor = spy_connection.cursor()
    while True:
        while len(pending_spy) > 0:
            row = pending_spy.pop()
            id1_flag = send_spy_message(row[0], 2, row[2])
            id2_flag = send_spy_message(row[1], 2, row[2])
            spy_cursor.execute("INSERT INTO spy(id1,id1_flag,id2,id2_flag,sendto,expires) VALUES(?,?,?,?,?,?)", (row[0], str(id1_flag), row[1], str(id2_flag), row[2], row[3]))
            spy_connection.commit()

        spy_cursor.execute("SELECT * FROM spy")
        rows = spy_cursor.fetchall()
        for row in rows:
            id1_flag = send_spy_message(row[0], row[1], row[4])
            id2_flag = send_spy_message(row[2], row[3], row[4])
            expires = row[5]
            now = int(datetime.now().timestamp())
            if now > expires:
                spy_cursor.execute("DELETE FROM spy WHERE sendto = ? AND expires = ?", (row[4], row[5],))
                try:
                    vk.messages.send(user_id=row[4], random_id=get_random_id(),
                                     message=messages.message_spy_expired, keyboard=spy_keyboard.get_keyboard())
                except Exception as msgexc:
                    print(msgexc)
                    pass
            else:
                spy_cursor.execute("UPDATE spy SET id1_flag = ?, id2_flag = ? WHERE sendto = ? AND expires = ?", (str(id1_flag), str(id2_flag), row[4], row[5]))
                spy_connection.commit()

        print("Spy still watching...", datetime.now())
        time.sleep(300)


for event in longpoll.listen():         #workflags: 0 = free, 1 = check, 2 = spy first link, 3 = spy second link
    if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text and event.from_user:
        text = event.text
        if (text == "Начать" or text == "Назад"):
            try:
                set_workflag(event.user_id, 0)
                vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                 message=messages.message_choose, keyboard=main_keyboard.get_keyboard())
            except Exception as msgexc:
                print(msgexc)
                pass

        elif (text == "Что бот умеет?"):
            try:
                set_workflag(event.user_id, 0)
                vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                 message=messages.message_bot_func, keyboard=main_keyboard.get_keyboard())
            except Exception as msgexc:
                print(msgexc)
                pass

        elif (text == "Установить слежку"):
            try:
                set_workflag(event.user_id, 0)
                msg = messages.message_spy_choose_dur + str(get_balance(user_id=event.user_id)) + " 🔑"
                vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                 message=msg, keyboard=spy_keyboard.get_keyboard())
            except Exception as msgexc:
                print(msgexc)
                pass

        elif (text == "1 день"):
            if get_balance(event.user_id) < 1:
                try:
                    vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                     message=messages.message_insufficient_funds, keyboard=balance_keyboard.get_keyboard())
                except Exception as msgexc:
                    print(msgexc)
                    pass
            else:
                try:
                    set_spy_price(event.user_id, 1)
                    set_workflag(event.user_id, 2)
                    vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                     message=messages.message_spy_first_link, keyboard=back_keyboard.get_keyboard())
                except Exception as msgexc:
                    print(msgexc)
                    pass

        elif (text == "3 дня"):
            if get_balance(event.user_id) < 3:
                try:
                    vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                     message=messages.message_insufficient_funds, keyboard=balance_keyboard.get_keyboard())
                except Exception as msgexc:
                    print(msgexc)
                    pass
            else:
                try:
                    set_spy_price(event.user_id, 3)
                    set_workflag(event.user_id, 2)
                    vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                     message=messages.message_spy_first_link, keyboard=back_keyboard.get_keyboard())
                except Exception as msgexc:
                    print(msgexc)
                    pass

        elif (text == "7 дней"):
            if get_balance(event.user_id) < 7:
                try:
                    vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                     message=messages.message_insufficient_funds, keyboard=balance_keyboard.get_keyboard())
                except Exception as msgexc:
                    print(msgexc)
                    pass
            else:
                try:
                    set_spy_price(event.user_id, 7)
                    set_workflag(event.user_id, 2)
                    vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                     message=messages.message_spy_first_link, keyboard=back_keyboard.get_keyboard())
                except Exception as msgexc:
                    print(msgexc)
                    pass

        elif (text == "Проверить оплату"):
            if check_payment(event.user_id):
                try:
                    msg = messages.message_payment_successful + str(get_balance(event.user_id)) + " 🔑"
                    vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                     message=msg, keyboard=main_keyboard.get_keyboard())
                except Exception as msgexc:
                    print(msgexc)
                    pass
            else:
                try:
                    vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                     message=messages.message_payment_failed, keyboard=main_keyboard.get_keyboard())
                except Exception as msgexc:
                    print(msgexc)
                    pass

        elif (text == "Купить 🔑"):
            msg_balance = "Ваш текущий баланс: " + str(get_balance(event.user_id)) + " 🔑"
            try:
                vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                 message=messages.message_pricelist, keyboard=payment_keyboard.get_keyboard())
                vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                 message=msg_balance, keyboard=main_keyboard.get_keyboard())
            except Exception as msgexc:
                print(msgexc)
                pass

        elif (text == "1x 🔑"):
            buy_keys(x1_key_price, 1, event.user_id)

        elif (text == "3x 🔑"):
            buy_keys(x3_key_price, 3, event.user_id)

        elif (text == "6x 🔑"):
            buy_keys(x6_key_price, 6, event.user_id)

        elif (text == "10x 🔑"):
            buy_keys(x10_key_price, 10, event.user_id)

        elif (text == "Проверить пользователя"):
            try:
                set_workflag(event.user_id, 1)
                msg = messages.message_check_link + str(get_balance(event.user_id)) + " 🔑"
                vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                 message=msg, keyboard=back_keyboard.get_keyboard())
            except Exception as msgexc:
                print(msgexc)
                pass

        elif (text == "kaplan_ewn"):
            if flag == "01":
                try:
                    vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                     message="YHAHA YOU FOUND ME!\nMade by policelettuce 20.03.2022\nSnake is already on Shadow Moses island...", keyboard=main_keyboard.get_keyboard())
                except Exception as msgexc:
                    print(msgexc)
                    pass
            else:
                flag = "01"
                try:
                    vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                     message="Spy has awaken!...", keyboard=main_keyboard.get_keyboard())
                except Exception as msgexc:
                    print(msgexc)
                    pass
                Thread(target=spy).start()

        elif (text == "tokens_ewn"):
            check_for_banned_tokens()
            try:
                vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                 message="done, check the console...", keyboard=back_keyboard.get_keyboard())
            except Exception as msgexc:
                print(msgexc)
                pass

        elif ((text.split("_"))[0] == "SETKEYS"):
            id = (text.split("_"))[1]
            amt = (text.split("_"))[2]
            if (event.user_id == 253605549 or event.user_id == 96982440):
                cursor.execute("UPDATE users SET balance = ? WHERE userid = ?", (str(amt), str(id),))
                connection.commit()
                try:
                    vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                     message="Set!", keyboard=back_keyboard.get_keyboard())
                except Exception as msgexc:
                    print(msgexc)
                    pass
            else:
                try:
                    vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                     message="EASTEREGG_POLICELETTUCE_01: You found me! Nice try, but you're not allowed to do that...", keyboard=back_keyboard.get_keyboard())
                except Exception as msgexc:
                    print(msgexc)
                    pass

        elif ((text.split("_"))[0] == "ADDKEYS"):
            id = (text.split("_"))[1]
            amt = (text.split("_"))[2]
            if (event.user_id == 253605549 or event.user_id == 96982440):
                cursor.execute("UPDATE users SET balance = balance + ? WHERE userid = ?", (str(amt), str(id),))
                connection.commit()
                try:
                    vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                     message="Added!", keyboard=back_keyboard.get_keyboard())
                except Exception as msgexc:
                    print(msgexc)
                    pass
            else:
                try:
                    vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                     message="EASTEREGG_POLICELETTUCE_01: You found me! Nice try, but you're not allowed to do that...", keyboard=back_keyboard.get_keyboard())
                except Exception as msgexc:
                    print(msgexc)
                    pass

        else:
            get_workflag(event.user_id)
            if (get_workflag(event.user_id) == 1):
                check_payment(event.user_id)
                if is_enough_keys(event.user_id):
                    #region check start
                    if event.user_id in busy_users:
                        try:
                            vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                             message=messages.message_wait_for_check, keyboard=back_keyboard.get_keyboard())
                        except Exception as msgexc:
                            print(msgexc)
                            pass
                        continue
                    else:
                        busy_users.append(event.user_id)
                        parts = text.split("/")
                        user_sex = 0
                        try:
                            temp = stl_session().method("users.get", {"user_id": parts[-1], "fields": "sex", "lang": "0"})[0]
                            user_id = temp.get("id")
                            user_sex = temp.get("sex")
                            user_name = temp.get("first_name") + " " + temp.get("last_name")
                        except Exception as exc:
                            busy_users.remove(event.user_id)
                            if (str(exc).split(" ")[0] == "[5]"):
                                print("CAUGHT EXCEPTION: ", exc)
                                remove_last_token()
                            try:
                                vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                                 message=messages.message_error_user_search,
                                                 keyboard=back_keyboard.get_keyboard())
                            except Exception as msgexc:
                                print(msgexc)
                                pass
                            continue

                        try:
                            temp = stl_session().method("friends.get",
                                                        {"user_id": user_id, "order": "random", "count": 500, "lang": "0"})
                            friends_list = temp.get("items")
                            friends_count = temp.get("count")
                        except Exception as exc:
                            if (str(exc).split(" ")[0] == "[5]"):
                                print("CAUGHT EXCEPTION: ", exc)
                                remove_last_token()
                            busy_users.remove(event.user_id)
                            try:
                                vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                                 message=messages.message_error_user_private,
                                                 keyboard=main_keyboard.get_keyboard())
                            except Exception as msgexc:
                                print(msgexc)
                                pass
                            continue

                        decrement_balance(event.user_id)    # ПИЗДИМ денЬГИ У АБОненТА
                        try:
                            vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                             message=(messages.message_check_in_progress + str(get_balance(event.user_id)) + " 🔑"),
                                             keyboard=back_keyboard.get_keyboard())
                        except Exception as msgexc:
                            print(msgexc)
                            pass
                        Thread(target=check, args=(event, friends_list, user_sex, user_id, friends_count, parts, user_name)).start()
                    #endregion
                else:
                    send_closed_check_message(event.user_id, text)

            elif (get_workflag(event.user_id) == 2):
                parts = text.split("/")
                try:
                    temp = stl_session().method("users.get", {"user_id": parts[-1], "lang": "0"})[0]
                    userid = temp.get("id")
                except Exception as exc:
                    if (str(exc).split(" ")[0] == "[5]"):
                        print("CAUGHT EXCEPTION: ", exc)
                        remove_last_token()
                    try:
                        vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                         message=messages.message_error_user_search,
                                         keyboard=back_keyboard.get_keyboard())
                    except Exception as msgexc:
                        print(msgexc)
                        pass
                    continue
                set_workflag(event.user_id, 3)
                cursor.execute("UPDATE spying SET id1 = ? WHERE send_to = ?", (str(userid), str(event.user_id),))
                connection.commit()
                try:
                    vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                     message=messages.message_spy_second_link,
                                     keyboard=back_keyboard.get_keyboard())
                except Exception as msgexc:
                    print(msgexc)
                    pass

            elif (get_workflag(event.user_id) == 3):
                parts = text.split("/")
                try:
                    temp = stl_session().method("users.get", {"user_id": parts[-1], "lang": "0"})[0]
                    userid = temp.get("id")
                except Exception as exc:
                    if (str(exc).split(" ")[0] == "[5]"):
                        print("CAUGHT EXCEPTION: ", exc)
                        remove_last_token()
                    try:
                        vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                         message=messages.message_error_user_search,
                                         keyboard=back_keyboard.get_keyboard())
                    except Exception as msgexc:
                        print(msgexc)
                        pass
                    continue
                cursor.execute("SELECT price FROM spying WHERE send_to=?", (str(event.user_id),))
                days = cursor.fetchall()[0][0]
                now = datetime.now()
                expires = int((now + timedelta(days=days)).timestamp())         #CHANGE TIMEDELTA ARG FROM HOURS TO DAYS
                cursor.execute("UPDATE spying SET id2 = ?, expires = ? WHERE send_to = ?", (str(userid), expires, str(event.user_id),))
                connection.commit()
                cursor.execute("SELECT * FROM spying WHERE send_to = ?", (str(event.user_id),))
                row = cursor.fetchall()
                pending_spy.append(row[0])
                decrement_balance_by_amt(event.user_id, row[0][4])
                set_workflag(event.user_id, 0)
                cursor.execute("DELETE FROM spying WHERE send_to = ?", (str(event.user_id),))
                connection.commit()
                try:
                    vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                     message=(messages.message_spy_payment + str(get_balance(event.user_id)) + " 🔑"),
                                     keyboard=main_keyboard.get_keyboard())
                except Exception as msgexc:
                    print(msgexc)
                    pass
            else:
                try:
                    vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                     message=messages.message_choose, keyboard=main_keyboard.get_keyboard())
                except Exception as msgexc:
                    print(msgexc)
                    pass
