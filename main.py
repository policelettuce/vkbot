import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id
from tokens import main_token, stl_token
import messages
import operator
import random
import sqlite3
from threading import Thread
from datetime import datetime
from itertools import islice

#region keyboards
main_keyboard = VkKeyboard(one_time=True)
main_keyboard.add_button("Проверить пользователя", color=VkKeyboardColor.PRIMARY)
main_keyboard.add_line()
main_keyboard.add_button("Установить слежку", color=VkKeyboardColor.PRIMARY)
main_keyboard.add_line()
main_keyboard.add_button("Что бот умеет?", color=VkKeyboardColor.SECONDARY)

back_keyboard = VkKeyboard(one_time=True)
back_keyboard.add_button("Назад", color=VkKeyboardColor.SECONDARY)
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

def stl_session():
    stl_token[0] += 1
    if stl_token[0] >= len(stl_token):
        stl_token[0] = 1

    return vk_api.VkApi(token=stl_token[stl_token[0]])

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
                         message=messages.message_wait_for_check, keyboard=main_keyboard.get_keyboard())
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
                             keyboard=main_keyboard.get_keyboard())
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
                     message=message_check)


for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text and event.from_user:
        text = event.text
        if (text == "Начать" or text == "Назад"):
            flag = "nothing"
            vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                             message=messages.message_choose, keyboard=main_keyboard.get_keyboard())

        elif (text == "Что бот умеет?"):
            flag = "nothing"
            vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                             message=messages.message_bot_func, keyboard=main_keyboard.get_keyboard())

        elif (text == "Установить слежку"):
            flag = "spy"
            vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                             message=messages.message_spy_first_link, keyboard=back_keyboard.get_keyboard())

        elif (text == "Проверить пользователя"):
            flag = "check"
            vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                             message=messages.message_check_link, keyboard=back_keyboard.get_keyboard())

        else:
            if (flag == "check"):
                Thread(target=check, args=(text, event,)).start()
            elif (flag == "spy"):
                temp = 1
            else:
                vk.messages.send(user_id=event.user_id, random_id=get_random_id(),
                                 message="сначала выбери функцию", keyboard=main_keyboard.get_keyboard())

