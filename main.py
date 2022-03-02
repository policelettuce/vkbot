import uuid
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id
from tokens import main_token, stl_token
import messages
import operator
import random
from threading import Thread

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

vk_session = vk_api.VkApi(token=main_token)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)


def stl_session():
    stl_token[0] += 1
    if stl_token[0] >= len(stl_token):
        stl_token[0] = 1

    return vk_api.VkApi(token=stl_token[stl_token[0]])

#check for banned tokens
for token in stl_token[1::]:
    print("TOKEN ", token, " : ")
    res = stl_session().method("friends.get", {"user_id": "253605549"})

flag = "MADE BY POLICELETTUCE 15.02.2022"
busy_users = []


def check(raw_link, current_event):
    if current_event.user_id in busy_users:
        vk.messages.send(user_id=current_event.user_id, random_id=get_random_id(),
                         message=messages.message_wait_for_check, keyboard=main_keyboard.get_keyboard())
        return
    else:
        busy_users.append(current_event.user_id)
        print(busy_users)
        parts = raw_link.split("/")
        user_sex = 0
        try:
            temp = vk_session.method("users.get", {"user_id": parts[-1], "fields": "sex"})[0]
            user_id = temp.get("id")
            user_sex = temp.get("sex")
        except Exception:
            vk.messages.send(user_id=current_event.user_id, random_id=get_random_id(),
                             message=messages.message_error_user_search,
                             keyboard=main_keyboard.get_keyboard())
            return

        try:
            friends_list = stl_session().method("friends.get", {"user_id": user_id, "order": "random", "count": 500}).get("items")
        except Exception:
            vk.messages.send(user_id=current_event.user_id, random_id=get_random_id(),
                             message=messages.message_error_user_private,
                             keyboard=main_keyboard.get_keyboard())
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

                    for photo in photos:
                        is_liked = stl_session().method("likes.isLiked", {"user_id": user_id, "type": "photo",
                                                        "owner_id": friend_id, "item_id": photo.get("id")}).get("liked")
                        if (is_liked):
                            times_user_liked[friend_id] += 1
                            print("FOUND LIKED PHOTO! TOTAL LIKES BY USER: ", times_user_liked[friend_id])

            except Exception:
                continue

    sorted_dict = sorted(times_user_liked.items(), key=operator.itemgetter(1))
    random.shuffle(no_mutual_friends)
    print("LIKES: ", sorted_dict)
    print(no_mutual_friends)
    vk.messages.send(user_id=current_event.user_id, random_id=get_random_id(),
                     message=messages.message_check_finished)


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

