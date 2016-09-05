# Created by Benjamin J. Thompson <bjt@rabidquill.com>

from os.path import dirname
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

from datetime import datetime, timedelta
from time import mktime
import parsedatetime
import re

import requests
from bs4 import BeautifulSoup

__author__ = 'bjt'

LOGGER = getLogger(__name__)

def match_class(target):
    def do_match(tag):
        classes = tag.get('class', [])
        return all(c in classes for c in target)
    return do_match


class NextLaunchSkill(MycroftSkill):
    def __init__(self):
        super(NextLaunchSkill, self).__init__(name="NextLaunchSkill")

    def initialize(self):
        self.load_data_files(dirname(__file__))
        next_launch_intent = IntentBuilder("NextLaunchIntent").\
            require("NextLaunchKeyword").build()
        self.register_intent(next_launch_intent, self.handle_next_launch_intent)

    def handle_next_launch_intent(self, message):
        html = requests.get("http://spaceflightnow.com/launch-schedule/").content
        soup = BeautifulSoup(html, 'html.parser')
        schedule = []
        cal = parsedatetime.Calendar()
        datenames = soup.find_all(match_class(['datename']))
        missiondatas = soup.find_all(match_class(['missiondata']))
        missdescrips = soup.find_all(match_class(['missdescrip']))
        for n in range(len(datenames)):
            try:
                launch = dict(launch_date=datenames[n].find('span', attrs={'class': 'launchdate'}).text,
                                     rocket_name=datenames[n].find('span', attrs={'class': 'mission'}).text.replace(u"\u2022 ", ""),
                                     #launch_description=missdescrips[n].text,
                                     launch_time=missiondatas[n].text.split("\n")[0].replace("Launch window: ", "").replace("Launch time: ", ""),
                                     launch_location=missiondatas[n].text.split("\n")[1].replace("Launch site: ", ""))
                launch['launch_date'] = launch['launch_date'].replace("Sept.", "Sep.") # For some reason the parser doesn't like Sept
                gmt_time = re.search(r"^\d{4}", launch['launch_time']).group(0)
                launch['launch_date'] += ' ' + ":".join([gmt_time[:2], gmt_time[2:]]) + ' GMT'
                time_struct, parse_status = cal.parse(launch['launch_date'])
                if parse_status == 0:
                    print("Could not parse for {0} - {1}".format(launch['launch_date'], launch['rocket_name']))
                    continue # If this didn't work it's probably not the upcoming launch
                sched_date = datetime.fromtimestamp(mktime(time_struct))
                time_till = sched_date - datetime.now()
                launch['time_till'] = time_till
                launch['launch_date'] = sched_date.strftime("%B %d")
                launch['launch_time'] = re.search(r"(\d+:.+EDT)", launch['launch_time']).group(0).replace("EDT", "Eastern Daylight Time").replace("EST", "Eastern Standard Time")
                schedule.append(launch)
            except Exception as e:
                print(e.message)
                continue

        sorted_schedule = sorted(schedule, key=lambda k: k['time_till'])
        print sorted_schedule
        self.speak_dialog("next.launch", sorted_schedule[0])

    def stop(self):
        pass


def create_skill():
    return NextLaunchSkill()