import os
import pickle
import time
from datetime import datetime, timedelta

import requests

tg_token = os.environ.get("tg_token")
hourly_rate = os.environ.get("hourly_rate")


def send_message(message: str, chats=["-772675144"]):
    telegram_token = tg_token
    for chat in chats:
        requests.post(
            f"https://api.telegram.org/bot{telegram_token}/sendMessage",
            data={"chat_id": chat, "text": message},
        )


first_time = None
last_time = None
break_time = timedelta(minutes=5)
total_money = 0
week_money = 0
week_work_times = []
week_work_deltas = []
while True:
    today = datetime.today()
    # Sunday
    if today.isoweekday() == 7:
        total_money += week_money
        week_message = f"""
            Сегодня день выплат. Нужно выплатить {week_money}
            Общий заработок {total_money}"""
        send_message(week_message)
        stats = {"week_deltas": week_work_deltas, "week_times": week_work_times, "week_money": week_money}
        today_str = str(today).split()[0]
        with open(f"{today_str}.pcl", "wb") as f:
            pickle.dump(stats, f)
        week_money = 0
    with open("annotation.log") as f:
        log = f.readlines()
    work_times = []
    work_deltas = []
    day_money = 0
    log = [l for l in log if "irina" in l]
    for line in log:
        time_str = line.split("\t")[0].split(",")[0]
        time_obj = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        if not first_time:
            first_time = time_obj
        if time_obj <= first_time:
            continue
        if not last_time:
            time_diff = time_obj - first_time
            if time_diff < break_time:
                last_time = time_obj
            else:
                first_time = time_obj
            continue
        time_diff = time_obj - last_time
        if time_diff > break_time:
            print("break", time_obj, time_diff)
            work_times.append((first_time, last_time))
            work_time = last_time - first_time
            work_deltas.append(work_time)
            day_money += round(hourly_rate * (work_time.seconds / 3600))
            last_time = None
            first_time = time_obj
            continue
        last_time = time_obj

    if last_time and first_time:
        print("break", time_obj, time_diff)
        work_times.append((first_time, last_time))
        work_time = last_time - first_time
        work_deltas.append(work_time)
        day_money += round(150 * (work_time.seconds / 3600))
        last_time = None
        first_time = time_obj

    week_money += day_money
    week_work_times.append(work_times)
    week_work_deltas.append(work_deltas)
    work_interval_str = "Вы работали в следующие периоды времени:\n"
    for pair in work_times:
        work_interval_str += f"\tс {pair[0]} до {pair[1]}\n"
    message = f"""
    С последней проверки вы заработали {day_money}.
    За эту неделю вы заработали {week_money}
    {work_interval_str}"""
    send_message(message)
    stats = {"week_deltas": week_work_deltas, "week_times": week_work_times, "week_money": week_money}
    with open("week_stats.pcl", "wb") as f:
        pickle.dump(stats, f)
    print(message)
    time.sleep(24 * 60 * 60)
